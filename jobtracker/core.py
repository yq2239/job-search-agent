from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


VALID_STATUSES = {
    "discovered",
    "manual_review",
    "recommended",
    "interested",
    "applied",
    "skipped",
    "rejected",
    "closed",
    "withdrawn",
}
VALID_AVAILABILITY = {"active", "closed", "unknown"}

_MUTATION_LOCK = threading.RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.casefold()
    path = re.sub(r"/+", "/", parts.path).rstrip("/") or "/"
    # Some official careers sites identify postings only in the query string
    # (for example Waymo's gh_jid and Snap's id). Remove presentation/tracking
    # parameters, but retain identity-bearing query parameters.
    dropped = {"lang", "locale", "source", "ref", "referrer"}
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in dropped
    ]
    return urlunsplit(
        (parts.scheme.casefold() or "https", host, path, urlencode(sorted(query)), "")
    )


def make_job_id(company: str, title: str, location: str, url: str) -> str:
    key = "|".join(
        [
            normalize_text(company),
            normalize_text(title),
            normalize_text(location),
            canonicalize_url(url),
        ]
    )
    return "JOB-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12].upper()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def evaluate_job(job: dict[str, Any], requirements: dict[str, Any]) -> tuple[str, list[str]]:
    hard = requirements["hard_filters"]
    reasons: list[str] = []

    location = normalize_text(job.get("location", ""))
    allowed = [normalize_text(item) for item in hard["allowed_locations"]]
    if not location or location in {"unknown", "not stated"}:
        reasons.append("location is unknown")
    elif not any(item in location or location in item for item in allowed):
        return "ineligible", ["location is outside the configured allowed location list"]

    sponsorship = job.get("sponsorship", "unknown")
    if hard.get("requires_employer_sponsorship_or_h1b_transfer", True):
        if sponsorship == "does_not_sponsor":
            return "ineligible", ["employer/role does not support required sponsorship or H-1B transfer"]
        if sponsorship == "unknown":
            reasons.append("sponsorship or H-1B transfer support is unverified")

    education = job.get("minimum_education", "unknown")
    if education in hard.get("exclude_if_minimum_education_is", []):
        return "ineligible", [f"minimum education requirement is {education}"]
    if education == "unknown":
        reasons.append("minimum education requirement is unknown")

    if reasons:
        return requirements.get("unknown_fact_policy", "manual_review"), reasons
    return "eligible", ["all configured hard requirements pass"]


class JobStore:
    def __init__(self, jobs_path: Path, requirements_path: Path):
        self.jobs_path = jobs_path
        self.requirements_path = requirements_path

    def _data(self) -> dict[str, Any]:
        return load_json(self.jobs_path)

    def _requirements(self) -> dict[str, Any]:
        return load_json(self.requirements_path)

    def add(self, candidate: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        with _MUTATION_LOCK:
            return self._add(candidate)

    def _add(self, candidate: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        data = self._data()
        jobs = data["jobs"]
        candidate = deepcopy(candidate)
        if candidate.get("availability") != "active" or not candidate.get("last_verified_at"):
            raise ValueError("job must pass a live official-page verification before it can be added")
        candidate["url"] = canonicalize_url(candidate["url"])
        candidate_id = make_job_id(
            candidate["company"], candidate["title"], candidate["location"], candidate["url"]
        )
        source_id = candidate.get("source_job_id")
        for existing in jobs:
            same_source = source_id and existing.get("source_job_id") == source_id
            if existing["id"] == candidate_id or existing.get("url") == candidate["url"] or same_source:
                eligibility, reasons = evaluate_job(candidate, self._requirements())
                existing.update(
                    {
                        "company": candidate["company"],
                        "title": candidate["title"],
                        "location": candidate["location"],
                        "url": candidate["url"],
                        "source_job_id": candidate.get("source_job_id"),
                        "sponsorship": candidate.get("sponsorship", "unknown"),
                        "minimum_education": candidate.get("minimum_education", "unknown"),
                        "fit_score": candidate.get("fit_score", existing.get("fit_score", 0)),
                        "evidence": candidate.get("evidence", existing.get("evidence", "")),
                        "eligibility": eligibility,
                        "eligibility_reasons": reasons,
                        "availability": candidate["availability"],
                        "last_verified_at": candidate["last_verified_at"],
                        "verification_evidence": candidate.get("verification_evidence", ""),
                    }
                )
                existing.setdefault("verification_history", []).append(
                    {
                        "at": candidate["last_verified_at"],
                        "availability": candidate["availability"],
                        "evidence": candidate.get("verification_evidence", ""),
                    }
                )
                save_json(self.jobs_path, data)
                return existing, False

        eligibility, reasons = evaluate_job(candidate, self._requirements())
        now = utc_now()
        initial_status = "manual_review" if eligibility == "manual_review" else "discovered"
        candidate.update(
            {
                "id": candidate_id,
                "eligibility": eligibility,
                "eligibility_reasons": reasons,
                "status": initial_status,
                "discovered_at": now,
                "updated_at": now,
                "history": [{"at": now, "status": initial_status, "note": "job added"}],
                "verification_history": [
                    {
                        "at": candidate["last_verified_at"],
                        "availability": candidate["availability"],
                        "evidence": candidate.get("verification_evidence", ""),
                    }
                ],
            }
        )
        jobs.append(candidate)
        save_json(self.jobs_path, data)
        return candidate, True

    def record_verification(self, job_id: str, result: dict[str, str]) -> dict[str, Any]:
        availability = result.get("availability", "unknown")
        if availability not in VALID_AVAILABILITY:
            raise ValueError(f"invalid availability: {availability}")
        with _MUTATION_LOCK:
            data = self._data()
            for job in data["jobs"]:
                if job["id"] != job_id:
                    continue
                checked_at = result["last_verified_at"]
                evidence = result.get("verification_evidence", "")
                job.update(
                    {
                        "availability": availability,
                        "last_verified_at": checked_at,
                        "verification_evidence": evidence,
                        "updated_at": checked_at,
                    }
                )
                job.setdefault("verification_history", []).append(
                    {"at": checked_at, "availability": availability, "evidence": evidence}
                )
                if availability == "closed" and job.get("status") != "closed":
                    job["status"] = "closed"
                    job.setdefault("history", []).append(
                        {"at": checked_at, "status": "closed", "note": evidence}
                    )
                save_json(self.jobs_path, data)
                return deepcopy(job)
        raise KeyError(job_id)

    def set_status(self, job_id: str, status: str, note: str = "") -> dict[str, Any]:
        with _MUTATION_LOCK:
            return self._set_status(job_id, status, note)

    def _set_status(self, job_id: str, status: str, note: str = "") -> dict[str, Any]:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status}")
        data = self._data()
        for job in data["jobs"]:
            if job["id"] == job_id:
                now = utc_now()
                job["status"] = status
                job["updated_at"] = now
                job.setdefault("history", []).append({"at": now, "status": status, "note": note})
                save_json(self.jobs_path, data)
                return job
        raise KeyError(job_id)

    def list(self) -> list[dict[str, Any]]:
        return deepcopy(self._data()["jobs"])

    def add_note(self, job_id: str, body: str) -> dict[str, Any]:
        body = body.strip()
        if not body:
            raise ValueError("note cannot be empty")
        if len(body) > 4000:
            raise ValueError("note cannot exceed 4000 characters")
        with _MUTATION_LOCK:
            return self._add_note(job_id, body)

    def _add_note(self, job_id: str, body: str) -> dict[str, Any]:
        data = self._data()
        for job in data["jobs"]:
            if job["id"] == job_id:
                return self._save_note(data, job, body)
        raise KeyError(job_id)

    def _save_note(self, data: dict[str, Any], job: dict[str, Any], body: str) -> dict[str, Any]:
        now = utc_now()
        note_id = "NOTE-" + uuid.uuid4().hex[:12].upper()
        note = {"id": note_id, "at": now, "body": body}
        job.setdefault("notes", []).append(note)
        job["updated_at"] = now
        save_json(self.jobs_path, data)
        return deepcopy(job)

    def recommendations(self, minimum_score: int = 0) -> list[dict[str, Any]]:
        jobs = self._data()["jobs"]
        terminal = {"applied", "skipped", "rejected", "closed", "withdrawn"}
        return [
            job
            for job in jobs
            if job.get("eligibility") == "eligible"
            and job.get("availability") == "active"
            and job.get("status") not in terminal
            and int(job.get("fit_score", 0)) >= minimum_score
        ]

    def get(self, job_id: str) -> dict[str, Any]:
        for job in self._data()["jobs"]:
            if job["id"] == job_id:
                return job
        raise KeyError(job_id)

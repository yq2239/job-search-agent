from __future__ import annotations

import html
import json
import re
import ssl
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, urlsplit


MAX_RESPONSE_BYTES = 4_000_000
USER_AGENT = "Mozilla/5.0 (compatible; JobTracker/1.0; local verification)"
SYSTEM_CA_FILE = Path("/etc/ssl/cert.pem")

GREENHOUSE_WRAPPER_BOARDS = {
    "careers.withwaymo.com": "waymo",
}
TESLA_CAREERS_STATE_URL = "https://www.tesla.com/cua-api/apps/careers/state"
TESLA_SNAPSHOT_MAX_AGE = timedelta(hours=24)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class VerificationResult:
    availability: str
    last_verified_at: str
    verification_evidence: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def visible_text(page_html: str) -> str:
    value = re.sub(r"<(script|style)\b.*?</\1>", " ", page_html, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def classify_official_posting_html(page_html: str, expected_title: str) -> tuple[str, str]:
    text = visible_text(page_html)
    folded = text.casefold()
    raw_folded = html.unescape(page_html).casefold()
    closed_markers = (
        "job not found",
        "this job may have been taken down",
        "this job has been closed",
        "job is no longer available",
        "position is no longer available",
        "no longer accepting applications",
    )
    if any(marker in folded for marker in closed_markers) or '"islisted":false' in raw_folded:
        return "closed", "official posting reports that the job is unavailable"
    if expected_title.casefold() not in folded and expected_title.casefold() not in raw_folded:
        return "unknown", "official page did not contain the expected job title"
    has_apply_action = bool(re.search(r"\bapply\b", text, flags=re.IGNORECASE))
    has_live_structured_posting = (
        '"@type":"jobposting"' in raw_folded
        and ('"directapply":true' in raw_folded or '"islisted":true' in raw_folded)
    )
    if not has_apply_action and not has_live_structured_posting:
        return "unknown", "official page did not contain an Apply action"
    return "active", "official posting contained the expected title and a live Apply action"


def classify_google_careers_html(page_html: str, expected_title: str) -> tuple[str, str]:
    """Backward-compatible alias for callers of the original Google-only verifier."""
    return classify_official_posting_html(page_html, expected_title)


def greenhouse_api_url(posting_url: str) -> str | None:
    parts = urlsplit(posting_url)
    board = GREENHOUSE_WRAPPER_BOARDS.get(parts.netloc.casefold())
    job_ids = parse_qs(parts.query).get("gh_jid", [])
    if not board or not job_ids or not job_ids[0].isdigit():
        return None
    return f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_ids[0]}?content=true"


def classify_greenhouse_job_json(payload: str, expected_title: str) -> tuple[str, str]:
    try:
        posting = json.loads(payload)
    except json.JSONDecodeError:
        return "unknown", "official Greenhouse response was not valid JSON"
    title = str(posting.get("title", ""))
    if title.casefold() != expected_title.casefold():
        return "unknown", "official Greenhouse posting did not match the expected title"
    if not posting.get("id") or not posting.get("absolute_url"):
        return "unknown", "official Greenhouse response lacked a live posting identifier"
    return "active", "official Greenhouse API returned the expected live posting"


def workday_api_url(posting_url: str) -> str | None:
    parts = urlsplit(posting_url)
    if not parts.netloc.casefold().endswith(".myworkdayjobs.com"):
        return None
    tenant = parts.netloc.split(".", 1)[0]
    path_parts = [part for part in parts.path.split("/") if part]
    if path_parts and re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", path_parts[0]):
        path_parts = path_parts[1:]
    if len(path_parts) < 4 or path_parts[1] != "job":
        return None
    site = path_parts[0]
    job_path = "/".join(path_parts[1:])
    return f"{parts.scheme}://{parts.netloc}/wday/cxs/{tenant}/{site}/{job_path}"


def classify_workday_job_json(payload: str, expected_title: str) -> tuple[str, str]:
    try:
        posting = json.loads(payload).get("jobPostingInfo", {})
    except json.JSONDecodeError:
        return "unknown", "official Workday response was not valid JSON"
    if str(posting.get("title", "")).casefold() != expected_title.casefold():
        return "unknown", "official Workday posting did not match the expected title"
    if not posting.get("posted") or not posting.get("canApply"):
        return "closed", "official Workday posting is no longer open for applications"
    if not posting.get("jobReqId") or not posting.get("externalUrl"):
        return "unknown", "official Workday response lacked a live posting identifier"
    return "active", "official Workday API returned the expected live, applyable posting"


def _normalized_location(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold()).replace(", california", ", ca")


def verify_tesla_snapshot(
    snapshot_path: Path,
    posting_url: str,
    expected_title: str,
    expected_source_job_id: str | None,
    expected_location: str,
) -> VerificationResult:
    """Verify a Tesla role against a fresh snapshot of Tesla's official careers feed."""
    checked_at = utc_now()
    parts = urlsplit(posting_url)
    match = re.search(r"(?:-|/)(\d{5,})/?$", parts.path)
    if parts.scheme != "https" or parts.netloc.casefold() != "www.tesla.com" or not match:
        return VerificationResult("unknown", checked_at, "Tesla snapshot requires an official Tesla job URL with a requisition ID")
    posting_id = match.group(1)
    if expected_source_job_id and expected_source_job_id != posting_id:
        return VerificationResult("unknown", checked_at, "Tesla requisition ID did not match the official posting URL")
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        captured_at = datetime.fromisoformat(str(snapshot["captured_at"]).replace("Z", "+00:00"))
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return VerificationResult("unknown", checked_at, "Tesla verification snapshot was missing or invalid")
    if captured_at.tzinfo is None:
        return VerificationResult("unknown", checked_at, "Tesla verification snapshot timestamp lacked a timezone")
    age = datetime.now(timezone.utc) - captured_at.astimezone(timezone.utc)
    if age < timedelta(minutes=-5) or age > TESLA_SNAPSHOT_MAX_AGE:
        return VerificationResult("unknown", checked_at, "Tesla verification snapshot was not captured within the last 24 hours")
    if snapshot.get("source_url") != TESLA_CAREERS_STATE_URL:
        return VerificationResult("unknown", checked_at, "Tesla verification snapshot did not identify the official careers feed")
    jobs = snapshot.get("jobs")
    if not isinstance(jobs, list):
        return VerificationResult("unknown", checked_at, "Tesla verification snapshot did not contain a job list")
    for job in jobs:
        if not isinstance(job, dict) or str(job.get("id", "")) != posting_id:
            continue
        if str(job.get("title", "")).casefold() != expected_title.casefold():
            return VerificationResult("unknown", checked_at, "official Tesla snapshot title did not match the expected title")
        if _normalized_location(str(job.get("location", ""))) != _normalized_location(expected_location):
            return VerificationResult("unknown", checked_at, "official Tesla snapshot location did not match the expected location")
        if job.get("apply") is not True:
            return VerificationResult("unknown", checked_at, "official Tesla snapshot lacked a live Apply action")
        return VerificationResult(
            "active",
            checked_at,
            f"fresh official Tesla careers snapshot confirmed requisition {posting_id}, exact title/location, and Apply action",
        )
    return VerificationResult("closed", checked_at, f"requisition {posting_id} was absent from the fresh official Tesla careers snapshot")


def verify_job_url(url: str, expected_title: str, timeout: float = 35.0) -> VerificationResult:
    checked_at = utc_now()
    greenhouse_url = greenhouse_api_url(url)
    workday_url = workday_api_url(url)
    api_url = greenhouse_url or workday_url
    request = Request(
        api_url or url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
    )
    ssl_context = (
        ssl.create_default_context(cafile=str(SYSTEM_CA_FILE))
        if SYSTEM_CA_FILE.is_file()
        else ssl.create_default_context()
    )
    try:
        payload = b""
        last_error: Exception | None = None
        for _ in range(2):
            try:
                with urlopen(request, timeout=timeout, context=ssl_context) as response:
                    payload = response.read(MAX_RESPONSE_BYTES + 1)
                last_error = None
                break
            except HTTPError:
                raise
            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        if len(payload) > MAX_RESPONSE_BYTES:
            return VerificationResult("unknown", checked_at, "official page exceeded size limit")
        page_html = payload.decode("utf-8", errors="replace")
        if greenhouse_url:
            availability, evidence = classify_greenhouse_job_json(page_html, expected_title)
        elif workday_url:
            availability, evidence = classify_workday_job_json(page_html, expected_title)
        else:
            availability, evidence = classify_official_posting_html(page_html, expected_title)
        return VerificationResult(availability, checked_at, evidence)
    except HTTPError as exc:
        if exc.code in {404, 410}:
            return VerificationResult("closed", checked_at, f"official posting returned HTTP {exc.code}")
        return VerificationResult("unknown", checked_at, f"official page check failed: {exc}")
    except (URLError, TimeoutError, OSError) as exc:
        return VerificationResult("unknown", checked_at, f"official page check failed: {exc}")

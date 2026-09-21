from __future__ import annotations

import html
import json
import re
import ssl
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .core import JobStore


GOOGLE_CAREERS_URL = "https://www.google.com/about/careers/applications/jobs/results"
GOOGLE_QUERIES = (
    "data scientist",
    "applied scientist",
    "research scientist",
    "machine learning engineer",
    "research engineer",
    "AI engineer",
    "AI agent",
)
PAGES_PER_QUERY = 3
MAX_RESPONSE_BYTES = 8_000_000
USER_AGENT = "Mozilla/5.0 (compatible; SmartJobTracker/1.0; local job monitor)"
PACIFIC = ZoneInfo("America/Los_Angeles")


@dataclass(frozen=True)
class GooglePosting:
    source_job_id: str
    title: str
    company: str
    locations: tuple[str, ...]
    url: str
    posted_at: str
    minimum_education: str
    minimum_qualifications: str
    description: str


def _decode_data_set(page_html: str) -> list[list[object]]:
    match = re.search(
        r"AF_initDataCallback\(\{key: 'ds:1'.*? data:(.*?), sideChannel: \{\}\}\);",
        page_html,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("official Google Careers page did not expose its job data")
    try:
        data = json.loads(match.group(1))
        jobs = data[0]
    except (json.JSONDecodeError, IndexError, TypeError) as exc:
        raise ValueError("official Google Careers job data was malformed") from exc
    if not isinstance(jobs, list):
        raise ValueError("official Google Careers page did not contain a job list")
    return jobs


def _plain(value: object) -> str:
    if isinstance(value, list) and len(value) > 1:
        value = value[1]
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _timestamp_date(value: object) -> str:
    if not isinstance(value, list) or not value or not isinstance(value[0], int):
        raise ValueError("Google Careers record lacked an employer posting timestamp")
    return datetime.fromtimestamp(value[0], timezone.utc).astimezone(PACIFIC).date().isoformat()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "job"


def _minimum_education(minimum: str) -> str:
    folded = minimum.casefold()
    equivalent = "equivalent practical" in folded or "equivalent experience" in folded
    if "phd" in folded and not equivalent and not any(term in folded for term in ("bachelor", "master")):
        return "phd"
    if "master" in folded and not equivalent and "bachelor" not in folded:
        return "masters"
    if "bachelor" in folded and not equivalent:
        return "bachelors"
    if equivalent:
        return "none"
    return "unknown"


def parse_google_careers_html(page_html: str) -> list[GooglePosting]:
    postings: list[GooglePosting] = []
    for record in _decode_data_set(page_html):
        if not isinstance(record, list) or len(record) < 20:
            continue
        source_job_id = str(record[0])
        title = str(record[1]).strip()
        source_company = str(record[7]).strip()
        raw_locations = record[9] if isinstance(record[9], list) else []
        locations = tuple(
            str(location[0]).strip()
            for location in raw_locations
            if isinstance(location, list) and location and str(location[0]).strip()
        )
        minimum = _plain(record[19] or record[4])
        postings.append(
            GooglePosting(
                source_job_id=source_job_id,
                title=title,
                company="Google DeepMind" if source_company == "DeepMind" else "Google",
                locations=locations,
                url=f"{GOOGLE_CAREERS_URL}/{source_job_id}-{_slug(title)}",
                posted_at=_timestamp_date(record[12]),
                minimum_education=_minimum_education(minimum),
                minimum_qualifications=minimum,
                description=_plain(record[10]),
            )
        )
    return postings


def _ssl_context() -> ssl.SSLContext:
    for ca_file in (Path("/etc/ssl/cert.pem"), Path("/etc/ssl/certs/ca-certificates.crt")):
        if ca_file.is_file():
            return ssl.create_default_context(cafile=str(ca_file))
    return ssl.create_default_context()


def fetch_google_careers_page(query: str, page: int, timeout: float = 45.0) -> str:
    params = urlencode(
        {
            "company": ["Google", "DeepMind", "YouTube"],
            "employment_type": "FULL_TIME",
            "location": "California, USA",
            "q": query,
            "sort_by": "date",
            "page": page,
        },
        doseq=True,
    )
    request = Request(f"{GOOGLE_CAREERS_URL}?{params}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("Google Careers response exceeded the safety limit")
    return body.decode("utf-8", errors="replace")


def _is_target_role(posting: GooglePosting) -> bool:
    title = posting.title.casefold()
    excluded = (
        "intern",
        "early career",
        "manager",
        "director",
        "vice president",
        "vp,",
        "principal",
        "senior staff",
    )
    if any(term in title for term in excluded):
        return False
    direct = (
        "data scientist",
        "applied scientist",
        "research scientist",
        "machine learning engineer",
        "ml engineer",
        "research engineer",
        "ai engineer",
        "artificial intelligence engineer",
        "quantitative researcher",
    )
    if any(term in title for term in direct):
        return True
    return "software engineer" in title and any(
        term in title for term in ("ai/ml", "machine learning", "artificial intelligence", "agent")
    )


def _allowed_locations(posting: GooglePosting, requirements: dict[str, object]) -> tuple[str, ...]:
    hard = requirements.get("hard_filters", {})
    configured = hard.get("allowed_locations", []) if isinstance(hard, dict) else []
    allowed = {str(value).casefold().replace(", california", ", ca") for value in configured}
    matches = []
    for location in posting.locations:
        normalized = location.casefold().replace(", california", ", ca").replace(", usa", "")
        if any(item in normalized or normalized in item for item in allowed):
            matches.append(location.replace(", USA", ""))
    return tuple(matches)


def _fit_score(title: str) -> int:
    folded = title.casefold()
    if "data scientist" in folded:
        score = 94
    elif "applied scientist" in folded or "research scientist" in folded:
        score = 90
    elif "research engineer" in folded:
        score = 89
    elif "machine learning engineer" in folded or "ai engineer" in folded:
        score = 88
    else:
        score = 80
    return score


def is_within_business_days(value: str, limit: int = 2, today: date | None = None) -> bool:
    posted = date.fromisoformat(value)
    today = today or datetime.now(PACIFIC).date()
    if posted > today:
        return False
    cutoff = today
    included = 0
    while included < limit:
        if cutoff.weekday() < 5:
            included += 1
        if included < limit:
            cutoff -= timedelta(days=1)
    return posted >= cutoff


def refresh_google_jobs(
    store: JobStore,
    requirements: dict[str, object],
    *,
    fetcher=fetch_google_careers_page,
    checked_at: str | None = None,
) -> dict[str, object]:
    checked_at = checked_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    seen: dict[str, GooglePosting] = {}
    fetched_pages = 0
    for query in GOOGLE_QUERIES:
        for page in range(1, PAGES_PER_QUERY + 1):
            for posting in parse_google_careers_html(fetcher(query, page)):
                seen[posting.source_job_id] = posting
            fetched_pages += 1

    created: list[dict[str, object]] = []
    refreshed: list[dict[str, object]] = []
    skipped = 0
    existing_source_ids = {
        str(job.get("source_job_id"))
        for job in store.list()
        if job.get("company") in {"Google", "Google DeepMind"} and job.get("source_job_id")
    }
    for posting in sorted(seen.values(), key=lambda item: (item.posted_at, item.source_job_id), reverse=True):
        locations = _allowed_locations(posting, requirements)
        is_existing = posting.source_job_id in existing_source_ids
        if (
            not locations
            or not _is_target_role(posting)
            or posting.minimum_education == "phd"
            or (not is_existing and not is_within_business_days(posting.posted_at, 2))
        ):
            skipped += 1
            continue
        evidence = (
            "Official Google Careers feed match for the candidate's target AI/ML/data-science roles. "
            f"Minimum qualifications: {posting.minimum_qualifications[:420]}"
        )
        job, was_created = store.add(
            {
                "company": posting.company,
                "title": posting.title,
                "location": "; ".join(locations),
                "url": posting.url,
                "source_job_id": posting.source_job_id,
                "sponsorship": "unknown",
                "minimum_education": posting.minimum_education,
                "fit_score": _fit_score(posting.title),
                "evidence": evidence,
                "availability": "active",
                "last_verified_at": checked_at,
                "verification_evidence": (
                    "official Google Careers search feed returned the exact requisition, title, "
                    "locations, qualifications, and employer timestamp"
                ),
                "posted_at": posting.posted_at,
                "posting_date_evidence": (
                    "Official Google Careers structured job record employer timestamp (Pacific date)."
                ),
            }
        )
        (created if was_created else refreshed).append(job)
    return {
        "source": GOOGLE_CAREERS_URL,
        "checked_at": checked_at,
        "pages_fetched": fetched_pages,
        "unique_postings_seen": len(seen),
        "created": created,
        "refreshed": refreshed,
        "skipped": skipped,
    }

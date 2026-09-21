from __future__ import annotations

import html
import json
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .core import JobStore
from .google_careers import PACIFIC, USER_AGENT, is_within_business_days


MAX_RESPONSE_BYTES = 12_000_000
SEARCH_TERMS = (
    "data scientist",
    "applied scientist",
    "research scientist",
    "machine learning engineer",
    "research engineer",
    "AI engineer",
)


@dataclass(frozen=True)
class CompanyPosting:
    source_job_id: str
    title: str
    company: str
    locations: tuple[str, ...]
    url: str
    posted_at: str
    description: str
    source: str


GREENHOUSE_BOARDS = {
    "Airbnb": "airbnb",
    "DoorDash": "doordashusa",
    "Roblox": "roblox",
    "Waymo": "waymo",
    "Instacart": "instacart",
    "Reddit": "reddit",
}

WORKDAY_SITES = {
    "Adobe": ("adobe.wd5.myworkdayjobs.com", "adobe", "external_experienced"),
    "NVIDIA": ("nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"),
}


def _ssl_context() -> ssl.SSLContext:
    for ca_file in (Path("/etc/ssl/cert.pem"), Path("/etc/ssl/certs/ca-certificates.crt")):
        if ca_file.is_file():
            return ssl.create_default_context(cafile=str(ca_file))
    return ssl.create_default_context()


def _request(url: str, *, payload: dict[str, object] | None = None, timeout: float = 45.0) -> bytes:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers)
    with urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        result = response.read(MAX_RESPONSE_BYTES + 1)
    if len(result) > MAX_RESPONSE_BYTES:
        raise ValueError(f"career response exceeded the safety limit: {url}")
    return result


def _json(url: str, *, payload: dict[str, object] | None = None) -> dict[str, object]:
    return json.loads(_request(url, payload=payload))


def _text(value: object) -> str:
    decoded = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", decoded)).strip()


def _iso_date(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(PACIFIC).date().isoformat()


def _employer_date(value: object) -> str:
    raw = str(value or "").strip()
    for parser in (
        lambda text: datetime.fromisoformat(text.replace("Z", "+00:00")),
        lambda text: datetime.strptime(text, "%B %d, %Y"),
        lambda text: datetime.strptime(text, "%b %d, %Y"),
        lambda text: datetime.strptime(text, "%m/%d/%Y"),
    ):
        try:
            return parser(raw).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unsupported employer posting date: {raw!r}")


def _minimum_education(description: str) -> str:
    folded = description.casefold().replace("ph.d.", "phd").replace("ph.d", "phd")
    equivalent = "equivalent experience" in folded or "equivalent practical" in folded
    if "phd" in folded and not equivalent and not any(word in folded for word in ("bachelor", "master")):
        return "phd"
    if "master" in folded and not equivalent and "bachelor" not in folded:
        return "masters"
    if "bachelor" in folded and not equivalent:
        return "bachelors"
    if equivalent:
        return "none"
    return "unknown"


def _sponsorship(description: str) -> str:
    folded = description.casefold()
    negatives = (
        "not eligible for immigration sponsorship",
        "does not provide immigration sponsorship",
        "will not sponsor",
        "unable to sponsor",
        "without sponsorship now or in the future",
    )
    return "does_not_sponsor" if any(value in folded for value in negatives) else "unknown"


def _is_target_title(title: str) -> bool:
    folded = title.casefold()
    excluded = (
        "intern",
        "early career",
        "new grad",
        "manager",
        "director",
        "vice president",
        "principal",
        "senior staff",
    )
    if any(value in folded for value in excluded):
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
    return any(value in folded for value in direct) or (
        "software engineer" in folded
        and any(value in folded for value in ("machine learning", "ai/ml", "agent", "artificial intelligence"))
    )


def _fit_score(title: str) -> int:
    folded = title.casefold()
    if "data scientist" in folded:
        return 94
    if "applied scientist" in folded or "research scientist" in folded:
        return 91
    if "research engineer" in folded:
        return 89
    return 88


def _normalize_location(value: str) -> str:
    folded = value.casefold()
    folded = folded.replace("california", "ca").replace("united states of america", "usa")
    folded = folded.replace("united states", "usa")
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def _allowed_locations(posting: CompanyPosting, requirements: dict[str, object]) -> tuple[str, ...]:
    hard = requirements.get("hard_filters", {})
    configured = hard.get("allowed_locations", []) if isinstance(hard, dict) else []
    allowed = [_normalize_location(str(value)) for value in configured if "remote" not in str(value).casefold()]
    matched: list[str] = []
    for location in posting.locations:
        normalized = _normalize_location(location)
        if any(value in normalized or normalized in value for value in allowed):
            matched.append(location)
    return tuple(dict.fromkeys(matched))


def parse_greenhouse_payload(company: str, payload: dict[str, object]) -> list[CompanyPosting]:
    postings: list[CompanyPosting] = []
    for record in payload.get("jobs", []):
        if not isinstance(record, dict) or not record.get("first_published"):
            continue
        source_id = str(record["id"])
        location = record.get("location", {})
        location_name = str(location.get("name", "")) if isinstance(location, dict) else ""
        postings.append(
            CompanyPosting(
                source_job_id=source_id,
                title=str(record.get("title", "")).strip(),
                company=company,
                locations=tuple(part.strip() for part in location_name.split(";") if part.strip()),
                url=str(record.get("absolute_url", "")),
                posted_at=_iso_date(str(record["first_published"])),
                description=_text(record.get("content", "")),
                source="official Greenhouse board",
            )
        )
    return postings


def fetch_greenhouse(company: str, board: str) -> list[CompanyPosting]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{quote(board)}/jobs?content=true"
    return parse_greenhouse_payload(company, _json(url))


def fetch_workday(company: str, host: str, tenant: str, site: str) -> list[CompanyPosting]:
    base = f"https://{host}/wday/cxs/{tenant}/{site}"
    summaries: dict[str, dict[str, object]] = {}
    for term in SEARCH_TERMS:
        result = _json(
            f"{base}/jobs",
            payload={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term},
        )
        for record in result.get("jobPostings", []):
            if isinstance(record, dict) and record.get("externalPath"):
                summaries[str(record["externalPath"])] = record
    postings: list[CompanyPosting] = []
    for path, summary in summaries.items():
        title = str(summary.get("title", ""))
        if not _is_target_title(title):
            continue
        detail = _json(f"{base}{path}").get("jobPostingInfo", {})
        if not isinstance(detail, dict) or not detail.get("startDate") or not detail.get("externalUrl"):
            continue
        locations = tuple(
            part.strip()
            for part in re.split(r"\s*;\s*|\s+and\s+", str(detail.get("location", summary.get("locationsText", ""))))
            if part.strip()
        )
        postings.append(
            CompanyPosting(
                source_job_id=str(detail.get("jobReqId") or path.rsplit("_", 1)[-1]),
                title=str(detail.get("title") or title),
                company=company,
                locations=locations,
                url=str(detail["externalUrl"]),
                posted_at=str(detail["startDate"])[:10],
                description=_text(detail.get("jobDescription", "")),
                source="official Workday job record",
            )
        )
    return postings


def fetch_snowflake() -> list[CompanyPosting]:
    seen: dict[str, CompanyPosting] = {}
    for term in SEARCH_TERMS:
        url = "https://careers.snowflake.com/us/en/search-results?" + urlencode(
            {"keywords": term, "from": 0, "s": 1}
        )
        page = _request(url).decode("utf-8", errors="replace")
        match = re.search(r"phApp\.ddo\s*=\s*(\{.*?\});\s*phApp\.experimentData", page, re.DOTALL)
        if not match:
            raise ValueError("Snowflake Careers page did not expose its structured search data")
        payload = json.loads(match.group(1)).get("eagerLoadRefineSearch", {})
        jobs = payload.get("data", {}).get("jobs", []) if isinstance(payload, dict) else []
        for record in jobs:
            if not isinstance(record, dict) or not record.get("postedDate"):
                continue
            source_id = str(record.get("jobSeqNo") or record.get("reqId") or record.get("jobId"))
            raw_locations = record.get("multi_location") or record.get("locations") or []
            if isinstance(raw_locations, str):
                raw_locations = [raw_locations]
            description = " ".join(
                str(record.get(key, "")) for key in ("descriptionTeaser", "ml_skills", "category")
            )
            seen[source_id] = CompanyPosting(
                source_job_id=source_id,
                title=str(record.get("title", "")),
                company="Snowflake",
                locations=tuple(_text(value) for value in raw_locations if _text(value)),
                url=f"https://careers.snowflake.com/us/en/job/{source_id}",
                posted_at=_employer_date(record["postedDate"]),
                description=_text(description),
                source="official Snowflake Careers structured search record",
            )
    return list(seen.values())


def fetch_amazon() -> list[CompanyPosting]:
    seen: dict[str, CompanyPosting] = {}
    for term in SEARCH_TERMS:
        url = "https://www.amazon.jobs/en/search.json?" + urlencode(
            {"base_query": term, "result_limit": 100, "sort": "recent"}
        )
        for record in _json(url).get("jobs", []):
            if not isinstance(record, dict) or not record.get("posted_date"):
                continue
            source_id = str(record.get("id_icims") or record.get("id"))
            description = " ".join(
                str(record.get(key, ""))
                for key in ("description", "basic_qualifications", "preferred_qualifications")
            )
            location = str(record.get("normalized_location") or record.get("location", ""))
            seen[source_id] = CompanyPosting(
                source_job_id=source_id,
                title=str(record.get("title", "")),
                company="Amazon",
                locations=(location,) if location else (),
                url=f"https://www.amazon.jobs{record.get('job_path', '')}",
                posted_at=_employer_date(record["posted_date"]),
                description=_text(description),
                source="official Amazon Jobs search record",
            )
    return list(seen.values())


def parse_apple_page(page: str) -> list[CompanyPosting]:
    match = re.search(
        r"window\.__staticRouterHydrationData\s*=\s*JSON\.parse\((\"(?:\\.|[^\"\\])*\")\);",
        page,
    )
    if not match:
        raise ValueError("Apple Jobs page did not expose its structured search data")
    payload = json.loads(json.loads(match.group(1)))["loaderData"]["search"]
    postings: list[CompanyPosting] = []
    for record in payload.get("searchResults", []):
        locations = tuple(
            str(value.get("name", "")).strip()
            for value in record.get("locations", [])
            if isinstance(value, dict) and value.get("name")
        )
        req_id = str(record.get("reqId") or record.get("positionId"))
        slug = str(record.get("transformedPostingTitle") or "job")
        postings.append(
            CompanyPosting(
                source_job_id=req_id,
                title=str(record.get("postingTitle", "")),
                company="Apple",
                locations=locations,
                url=f"https://jobs.apple.com/en-us/details/{req_id}/{slug}",
                posted_at=_employer_date(record.get("postingDate") or record.get("postDateInGMT")),
                description=_text(record.get("jobSummary", "")),
                source="official Apple Jobs structured search record",
            )
        )
    return postings


def fetch_apple() -> list[CompanyPosting]:
    seen: dict[str, CompanyPosting] = {}
    for term in SEARCH_TERMS:
        for page_number in range(1, 4):
            url = "https://jobs.apple.com/en-us/search?" + urlencode(
                {"search": term, "sort": "newest", "page": page_number}
            )
            for posting in parse_apple_page(_request(url).decode("utf-8", errors="replace")):
                seen[posting.source_job_id] = posting
    return list(seen.values())


SOURCE_FETCHERS: tuple[tuple[str, Callable[[], list[CompanyPosting]]], ...] = (
    *((company, lambda company=company, board=board: fetch_greenhouse(company, board)) for company, board in GREENHOUSE_BOARDS.items()),
    *((company, lambda company=company, values=values: fetch_workday(company, *values)) for company, values in WORKDAY_SITES.items()),
    ("Snowflake", fetch_snowflake),
    ("Amazon", fetch_amazon),
    ("Apple", fetch_apple),
)


def _save_postings(
    store: JobStore,
    requirements: dict[str, object],
    postings: Iterable[CompanyPosting],
    checked_at: str,
) -> dict[str, object]:
    postings = list(postings)
    existing_ids = {
        (str(job.get("company")), str(job.get("source_job_id")))
        for job in store.list()
        if job.get("source_job_id")
    }
    created: list[dict[str, object]] = []
    refreshed: list[dict[str, object]] = []
    skipped = 0
    for posting in sorted(postings, key=lambda value: (value.posted_at, value.source_job_id), reverse=True):
        locations = _allowed_locations(posting, requirements)
        existing = (posting.company, posting.source_job_id) in existing_ids
        education = _minimum_education(posting.description)
        sponsorship = _sponsorship(posting.description)
        if (
            not locations
            or not _is_target_title(posting.title)
            or education == "phd"
            or sponsorship == "does_not_sponsor"
            or (not existing and not is_within_business_days(posting.posted_at, 2))
        ):
            skipped += 1
            continue
        job, was_created = store.add(
            {
                "company": posting.company,
                "title": posting.title,
                "location": "; ".join(locations),
                "url": posting.url,
                "source_job_id": posting.source_job_id,
                "sponsorship": sponsorship,
                "minimum_education": education,
                "fit_score": _fit_score(posting.title),
                "evidence": (
                    f"Fresh official {posting.company} career-site match for the configured target roles. "
                    f"Employer description excerpt: {posting.description[:420]}"
                ),
                "availability": "active",
                "last_verified_at": checked_at,
                "verification_evidence": (
                    f"{posting.source} returned the exact requisition, title, location, and employer posting date"
                ),
                "posted_at": posting.posted_at,
                "posting_date_evidence": f"Employer posting date from {posting.source}.",
            }
        )
        (created if was_created else refreshed).append(job)
    return {"seen": len(postings), "created": created, "refreshed": refreshed, "skipped": skipped}


def refresh_other_companies(
    store: JobStore,
    requirements: dict[str, object],
    *,
    fetchers: Iterable[tuple[str, Callable[[], list[CompanyPosting]]]] = SOURCE_FETCHERS,
    checked_at: str | None = None,
) -> dict[str, object]:
    checked_at = checked_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    companies: dict[str, object] = {}
    for name, fetcher in fetchers:
        try:
            companies[name] = _save_postings(store, requirements, fetcher(), checked_at)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            companies[name] = {"error": str(exc), "seen": 0, "created": [], "refreshed": [], "skipped": 0}
    return {"checked_at": checked_at, "companies": companies}


def refresh_new_jobs(store: JobStore, requirements: dict[str, object]) -> dict[str, object]:
    from .google_careers import refresh_google_jobs

    google = refresh_google_jobs(store, requirements)
    others = refresh_other_companies(store, requirements, checked_at=str(google["checked_at"]))
    return {"checked_at": google["checked_at"], "Google Careers": google, **others}

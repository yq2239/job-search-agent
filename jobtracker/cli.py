from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import JobStore, VALID_AVAILABILITY, VALID_STATUSES, load_json
from .paths import (
    EXAMPLE_STATE_ROOT,
    StatePaths,
    ensure_external_state_dir,
    initialize_state,
    resolve_state_paths,
)
from .verification import verify_job_url


def print_json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobtracker")
    parser.add_argument(
        "--state-dir",
        help="private state directory (overrides JOBTRACKER_STATE_DIR and .jobtracker.json)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize a private state directory")
    init.add_argument(
        "--from-dir",
        type=Path,
        default=EXAMPLE_STATE_ROOT,
        help="copy state from this directory instead of the fictional examples",
    )
    sub.add_parser("state-path", help="show the resolved private state directory")

    add = sub.add_parser("add-job", help="add and evaluate one opening")
    add.add_argument("--company", required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--location", required=True)
    add.add_argument("--url", required=True)
    add.add_argument("--source-job-id")
    add.add_argument(
        "--sponsorship",
        choices=["sponsors", "does_not_sponsor", "unknown"],
        default="unknown",
    )
    add.add_argument(
        "--min-education",
        choices=["none", "high_school", "associates", "bachelors", "masters", "phd", "unknown"],
        default="unknown",
    )
    add.add_argument("--fit-score", type=int, choices=range(0, 101), default=0, metavar="0..100")
    add.add_argument("--evidence", default="")

    recommendations = sub.add_parser("recommendations", help="list eligible non-terminal jobs")
    recommendations.add_argument("--minimum-score", type=int)

    status = sub.add_parser("set-status", help="record an application decision")
    status.add_argument("job_id")
    status.add_argument("status", choices=sorted(VALID_STATUSES))
    status.add_argument("--note", default="")

    note = sub.add_parser("add-note", help="append a note to one job")
    note.add_argument("job_id")
    note.add_argument("--note", required=True)

    web = sub.add_parser("web", help="run the private local dashboard")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--no-open", action="store_true")

    history = sub.add_parser("history", help="show one job and its status history")
    history.add_argument("job_id")

    sub.add_parser("list-companies", help="show companies of interest")
    sub.add_parser("validate", help="validate required files and stored records")
    sub.add_parser("verify-jobs", help="live-check all official posting URLs")
    return parser


def validate(paths: StatePaths | None = None) -> list[str]:
    paths = paths or resolve_state_paths()
    errors: list[str] = []
    for path in (paths.jobs, paths.requirements, paths.matching, paths.companies, paths.career):
        try:
            load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")
    if not paths.resume.is_file():
        errors.append(f"{paths.resume}: file is missing")
    if errors:
        return errors
    jobs = load_json(paths.jobs).get("jobs")
    if not isinstance(jobs, list):
        errors.append(f"{paths.jobs}: jobs must be a list")
        return errors
    ids: set[str] = set()
    urls: set[str] = set()
    for index, job in enumerate(jobs):
        prefix = f"{paths.jobs} jobs[{index}]"
        if job.get("id") in ids:
            errors.append(f"{prefix}: duplicate id {job.get('id')}")
        if job.get("url") in urls:
            errors.append(f"{prefix}: duplicate URL {job.get('url')}")
        ids.add(job.get("id"))
        urls.add(job.get("url"))
        if job.get("status") not in VALID_STATUSES:
            errors.append(f"{prefix}: invalid status {job.get('status')}")
        if job.get("availability") not in VALID_AVAILABILITY:
            errors.append(f"{prefix}: invalid or missing availability")
        if not job.get("last_verified_at"):
            errors.append(f"{prefix}: last_verified_at is required")
        if not job.get("verification_evidence"):
            errors.append(f"{prefix}: verification_evidence is required")
        notes = job.get("notes", [])
        if not isinstance(notes, list):
            errors.append(f"{prefix}: notes must be a list")
            continue
        for note in notes:
            if not all(note.get(key) for key in ("id", "at", "body")):
                errors.append(f"{prefix}: each note requires id, at, and body")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = resolve_state_paths(args.state_dir)
    try:
        ensure_external_state_dir(paths.root)
        if args.command == "init":
            initialize_state(paths, source_root=args.from_dir)
            print_json({"initialized": True, "state_dir": str(paths.root)})
            return 0
        if args.command == "state-path":
            print(str(paths.root))
            return 0

        store = JobStore(paths.jobs, paths.requirements)
        if args.command == "add-job":
            verification = verify_job_url(args.url, args.title)
            if verification.availability != "active":
                raise ValueError(verification.verification_evidence)
            job, created = store.add(
                {
                    "company": args.company,
                    "title": args.title,
                    "location": args.location,
                    "url": args.url,
                    "source_job_id": args.source_job_id,
                    "sponsorship": args.sponsorship,
                    "minimum_education": args.min_education,
                    "fit_score": args.fit_score,
                    "evidence": args.evidence,
                    **verification.as_dict(),
                }
            )
            print_json({"created": created, "job": job})
        elif args.command == "recommendations":
            configured = load_json(paths.matching)["minimum_recommendation_score"]
            minimum = configured if args.minimum_score is None else args.minimum_score
            print_json(store.recommendations(minimum))
        elif args.command == "set-status":
            print_json(store.set_status(args.job_id, args.status, args.note))
        elif args.command == "add-note":
            print_json(store.add_note(args.job_id, args.note))
        elif args.command == "web":
            from .web import run_server

            run_server(
                store,
                args.host,
                args.port,
                open_browser=not args.no_open,
                companies_path=paths.companies,
            )
        elif args.command == "history":
            print_json(store.get(args.job_id))
        elif args.command == "list-companies":
            print_json(load_json(paths.companies)["companies"])
        elif args.command == "validate":
            errors = validate(paths)
            if errors:
                print_json({"valid": False, "errors": errors})
                return 1
            print_json({"valid": True})
        elif args.command == "verify-jobs":
            results = []
            for job in store.list():
                verification = verify_job_url(job["url"], job["title"])
                updated = store.record_verification(job["id"], verification.as_dict())
                results.append(
                    {
                        "id": updated["id"],
                        "title": updated["title"],
                        **verification.as_dict(),
                    }
                )
            print_json(results)
    except (KeyError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0

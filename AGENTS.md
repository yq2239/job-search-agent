# Agent operating rules

This repository tracks a private job search. Treat all candidate data as sensitive.

1. Run `python3 -m jobtracker state-path` to locate the active private state directory. Read its `profile/requirements.json`, `profile/career.json`, and `profile/matching.json` before recommending any role.
2. Hard requirements in the active private state are absolute. Never recommend a role that fails its configured location, sponsorship, education, or other eligibility rules.
3. Missing evidence is not evidence of eligibility. Put jobs with unknown sponsorship, location, or education requirements in `manual_review`.
4. Use `python3 -m jobtracker add-job` to preserve stable IDs and deduplication. Do not edit job IDs manually.
5. Use `python3 -m jobtracker set-status` to record user decisions. Preserve status history.
6. Link every job to its source and record concise evidence for sponsorship, education, and location when available.
7. Never submit an application or contact a recruiter without explicit user approval.
8. Never store identity documents, government identifiers, immigration receipt numbers, or account credentials.
9. Keep real candidate state outside the repository. Only fictional examples belong under `examples/state/`.
10. Run `python3 -m jobtracker validate` and the test suite after changing private state or code.

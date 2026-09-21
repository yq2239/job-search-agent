import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from jobtracker.core import JobStore
from jobtracker.google_careers import parse_google_careers_html, refresh_google_jobs


def google_page(records):
    data = [records, None, len(records), 20]
    return (
        "<html><script>AF_initDataCallback({key: 'ds:1', hash: '2', data:"
        + json.dumps(data)
        + ", sideChannel: {}});</script></html>"
    )


def record(
    job_id="123456789",
    title="Senior Data Scientist, AI",
    company="Google",
    location="Mountain View, CA, USA",
    timestamp=1789952400,
    minimum="Bachelor's degree or equivalent practical experience.",
):
    value = [None] * 21
    value[0] = job_id
    value[1] = title
    value[4] = [None, f"<h3>Minimum qualifications:</h3><p>{minimum}</p>"]
    value[7] = company
    value[9] = [[location, [location], "Mountain View", None, "CA", "US"]]
    value[10] = [None, "Build production machine learning systems."]
    value[12] = [timestamp, 0]
    value[19] = value[4]
    return value


class GoogleCareersTests(unittest.TestCase):
    def test_parser_uses_official_timestamp_and_canonical_posting_url(self):
        posting = parse_google_careers_html(google_page([record()]))[0]
        self.assertEqual(posting.source_job_id, "123456789")
        self.assertEqual(posting.minimum_education, "none")
        self.assertRegex(posting.posted_at, r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(
            posting.url,
            "https://www.google.com/about/careers/applications/jobs/results/123456789-senior-data-scientist-ai",
        )

    def test_refresh_adds_matching_bay_area_role_and_deduplicates_queries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jobs = root / "jobs.json"
            requirements = root / "requirements.json"
            jobs.write_text('{"schema_version": 1, "jobs": []}\n')
            requirement_data = {
                "hard_filters": {
                    "requires_employer_sponsorship_or_h1b_transfer": True,
                    "allowed_locations": ["Mountain View, CA"],
                    "exclude_if_minimum_education_is": ["phd"],
                },
                "unknown_fact_policy": "manual_review",
            }
            requirements.write_text(json.dumps(requirement_data))
            store = JobStore(jobs, requirements)
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            fetcher = lambda query, page: google_page([record(timestamp=current_timestamp)])
            result = refresh_google_jobs(
                store,
                requirement_data,
                fetcher=fetcher,
                checked_at="2026-09-21T12:00:00+00:00",
            )
            self.assertEqual(result["unique_postings_seen"], 1)
            self.assertEqual(len(result["created"]), 1)
            saved = store.list()[0]
            self.assertEqual(saved["status"], "manual_review")
            self.assertEqual(saved["source_job_id"], "123456789")
            self.assertIn("Official Google Careers", saved["evidence"])

    def test_refresh_excludes_phd_only_and_junior_or_management_roles(self):
        records = [
            record("1", "Data Scientist Intern"),
            record("2", "Data Science Manager"),
            record("3", "Research Scientist", minimum="PhD in Computer Science."),
        ]
        parsed = parse_google_careers_html(google_page(records))
        self.assertEqual([item.minimum_education for item in parsed], ["none", "none", "phd"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from jobtracker.company_careers import (
    CompanyPosting,
    parse_apple_page,
    parse_greenhouse_payload,
    refresh_other_companies,
)
from jobtracker.core import JobStore


class CompanyCareerTests(unittest.TestCase):
    def test_greenhouse_uses_first_published(self):
        postings = parse_greenhouse_payload(
            "Airbnb",
            {
                "jobs": [
                    {
                        "id": 123,
                        "title": "Senior Data Scientist",
                        "absolute_url": "https://example.test/123",
                        "first_published": "2026-09-21T12:00:00Z",
                        "location": {"name": "San Francisco, California, United States"},
                        "content": "Bachelor's degree and Python",
                    }
                ]
            },
        )
        self.assertEqual(postings[0].posted_at, "2026-09-21")
        self.assertEqual(postings[0].source_job_id, "123")

    def test_apple_parser_reads_employer_date(self):
        data = {
            "loaderData": {
                "search": {
                    "searchResults": [
                        {
                            "reqId": "2001-0001",
                            "postingTitle": "Machine Learning Engineer",
                            "transformedPostingTitle": "machine-learning-engineer",
                            "postingDate": "Sep 21, 2026",
                            "locations": [{"name": "Cupertino, California, United States"}],
                            "jobSummary": "Build production ML systems.",
                        }
                    ]
                }
            }
        }
        encoded = json.dumps(json.dumps(data))
        posting = parse_apple_page(f"<script>window.__staticRouterHydrationData = JSON.parse({encoded});</script>")[0]
        self.assertEqual(posting.company, "Apple")
        self.assertEqual(posting.posted_at, "2026-09-21")

    def test_refresh_adds_recent_match_and_keeps_unknowns_for_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jobs = root / "jobs.json"
            requirements = root / "requirements.json"
            jobs.write_text('{"jobs": []}', encoding="utf-8")
            requirements.write_text(
                json.dumps(
                    {
                        "hard_filters": {
                            "allowed_locations": ["San Francisco, CA"],
                            "requires_employer_sponsorship_or_h1b_transfer": True,
                            "exclude_if_minimum_education_is": ["phd"],
                        },
                        "unknown_fact_policy": "manual_review",
                    }
                ),
                encoding="utf-8",
            )
            posting = CompanyPosting(
                source_job_id="A1",
                title="Senior Data Scientist",
                company="Example",
                locations=("San Francisco, California, United States",),
                url="https://example.test/jobs/A1",
                posted_at="2026-09-21",
                description="Use Python and statistics.",
                source="official test feed",
            )
            result = refresh_other_companies(
                JobStore(jobs, requirements),
                json.loads(requirements.read_text()),
                fetchers=(("Example", lambda: [posting]),),
                checked_at="2026-09-21T18:00:00+00:00",
            )
            created = result["companies"]["Example"]["created"]
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0]["status"], "manual_review")
            self.assertEqual(created[0]["posted_at"], "2026-09-21")


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from jobtracker.core import JobStore, canonicalize_url, evaluate_job, make_job_id


REQUIREMENTS = {
    "hard_filters": {
        "requires_employer_sponsorship_or_h1b_transfer": True,
        "allowed_locations": ["San Francisco, CA", "Mountain View, CA"],
        "exclude_if_minimum_education_is": ["phd"],
    },
    "unknown_fact_policy": "manual_review",
}


class EligibilityTests(unittest.TestCase):
    def job(self, **overrides):
        value = {
            "location": "San Francisco, CA",
            "sponsorship": "sponsors",
            "minimum_education": "bachelors",
        }
        value.update(overrides)
        return value

    def test_hard_filters(self):
        self.assertEqual(evaluate_job(self.job(location="New York, NY"), REQUIREMENTS)[0], "ineligible")
        self.assertEqual(
            evaluate_job(self.job(sponsorship="does_not_sponsor"), REQUIREMENTS)[0], "ineligible"
        )
        self.assertEqual(evaluate_job(self.job(minimum_education="phd"), REQUIREMENTS)[0], "ineligible")

    def test_unknown_sponsorship_requires_review(self):
        result, reasons = evaluate_job(self.job(sponsorship="unknown"), REQUIREMENTS)
        self.assertEqual(result, "manual_review")
        self.assertTrue(any("unverified" in reason for reason in reasons))

    def test_unknown_location_requires_review(self):
        result, reasons = evaluate_job(self.job(location="unknown"), REQUIREMENTS)
        self.assertEqual(result, "manual_review")
        self.assertTrue(any("location is unknown" in reason for reason in reasons))

    def test_sponsorship_is_ignored_when_not_required(self):
        requirements = json.loads(json.dumps(REQUIREMENTS))
        requirements["hard_filters"]["requires_employer_sponsorship_or_h1b_transfer"] = False
        self.assertEqual(
            evaluate_job(self.job(sponsorship="does_not_sponsor"), requirements)[0],
            "eligible",
        )

    def test_eligible(self):
        self.assertEqual(evaluate_job(self.job(), REQUIREMENTS)[0], "eligible")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.jobs_path = root / "jobs.json"
        self.requirements_path = root / "requirements.json"
        self.jobs_path.write_text('{"schema_version": 1, "jobs": []}\n')
        self.requirements_path.write_text(json.dumps(REQUIREMENTS))
        self.store = JobStore(self.jobs_path, self.requirements_path)

    def tearDown(self):
        self.temp.cleanup()

    def candidate(self, url="https://example.com/jobs/123?utm_source=test"):
        return {
            "company": "Example",
            "title": "Software Engineer",
            "location": "Mountain View, CA",
            "url": url,
            "sponsorship": "sponsors",
            "minimum_education": "bachelors",
            "fit_score": 80,
            "availability": "active",
            "last_verified_at": "2026-08-14T12:00:00+00:00",
            "verification_evidence": "official page contained title and Apply action",
        }

    def test_id_is_stable_and_url_is_canonical(self):
        first, created = self.store.add(self.candidate())
        second, created_again = self.store.add(self.candidate("https://example.com/jobs/123#top"))
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["url"], "https://example.com/jobs/123")

    def test_status_history(self):
        job, _ = self.store.add(self.candidate())
        updated = self.store.set_status(job["id"], "applied", "submitted")
        self.assertEqual(updated["status"], "applied")
        self.assertEqual(updated["history"][-1]["note"], "submitted")
        self.assertEqual(self.store.recommendations(60), [])

    def test_notes_are_append_only(self):
        job, _ = self.store.add(self.candidate())
        updated = self.store.add_note(job["id"], "Referral requested")
        self.assertEqual(updated["notes"][0]["body"], "Referral requested")
        self.assertRegex(updated["notes"][0]["id"], r"^NOTE-[0-9A-F]{12}$")

    def test_blank_note_is_rejected(self):
        job, _ = self.store.add(self.candidate())
        with self.assertRaises(ValueError):
            self.store.add_note(job["id"], "   ")

    def test_identifier_format(self):
        value = make_job_id("Google", "SWE", "SF", "https://example.com/1")
        self.assertRegex(value, r"^JOB-[0-9A-F]{12}$")

    def test_unverified_job_is_rejected(self):
        candidate = self.candidate()
        candidate.pop("last_verified_at")
        with self.assertRaises(ValueError):
            self.store.add(candidate)

    def test_closed_verification_updates_status_history(self):
        job, _ = self.store.add(self.candidate())
        updated = self.store.record_verification(
            job["id"],
            {
                "availability": "closed",
                "last_verified_at": "2026-08-14T13:00:00+00:00",
                "verification_evidence": "official page reports job not found",
            },
        )
        self.assertEqual(updated["status"], "closed")
        self.assertEqual(updated["history"][-1]["status"], "closed")

    def test_canonicalize_url_drops_tracking(self):
        self.assertEqual(
            canonicalize_url("HTTPS://Example.COM/jobs/1/?utm_campaign=x#apply"),
            "https://example.com/jobs/1",
        )

    def test_canonicalize_url_preserves_job_identity_query(self):
        self.assertEqual(
            canonicalize_url(
                "https://careers.snap.com/job?lang=en-US&id=R123&utm_source=search"
            ),
            "https://careers.snap.com/job?id=R123",
        )
        self.assertEqual(
            canonicalize_url("https://careers.withwaymo.com/jobs?gh_jid=456"),
            "https://careers.withwaymo.com/jobs?gh_jid=456",
        )

    def test_same_source_refreshes_canonical_url_without_losing_history(self):
        candidate = self.candidate("https://example.com/jobs?gh_jid=123")
        candidate["source_job_id"] = "123"
        job, _ = self.store.add(candidate)
        self.store.set_status(job["id"], "interested", "keep me")
        refreshed = self.candidate("https://example.com/posting?gh_jid=123")
        refreshed["source_job_id"] = "123"
        updated, created = self.store.add(refreshed)
        self.assertFalse(created)
        self.assertEqual(updated["url"], "https://example.com/posting?gh_jid=123")
        self.assertEqual(updated["status"], "interested")
        self.assertEqual(updated["history"][-1]["note"], "keep me")


if __name__ == "__main__":
    unittest.main()

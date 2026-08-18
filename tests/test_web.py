import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from jobtracker.core import JobStore
from jobtracker.web import company_icon_urls, create_server


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        jobs = root / "jobs.json"
        requirements = root / "requirements.json"
        self.companies = root / "companies.json"
        jobs.write_text('{"schema_version": 1, "jobs": []}\n')
        self.companies.write_text(json.dumps({"schema_version": 1, "companies": [{
            "name": "Netflix", "careers_url": "https://jobs.netflix.com/search"
        }]}))
        requirements.write_text(json.dumps({"hard_filters": {
            "allowed_locations": ["Mountain View, CA"],
            "exclude_if_minimum_education_is": ["phd"]},
            "unknown_fact_policy": "manual_review"}))
        self.store = JobStore(jobs, requirements)
        self.job, _ = self.store.add({"company": "Example", "title": "Research Engineer",
            "location": "Mountain View, CA", "url": "https://example.com/jobs/1",
            "sponsorship": "sponsors", "minimum_education": "bachelors", "fit_score": 90,
            "availability": "active", "last_verified_at": "2026-08-14T12:00:00+00:00",
            "verification_evidence": "official page contained title and Apply action"})
        self.server = create_server(self.store, "127.0.0.1", 0, self.companies)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1])

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, payload=None):
        body = json.dumps(payload) if payload is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        self.connection.request(method, path, body=body, headers=headers)
        response = self.connection.getresponse()
        return response.status, response.read()

    def test_dashboard_and_jobs_api(self):
        self.connection.request("GET", "/")
        response = self.connection.getresponse()
        body = response.read()
        self.assertEqual(response.status, 200)
        self.assertIn("img-src 'self' data: https:", response.getheader("Content-Security-Policy"))
        self.assertIn(b"Smart Job Tracker", body)
        self.assertIn(b'id="companyFilter"', body)
        self.assertIn(b"Referred", body)
        self.assertIn(b"Pending review", body)
        self.assertIn(b"metric metric-review", body)
        self.assertIn(b'id="pendingCompanies"', body)
        self.assertIn(b'id="discoveredCompanies"', body)
        self.assertIn(b'id="interestedCompanies"', body)
        self.assertIn(b'id="appliedCompanies"', body)
        self.assertIn(b'id="referredCompanies"', body)
        self.assertIn(b'class="metric-company"', body)
        self.assertIn(b'data-company="${esc(company)}"', body)
        self.assertIn(b"$('statusMetrics').addEventListener", body)
        self.assertIn(b"$('statusFilter').value=''", body)
        self.assertIn(b".metric-review{grid-column:span 2", body)
        labels = [b"Pending review", b"Discovered", b"Interested", b"Applied", b"Referred"]
        positions = [body.index(label) for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertIn(b"company-name", body)
        self.assertIn(b"background-image:url", body)
        self.assertIn(b"function companyMark", body)
        self.assertIn(b"function automaticCompanyIcon", body)
        self.assertIn(b"function companyFallback", body)
        self.assertIn(b"company-logo-auto", body)
        self.assertIn(b"state.company_icons", body)
        self.assertIn(b"data:image/png;base64", body)
        self.assertIn(b'aria-label="Google DeepMind"', body)
        self.assertIn(b"logos['Google DeepMind']", body)
        self.assertIn(b"logos.Microsoft", body)
        self.assertIn(b'aria-label="Microsoft"', body)
        self.assertIn(b"logos.Reddit", body)
        self.assertIn(b'aria-label="Reddit"', body)
        self.assertIn(b"logos.NVIDIA", body)
        self.assertIn(b'aria-label="NVIDIA"', body)
        self.assertIn(b"logos.TikTok", body)
        self.assertIn(b'aria-label="TikTok"', body)
        self.assertIn(b"logos.ByteDance", body)
        self.assertIn(b'aria-label="ByteDance"', body)
        self.assertIn(b"logos.Adobe", body)
        self.assertIn(b'aria-label="Adobe"', body)
        self.assertIn(b"role-line", body)
        self.assertIn(b"Status history", body)
        self.assertIn(b"status-chip", body)
        self.assertIn(b".status-discovered{background:#e8f3ff", body)
        status, body = self.request("GET", "/api/jobs")
        payload = json.loads(body)
        self.assertEqual(payload["jobs"][0]["id"], self.job["id"])
        self.assertEqual(payload["company_icons"]["Netflix"], "https://jobs.netflix.com/favicon.ico")

    def test_company_icons_use_safe_configured_careers_hosts(self):
        self.assertEqual(
            company_icon_urls(self.companies),
            {"Netflix": "https://jobs.netflix.com/favicon.ico"},
        )
        self.companies.write_text(json.dumps({"companies": [
            {"name": "Local", "careers_url": "https://127.0.0.1/jobs"},
            {"name": "Insecure", "careers_url": "http://example.com/jobs"},
        ]}))
        self.assertEqual(company_icon_urls(self.companies), {})

    def test_status_and_note_mutations(self):
        path = f"/api/jobs/{self.job['id']}"
        status, body = self.request("PATCH", path + "/status", {"status": "applied", "note": "Submitted"})
        self.assertEqual(status, 200)
        updated = json.loads(body)["job"]
        self.assertEqual(updated["status"], "applied")
        self.assertEqual(updated["history"][-1]["note"], "Submitted")
        status, body = self.request("POST", path + "/notes", {"body": "Referral pending"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["job"]["notes"][0]["body"], "Referral pending")

    def test_company_icon_override_takes_priority(self):
        self.companies.write_text(json.dumps({"companies": [{
            "name": "TikTok",
            "careers_url": "https://lifeattiktok.com/search/",
            "icon_url": "https://www.tiktok.com/favicon.ico",
        }]}))
        self.assertEqual(
            company_icon_urls(self.companies),
            {"TikTok": "https://www.tiktok.com/favicon.ico"},
        )


if __name__ == "__main__":
    unittest.main()

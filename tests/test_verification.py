import unittest

from jobtracker.verification import (
    classify_greenhouse_job_json,
    classify_official_posting_html,
    classify_workday_job_json,
    greenhouse_api_url,
    workday_api_url,
)


class VerificationTests(unittest.TestCase):
    def test_waymo_wrapper_uses_identity_preserving_greenhouse_api(self):
        self.assertEqual(
            greenhouse_api_url("https://careers.withwaymo.com/jobs?gh_jid=7488596"),
            "https://boards-api.greenhouse.io/v1/boards/waymo/jobs/7488596?content=true",
        )

    def test_greenhouse_api_requires_exact_live_posting(self):
        payload = '{"id":7488596,"title":"Senior ML Engineer","absolute_url":"https://example"}'
        self.assertEqual(classify_greenhouse_job_json(payload, "Senior ML Engineer")[0], "active")
        self.assertEqual(classify_greenhouse_job_json(payload, "Different Role")[0], "unknown")

    def test_workday_url_uses_official_structured_posting_api(self):
        self.assertEqual(
            workday_api_url(
                "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/"
                "job/US-CA-Santa-Clara/Senior-AI-Engineer_JR123"
            ),
            "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/"
            "NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Senior-AI-Engineer_JR123",
        )

    def test_workday_api_requires_exact_open_posting(self):
        payload = '''{"jobPostingInfo":{"title":"Senior AI Engineer","posted":true,
        "canApply":true,"jobReqId":"JR123","externalUrl":"https://example"}}'''
        self.assertEqual(classify_workday_job_json(payload, "Senior AI Engineer")[0], "active")
        self.assertEqual(classify_workday_job_json(payload, "Different Role")[0], "unknown")

    def test_workday_api_rejects_non_applyable_posting(self):
        payload = '''{"jobPostingInfo":{"title":"Senior AI Engineer","posted":true,
        "canApply":false,"jobReqId":"JR123","externalUrl":"https://example"}}'''
        self.assertEqual(classify_workday_job_json(payload, "Senior AI Engineer")[0], "closed")

    def test_active_page_requires_expected_title_and_apply(self):
        page = "<main><h1>Research Engineer, DeepMind</h1><button>Apply</button></main>"
        availability, _ = classify_official_posting_html(page, "Research Engineer, DeepMind")
        self.assertEqual(availability, "active")

    def test_taken_down_page_is_closed(self):
        page = "<main><h1>Job not found.</h1><p>This job may have been taken down.</p></main>"
        availability, _ = classify_official_posting_html(page, "Research Engineer, DeepMind")
        self.assertEqual(availability, "closed")

    def test_wrong_title_is_unknown(self):
        page = "<main><h1>Some Other Role</h1><button>Apply</button></main>"
        availability, _ = classify_official_posting_html(page, "Research Engineer, DeepMind")
        self.assertEqual(availability, "unknown")

    def test_snowflake_closed_page_is_closed(self):
        page = "<main><h1>OH SNAP! THIS JOB HAS BEEN CLOSED.</h1></main>"
        availability, _ = classify_official_posting_html(page, "AI Engineer")
        self.assertEqual(availability, "closed")

    def test_ashby_structured_posting_is_active(self):
        page = '''
        <title>AI Engineer @ Snowflake</title>
        <script type="application/ld+json">
        {"@type":"JobPosting","title":"AI Engineer","directApply":true}
        </script>
        <script>{"isListed":true}</script>
        '''
        availability, _ = classify_official_posting_html(page, "AI Engineer")
        self.assertEqual(availability, "active")


if __name__ == "__main__":
    unittest.main()

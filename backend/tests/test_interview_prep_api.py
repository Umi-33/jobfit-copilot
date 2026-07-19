import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.app.llm.interview_prep_generator import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
)
from backend.app.main import app
from backend.app.storage.database import DATABASE_ENV_VAR
from backend.app.storage.job_record_repository import create_job_record, get_job_record


VALID_PREP = {
    "job_focus": ["AI integration", "frontend delivery", "API collaboration"],
    "likely_questions": [
        {"question": f"Question {index}", "answer_outline": ["Fact one", "Fact two"]}
        for index in range(1, 5)
    ],
    "project_talking_points": [
        {"project_name": "JobFit Copilot", "talking_points": ["Explain saved facts"]}
    ],
    "honest_boundaries": ["No production Agent ownership", "No invented experience"],
    "questions_to_ask": ["Team scope?", "Work schedule?", "Expected ownership?"],
}


def analysis_fixture(projects=None):
    return {
        "total_score": 76,
        "rating": "A-",
        "decision": "可投但需确认",
        "risk_level": "low",
        "unknown_items": ["work schedule"],
        "parsed_profile": {"projects": projects or []},
    }


def action_plan_fixture():
    return {
        "primary_action": "prepare_application",
        "human_approval_required": True,
        "human_checkpoints": [
            {
                "id": "confirm_before_action",
                "question": "Confirm before continuing?",
                "required": True,
                "blocking": True,
                "related_items": ["prepare_application"],
            }
        ],
        "allowed_outputs": ["整理面试准备要点"],
        "blocked_outputs": ["不能编造技能、项目或经历"],
    }


class InterviewPrepApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "interview_prep.sqlite3"
        self.environment = patch.dict(os.environ, {DATABASE_ENV_VAR: str(self.database_path)})
        self.environment.start()
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()
        self.record = create_job_record(
            company_name="Example Company",
            job_title="AI Frontend Engineer",
            city="Shanghai",
            profile_snapshot="Project: JobFit Copilot. Uses Python and FastAPI.",
            jd_text="Integrate an LLM API into a frontend product.",
            analysis=analysis_fixture(
                [{"name": "JobFit Copilot", "tags": ["Python"], "summary": "Saved project"}]
            ),
            action_plan=action_plan_fixture(),
            database_path=self.database_path,
        )

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.environment.stop()
        self.temp_directory.cleanup()

    def endpoint(self, record_id=None):
        return f"/api/records/{record_id or self.record['id']}/interview-prep"

    @patch("backend.app.main.generate_interview_prep", return_value=VALID_PREP)
    def test_success_uses_record_from_repository(self, generator):
        response = self.client.post(self.endpoint(), json={"human_approved": True})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"record_id": self.record["id"], "interview_prep": VALID_PREP})
        supplied_record = generator.call_args.args[0]
        self.assertEqual(supplied_record["profile_snapshot"], self.record["profile_snapshot"])
        self.assertEqual(supplied_record["jd_text"], self.record["jd_text"])
        self.assertEqual(supplied_record["analysis"], self.record["analysis"])
        self.assertEqual(supplied_record["action_plan"], self.record["action_plan"])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_invalid_first_provider_response_retries_and_api_succeeds(self, openai_class):
        invalid_prep = json.loads(json.dumps(VALID_PREP))
        invalid_prep["questions_to_ask"] = ["Too few questions"]
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=json.dumps(invalid_prep)))
                ]
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=json.dumps(VALID_PREP)))
                ]
            ),
        ]
        openai_class.return_value = client

        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "api-test-key-never-sent",
                "GROQ_MODEL": "api-test-model",
                "GROQ_TIMEOUT_SECONDS": "5",
            },
        ):
            with self.assertLogs(
                "backend.app.llm.interview_prep_generator", level="WARNING"
            ):
                response = self.client.post(
                    self.endpoint(),
                    json={"human_approved": True},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"record_id": self.record["id"], "interview_prep": VALID_PREP},
        )
        self.assertEqual(client.chat.completions.create.call_count, 2)

    @patch("backend.app.main.generate_interview_prep")
    def test_human_approval_is_required(self, generator):
        self.assertEqual(self.client.post(self.endpoint(), json={}).status_code, 422)
        response = self.client.post(self.endpoint(), json={"human_approved": False})
        self.assertEqual(response.status_code, 403)
        generator.assert_not_called()

    @patch("backend.app.main.generate_interview_prep")
    def test_request_cannot_upload_saved_analysis_or_plan(self, generator):
        response = self.client.post(
            self.endpoint(),
            json={"human_approved": True, "analysis": {}, "action_plan": {}},
        )
        self.assertEqual(response.status_code, 422)
        generator.assert_not_called()

    @patch("backend.app.main.generate_interview_prep")
    def test_missing_record_returns_404(self, generator):
        response = self.client.post(self.endpoint(9999), json={"human_approved": True})
        self.assertEqual(response.status_code, 404)
        generator.assert_not_called()

    def test_domain_errors_have_safe_http_statuses(self):
        cases = [
            (LLMConfigurationError("LLM service is not configured"), 503),
            (LLMAuthenticationError("LLM service authentication failed"), 503),
            (LLMRateLimitError("LLM service is temporarily rate limited"), 429),
            (LLMTimeoutError("LLM service timed out"), 504),
            (LLMUpstreamError("LLM service request failed"), 502),
            (LLMInvalidResponseError("LLM returned an invalid response"), 502),
        ]
        for error, expected_status in cases:
            with self.subTest(error=type(error).__name__):
                with patch("backend.app.main.generate_interview_prep", side_effect=error):
                    response = self.client.post(self.endpoint(), json={"human_approved": True})
                self.assertEqual(response.status_code, expected_status)
                self.assertNotIn("api_key", response.text.lower())

    @patch("backend.app.main.generate_interview_prep", return_value=VALID_PREP)
    def test_generation_does_not_change_saved_record(self, generator):
        before = get_job_record(self.record["id"], self.database_path)
        response = self.client.post(self.endpoint(), json={"human_approved": True})
        after = get_job_record(self.record["id"], self.database_path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(after["analysis"], before["analysis"])
        self.assertEqual(after["action_plan"], before["action_plan"])
        self.assertEqual(after["status"], before["status"])
        self.assertEqual(after["updated_at"], before["updated_at"])


if __name__ == "__main__":
    unittest.main()

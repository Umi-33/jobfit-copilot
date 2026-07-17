import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic import ValidationError

from backend.app.llm.interview_prep_generator import (
    InterviewPrep,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUpstreamError,
    generate_interview_prep,
)


def record_fixture(projects=None):
    return {
        "company_name": "Example Company",
        "job_title": "AI Frontend Engineer",
        "city": "Shanghai",
        "profile_snapshot": "UNTRUSTED PROFILE TEXT",
        "jd_text": "UNTRUSTED JD TEXT",
        "analysis": {
            "total_score": 76,
            "rating": "A-",
            "decision": "可投但需确认",
            "risk_level": "low",
            "parsed_profile": {"projects": projects or []},
        },
        "action_plan": {
            "human_approval_required": True,
            "allowed_outputs": ["整理面试准备要点"],
            "blocked_outputs": ["不能编造技能、项目或经历"],
            "human_checkpoints": [{"id": "confirm_before_action"}],
        },
    }


def prep_payload(project_name=None):
    projects = []
    if project_name:
        projects.append({"project_name": project_name, "talking_points": ["Use saved facts"]})
    return {
        "job_focus": ["Focus one", "Focus two", "Focus three"],
        "likely_questions": [
            {"question": f"Question {index}", "answer_outline": ["Point one", "Point two"]}
            for index in range(1, 5)
        ],
        "project_talking_points": projects,
        "honest_boundaries": ["Boundary one", "Boundary two"],
        "questions_to_ask": ["Ask one", "Ask two", "Ask three"],
    }


class InterviewPrepGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key-never-sent",
                "OPENAI_MODEL": "configured-test-model",
                "OPENAI_TIMEOUT_SECONDS": "12",
            },
            clear=False,
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def mock_client(self, output):
        client = MagicMock()
        client.responses.parse.return_value = SimpleNamespace(output_parsed=output)
        return client

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_success_uses_responses_parse_store_false_and_saved_input(self, openai_class):
        record = record_fixture([{"name": "JobFit Copilot", "tags": [], "summary": "Saved"}])
        parsed = InterviewPrep.model_validate(prep_payload("JobFit, Copilot"))
        client = self.mock_client(parsed)
        openai_class.return_value = client

        result = generate_interview_prep(record)

        self.assertEqual(result["project_talking_points"][0]["project_name"], "JobFit Copilot")
        openai_class.assert_called_once_with(api_key="test-key-never-sent", timeout=12.0)
        call = client.responses.parse.call_args.kwargs
        self.assertEqual(call["model"], "configured-test-model")
        self.assertIs(call["text_format"], InterviewPrep)
        self.assertIs(call["store"], False)
        self.assertIn("UNTRUSTED PROFILE TEXT", call["input"])
        self.assertIn("UNTRUSTED JD TEXT", call["input"])
        self.assertIn("不能编造技能、项目或经历", call["input"])

    def test_missing_configuration_is_rejected_before_client_creation(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": ""}):
            with patch("backend.app.llm.interview_prep_generator.OpenAI") as openai_class:
                with self.assertRaises(LLMConfigurationError):
                    generate_interview_prep(record_fixture())
                openai_class.assert_not_called()

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_refusal_or_empty_output_is_rejected(self, openai_class):
        openai_class.return_value = self.mock_client(None)
        with self.assertRaises(LLMInvalidResponseError):
            generate_interview_prep(record_fixture())

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_structurally_invalid_output_is_rejected(self, openai_class):
        openai_class.return_value = self.mock_client({"job_focus": ["too short"]})
        with self.assertRaises(LLMInvalidResponseError):
            generate_interview_prep(record_fixture())

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_invented_project_is_rejected(self, openai_class):
        parsed = InterviewPrep.model_validate(prep_payload("Invented Project"))
        openai_class.return_value = self.mock_client(parsed)
        record = record_fixture([{"name": "Real Project", "tags": [], "summary": "Saved"}])
        with self.assertRaises(LLMInvalidResponseError):
            generate_interview_prep(record)

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_no_saved_projects_requires_empty_talking_points(self, openai_class):
        openai_class.return_value = self.mock_client(
            InterviewPrep.model_validate(prep_payload("Invented Project"))
        )
        with self.assertRaises(LLMInvalidResponseError):
            generate_interview_prep(record_fixture())

        openai_class.return_value = self.mock_client(InterviewPrep.model_validate(prep_payload()))
        result = generate_interview_prep(record_fixture())
        self.assertEqual(result["project_talking_points"], [])

    def test_output_model_rejects_extra_fields_and_invalid_counts(self):
        with self.assertRaises(ValidationError):
            InterviewPrep.model_validate({**prep_payload(), "extra": "not allowed"})
        with self.assertRaises(ValidationError):
            InterviewPrep.model_validate({**prep_payload(), "job_focus": ["one"]})

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_provider_exceptions_are_mapped_to_domain_errors(self, openai_class):
        request = httpx.Request("POST", "https://example.invalid")
        response = httpx.Response(401, request=request)
        cases = [
            (AuthenticationError("bad auth", response=response, body=None), LLMAuthenticationError),
            (RateLimitError("limited", response=response, body=None), LLMRateLimitError),
            (APITimeoutError(request), LLMTimeoutError),
            (APIConnectionError(request=request), LLMUpstreamError),
        ]
        for provider_error, domain_error in cases:
            with self.subTest(error=type(provider_error).__name__):
                client = MagicMock()
                client.responses.parse.side_effect = provider_error
                openai_class.return_value = client
                with self.assertRaises(domain_error):
                    generate_interview_prep(record_fixture())


if __name__ == "__main__":
    unittest.main()

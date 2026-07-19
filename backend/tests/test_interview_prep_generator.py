import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)
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
            "decision": "Apply after confirmation",
            "risk_level": "low",
            "parsed_profile": {"projects": projects or []},
        },
        "action_plan": {
            "human_approval_required": True,
            "allowed_outputs": ["Prepare interview talking points"],
            "blocked_outputs": ["Do not invent skills, projects, or experience"],
            "human_checkpoints": [{"id": "confirm_before_action"}],
        },
    }


def prep_payload(project_name=None):
    projects = []
    if project_name:
        projects.append(
            {
                "project_name": project_name,
                "talking_points": ["Use saved facts", "Explain the design", "State boundaries"],
            }
        )
    return {
        "job_focus": ["Focus one", "Focus two", "Focus three", "Focus four"],
        "likely_questions": [
            {
                "question": f"Question {index}",
                "answer_outline": ["Point one", "Point two", "Point three"],
            }
            for index in range(1, 6)
        ],
        "project_talking_points": projects,
        "honest_boundaries": ["Boundary one", "Boundary two", "Boundary three"],
        "questions_to_ask": ["Ask one", "Ask two", "Ask three", "Ask four"],
    }


def assert_strict_objects(test_case, schema):
    """Assert every object rejects extras and requires every declared property."""
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            test_case.assertIs(schema.get("additionalProperties"), False)
            test_case.assertEqual(set(schema.get("required", [])), set(properties))
        for value in schema.values():
            assert_strict_objects(test_case, value)
    elif isinstance(schema, list):
        for value in schema:
            assert_strict_objects(test_case, value)


class InterviewPrepGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "test-key-never-sent",
                "GROQ_MODEL": "configured-test-model",
                "GROQ_TIMEOUT_SECONDS": "12",
            },
            clear=True,
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def mock_client(self, content):
        client = MagicMock()
        client.chat.completions.create.return_value = self.mock_response(content)
        return client

    def mock_response(self, content):
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_success_uses_groq_chat_completions_and_strict_schema(self, openai_class):
        record = record_fixture([{"name": "JobFit Copilot", "tags": [], "summary": "Saved"}])
        client = self.mock_client(json.dumps(prep_payload("JobFit, Copilot")))
        openai_class.return_value = client

        result = generate_interview_prep(record)

        self.assertEqual(result["project_talking_points"][0]["project_name"], "JobFit Copilot")
        openai_class.assert_called_once_with(
            api_key="test-key-never-sent",
            base_url="https://api.groq.com/openai/v1",
            timeout=12.0,
        )
        client.chat.completions.create.assert_called_once()
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], "configured-test-model")
        self.assertIs(call["stream"], False)
        self.assertNotIn("store", call)
        self.assertEqual([message["role"] for message in call["messages"]], ["system", "user"])
        self.assertIn("UNTRUSTED PROFILE TEXT", call["messages"][1]["content"])
        self.assertIn("UNTRUSTED JD TEXT", call["messages"][1]["content"])
        self.assertIn("Do not invent skills, projects, or experience", call["messages"][1]["content"])
        instructions = call["messages"][0]["content"]
        self.assertIn("job_focus must contain exactly 4", instructions)
        self.assertIn("likely_questions must contain exactly 5", instructions)
        self.assertIn("answer_outline", instructions)
        self.assertIn("exactly 3 distinct points", instructions)
        self.assertIn("honest_boundaries must contain exactly 3", instructions)
        self.assertIn("questions_to_ask must contain exactly 4", instructions)
        self.assertIn("analysis.unknown_items", instructions)
        self.assertIn("human_checkpoints", instructions)
        self.assertIn("job_focus item in Simplified Chinese", instructions)
        self.assertIn("likely_questions are questions an interviewer may ask the candidate", instructions)
        self.assertIn("Never put candidate-to-company questions", instructions)
        self.assertIn("Every answer_outline is a first-person answer plan", instructions)
        self.assertIn("Never answer on behalf of the company", instructions)
        self.assertIn("training, technical sharing", instructions)
        self.assertIn("work schedules, promotion opportunities", instructions)
        self.assertIn("questions_to_ask are questions the candidate may ask", instructions)
        self.assertIn("Do not mix these questions into likely_questions", instructions)
        self.assertEqual(call["response_format"]["type"], "json_schema")
        json_schema = call["response_format"]["json_schema"]
        self.assertIs(json_schema["strict"], True)
        provider_schema = json_schema["schema"]
        assert_strict_objects(self, provider_schema)
        properties = provider_schema["properties"]
        self.assertIn("exactly 4", properties["job_focus"]["description"])
        self.assertIn("exactly 5", properties["likely_questions"]["description"])
        self.assertIn(
            "exactly 3",
            properties["likely_questions"]["items"]["properties"]["answer_outline"][
                "description"
            ],
        )
        self.assertIn("exactly 3", properties["honest_boundaries"]["description"])
        self.assertIn("exactly 4", properties["questions_to_ask"]["description"])
        self.assertIn("non-repeated", properties["questions_to_ask"]["description"])
        self.assertIn("allowed real projects", properties["project_talking_points"]["description"])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_pydantic_invalid_response_retries_once_then_succeeds(self, openai_class):
        invalid_payload = prep_payload()
        invalid_payload["questions_to_ask"] = ["Too few", "Still too few"]
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            self.mock_response(json.dumps(invalid_payload)),
            self.mock_response(json.dumps(prep_payload())),
        ]
        openai_class.return_value = client

        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ) as logs:
            result = generate_interview_prep(record_fixture())

        self.assertEqual(result, prep_payload())
        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertIn(
            "interview_prep_retry attempt=2 reason=invalid_response",
            "\n".join(logs.output),
        )

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_project_whitelist_failure_retries_and_keeps_saved_name(self, openai_class):
        record = record_fixture(
            [{"name": "Real Project", "tags": [], "summary": "Saved project"}]
        )
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            self.mock_response(json.dumps(prep_payload("Invented Project"))),
            self.mock_response(json.dumps(prep_payload("Real, Project"))),
        ]
        openai_class.return_value = client

        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ):
            result = generate_interview_prep(record)

        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertEqual(
            result["project_talking_points"][0]["project_name"],
            "Real Project",
        )

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_two_invalid_responses_stop_after_second_attempt(self, openai_class):
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            self.mock_response("first-invalid-json"),
            self.mock_response("second-invalid-json"),
        ]
        openai_class.return_value = client

        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ):
            with self.assertRaises(LLMInvalidResponseError):
                generate_interview_prep(record_fixture())

        self.assertEqual(client.chat.completions.create.call_count, 2)

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_temporary_upstream_error_retries_once_then_succeeds(self, openai_class):
        request = httpx.Request("POST", "https://example.invalid")
        server_response = httpx.Response(500, request=request)
        temporary_errors = [
            APIConnectionError(request=request),
            InternalServerError("temporary server error", response=server_response, body=None),
        ]

        for temporary_error in temporary_errors:
            with self.subTest(error=type(temporary_error).__name__):
                client = MagicMock()
                client.chat.completions.create.side_effect = [
                    temporary_error,
                    self.mock_response(json.dumps(prep_payload())),
                ]
                openai_class.return_value = client

                with self.assertLogs(
                    "backend.app.llm.interview_prep_generator", level="WARNING"
                ) as logs:
                    result = generate_interview_prep(record_fixture())

                self.assertEqual(result, prep_payload())
                self.assertEqual(client.chat.completions.create.call_count, 2)
                self.assertIn(
                    "interview_prep_retry attempt=2 reason=temporary_upstream",
                    "\n".join(logs.output),
                )

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_two_temporary_upstream_errors_keep_upstream_error(self, openai_class):
        request = httpx.Request("POST", "https://example.invalid")
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            APIConnectionError(request=request),
            APIConnectionError(request=request),
        ]
        openai_class.return_value = client

        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ):
            with self.assertRaises(LLMUpstreamError):
                generate_interview_prep(record_fixture())

        self.assertEqual(client.chat.completions.create.call_count, 2)

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_retry_logs_do_not_include_sensitive_values(self, openai_class):
        sensitive_model_output = "MODEL_OUTPUT_MUST_NOT_BE_LOGGED"
        sensitive_profile = "PROFILE_TEXT_MUST_NOT_BE_LOGGED"
        sensitive_jd = "JD_TEXT_MUST_NOT_BE_LOGGED"
        sensitive_demo_code = "DEMO_CODE_MUST_NOT_BE_LOGGED"
        record = record_fixture()
        record["profile_snapshot"] = sensitive_profile
        record["jd_text"] = sensitive_jd
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            self.mock_response(sensitive_model_output),
            self.mock_response(json.dumps(prep_payload())),
        ]
        openai_class.return_value = client

        with patch.dict(os.environ, {"DEMO_ACCESS_CODE": sensitive_demo_code}):
            with self.assertLogs(
                "backend.app.llm.interview_prep_generator", level="WARNING"
            ) as logs:
                generate_interview_prep(record)

        log_text = "\n".join(logs.output)
        self.assertNotIn(sensitive_model_output, log_text)
        self.assertNotIn(sensitive_profile, log_text)
        self.assertNotIn(sensitive_jd, log_text)
        self.assertNotIn("test-key-never-sent", log_text)
        self.assertNotIn(sensitive_demo_code, log_text)

    def test_missing_groq_api_key_is_rejected_without_openai_fallback(self):
        with patch.dict(
            os.environ,
            {"GROQ_API_KEY": "", "OPENAI_API_KEY": "old-key-must-not-be-used"},
            clear=False,
        ):
            with patch("backend.app.llm.interview_prep_generator.OpenAI") as openai_class:
                with self.assertRaises(LLMConfigurationError):
                    generate_interview_prep(record_fixture())
                openai_class.assert_not_called()

    def test_missing_groq_model_is_rejected_without_openai_fallback(self):
        with patch.dict(
            os.environ,
            {"GROQ_MODEL": "", "OPENAI_MODEL": "old-model-must-not-be-used"},
            clear=False,
        ):
            with patch("backend.app.llm.interview_prep_generator.OpenAI") as openai_class:
                with self.assertRaises(LLMConfigurationError):
                    generate_interview_prep(record_fixture())
                openai_class.assert_not_called()

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_empty_content_is_rejected(self, openai_class):
        for content in (None, "", "   "):
            with self.subTest(content=repr(content)):
                openai_class.return_value = self.mock_client(content)
                with self.assertLogs(
                    "backend.app.llm.interview_prep_generator", level="WARNING"
                ) as logs:
                    with self.assertRaises(LLMInvalidResponseError):
                        generate_interview_prep(record_fixture())
                self.assertIn("interview_prep_invalid_stage=empty_content", logs.output[0])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_missing_choices_is_logged_as_response_shape(self, openai_class):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[])
        openai_class.return_value = client
        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ) as logs:
            with self.assertRaises(LLMInvalidResponseError):
                generate_interview_prep(record_fixture())
        self.assertIn("interview_prep_invalid_stage=response_shape", logs.output[0])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_invalid_json_is_rejected(self, openai_class):
        openai_class.return_value = self.mock_client("not-json")
        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ) as logs:
            with self.assertRaises(LLMInvalidResponseError):
                generate_interview_prep(record_fixture())
        self.assertIn("interview_prep_invalid_stage=json_decode", logs.output[0])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_json_that_fails_pydantic_is_rejected(self, openai_class):
        invalid_payload = prep_payload()
        invalid_payload["questions_to_ask"] = ["Only one", "Only two"]
        openai_class.return_value = self.mock_client(json.dumps(invalid_payload))
        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ) as logs:
            with self.assertRaises(LLMInvalidResponseError):
                generate_interview_prep(record_fixture())
        self.assertIn("interview_prep_invalid_stage=pydantic_validation", logs.output[0])
        self.assertIn("questions_to_ask:too_short", logs.output[0])
        self.assertNotIn("Only one", logs.output[0])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_invented_project_is_rejected(self, openai_class):
        openai_class.return_value = self.mock_client(json.dumps(prep_payload("Invented Project")))
        record = record_fixture([{"name": "Real Project", "tags": [], "summary": "Saved"}])
        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ) as logs:
            with self.assertRaises(LLMInvalidResponseError):
                generate_interview_prep(record)
        self.assertIn("interview_prep_invalid_stage=project_whitelist", logs.output[0])
        self.assertIn("project_whitelist_mismatch", logs.output[0])
        self.assertNotIn("Invented Project", logs.output[0])

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_no_saved_projects_requires_empty_talking_points(self, openai_class):
        openai_class.return_value = self.mock_client(json.dumps(prep_payload("Invented Project")))
        with self.assertLogs(
            "backend.app.llm.interview_prep_generator", level="WARNING"
        ):
            with self.assertRaises(LLMInvalidResponseError):
                generate_interview_prep(record_fixture())

        openai_class.return_value = self.mock_client(json.dumps(prep_payload()))
        result = generate_interview_prep(record_fixture())
        self.assertEqual(result["project_talking_points"], [])

    def test_local_output_model_keeps_full_constraints(self):
        with self.assertRaises(ValidationError):
            InterviewPrep.model_validate({**prep_payload(), "extra": "not allowed"})
        with self.assertRaises(ValidationError):
            InterviewPrep.model_validate({**prep_payload(), "job_focus": ["one"]})

    @patch("backend.app.llm.interview_prep_generator.OpenAI")
    def test_provider_exceptions_are_mapped_to_domain_errors(self, openai_class):
        request = httpx.Request("POST", "https://example.invalid")
        response = httpx.Response(401, request=request)
        cases = [
            (
                AuthenticationError("bad auth", response=response, body=None),
                LLMAuthenticationError,
                1,
            ),
            (RateLimitError("limited", response=response, body=None), LLMRateLimitError, 1),
            (APITimeoutError(request), LLMTimeoutError, 1),
            (APIConnectionError(request=request), LLMUpstreamError, 2),
        ]
        for provider_error, domain_error, expected_calls in cases:
            with self.subTest(error=type(provider_error).__name__):
                client = MagicMock()
                client.chat.completions.create.side_effect = provider_error
                openai_class.return_value = client
                with self.assertRaises(domain_error):
                    generate_interview_prep(record_fixture())
                self.assertEqual(client.chat.completions.create.call_count, expected_calls)


if __name__ == "__main__":
    unittest.main()

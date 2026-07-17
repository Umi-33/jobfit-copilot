import json
import logging
import os
import unicodedata
from typing import Annotated, Dict, List

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError as OpenAIAuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError as OpenAIRateLimitError,
)
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from .prompts import INTERVIEW_PREP_INSTRUCTIONS, build_interview_prep_input


logger = logging.getLogger(__name__)

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
ProjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class LikelyQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: ShortText
    answer_outline: List[ShortText] = Field(min_length=2, max_length=5)


class ProjectTalkingPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: ProjectName
    talking_points: List[ShortText] = Field(min_length=1, max_length=5)


class InterviewPrep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_focus: List[ShortText] = Field(min_length=3, max_length=6)
    likely_questions: List[LikelyQuestion] = Field(min_length=4, max_length=8)
    project_talking_points: List[ProjectTalkingPoint] = Field(max_length=3)
    honest_boundaries: List[ShortText] = Field(min_length=2, max_length=6)
    questions_to_ask: List[ShortText] = Field(min_length=3, max_length=6)


class InterviewPrepError(Exception):
    """Base domain error for safe HTTP mapping."""


class LLMConfigurationError(InterviewPrepError):
    pass


class LLMAuthenticationError(InterviewPrepError):
    pass


class LLMRateLimitError(InterviewPrepError):
    pass


class LLMTimeoutError(InterviewPrepError):
    pass


class LLMUpstreamError(InterviewPrepError):
    pass


class LLMInvalidResponseError(InterviewPrepError):
    pass


def _timeout_seconds() -> float:
    raw_value = os.getenv("GROQ_TIMEOUT_SECONDS", "30").strip()
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise LLMConfigurationError("LLM service is not configured") from exc
    if value <= 0:
        raise LLMConfigurationError("LLM service is not configured")
    return value


def _normalize_project_name(value: str) -> str:
    """Normalize spacing and Chinese/English punctuation for exact name matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        character
        for character in normalized
        if not character.isspace() and not unicodedata.category(character).startswith("P")
    )


def _saved_project_names(record: Dict) -> Dict[str, str]:
    projects = record.get("analysis", {}).get("parsed_profile", {}).get("projects", [])
    names = {}
    for project in projects:
        if not isinstance(project, dict) or not isinstance(project.get("name"), str):
            continue
        original_name = project["name"].strip()
        normalized_name = _normalize_project_name(original_name)
        if original_name and normalized_name:
            names[normalized_name] = original_name
    return names


def _validate_project_names(prep: InterviewPrep, record: Dict) -> InterviewPrep:
    """Reject invented projects and restore the exact saved project spelling."""
    allowed_names = _saved_project_names(record)
    if not allowed_names and prep.project_talking_points:
        logger.warning(
            "interview_prep_invalid_stage=project_whitelist detail=project_whitelist_mismatch"
        )
        raise LLMInvalidResponseError("LLM returned an invalid response")

    for item in prep.project_talking_points:
        original_name = allowed_names.get(_normalize_project_name(item.project_name))
        if original_name is None:
            logger.warning(
                "interview_prep_invalid_stage=project_whitelist detail=project_whitelist_mismatch"
            )
            raise LLMInvalidResponseError("LLM returned an invalid response")
        item.project_name = original_name
    return prep


def _log_pydantic_failure(error: ValidationError) -> None:
    """Log only validation locations and error types, never model values."""
    safe_errors = [
        f"{'.'.join(str(part) for part in item['loc'])}:{item['type']}"
        for item in error.errors(include_url=False, include_context=False, include_input=False)
    ]
    logger.warning(
        "interview_prep_invalid_stage=pydantic_validation fields=%s",
        ",".join(safe_errors),
    )


def _provider_schema() -> Dict:
    """Return a Groq-compatible structural schema; Pydantic enforces full limits."""
    likely_question = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question": {"type": "string"},
            "answer_outline": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Must contain exactly 3 distinct answer-outline points.",
            },
        },
        "required": ["question", "answer_outline"],
    }
    project_talking_point = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "project_name": {
                "type": "string",
                "description": "Must reference one project from allowed_project_names.",
            },
            "talking_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Should contain exactly 3 concise talking points.",
            },
        },
        "required": ["project_name", "talking_points"],
    }
    properties = {
        "job_focus": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Must contain exactly 4 distinct job-focus items.",
        },
        "likely_questions": {
            "type": "array",
            "items": likely_question,
            "description": "Must contain exactly 5 interview questions.",
        },
        "project_talking_points": {
            "type": "array",
            "items": project_talking_point,
            "description": (
                "May contain only 1 to 3 allowed real projects; must be empty when no "
                "allowed project exists."
            ),
        },
        "honest_boundaries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Must contain exactly 3 distinct honest boundaries.",
        },
        "questions_to_ask": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Must contain exactly 4 distinct, non-repeated questions.",
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def generate_interview_prep(record: Dict) -> Dict:
    """Generate and validate interview preparation without changing saved analysis."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "").strip()
    if not api_key or not model:
        raise LLMConfigurationError("LLM service is not configured")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=_timeout_seconds(),
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": INTERVIEW_PREP_INSTRUCTIONS},
                {"role": "user", "content": build_interview_prep_input(record)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "interview_prep",
                    "strict": True,
                    "schema": _provider_schema(),
                },
            },
            stream=False,
        )
    except OpenAIAuthenticationError as exc:
        raise LLMAuthenticationError("LLM service authentication failed") from exc
    except OpenAIRateLimitError as exc:
        raise LLMRateLimitError("LLM service is temporarily rate limited") from exc
    except APITimeoutError as exc:
        raise LLMTimeoutError("LLM service timed out") from exc
    except (APIConnectionError, OpenAIError) as exc:
        raise LLMUpstreamError("LLM service request failed") from exc
    try:
        choices = response.choices
        if not choices:
            raise AttributeError("missing choices")
        message = choices[0].message
        if message is None:
            raise AttributeError("missing message")
        content = message.content
        if content is not None and not isinstance(content, str):
            raise TypeError("invalid content type")
    except (AttributeError, IndexError, TypeError) as exc:
        logger.warning("interview_prep_invalid_stage=response_shape")
        raise LLMInvalidResponseError("LLM returned an invalid response") from exc

    if content is None or not content.strip():
        logger.warning("interview_prep_invalid_stage=empty_content")
        raise LLMInvalidResponseError("LLM returned an invalid response")

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("interview_prep_invalid_stage=json_decode")
        raise LLMInvalidResponseError("LLM returned an invalid response") from exc

    try:
        parsed = InterviewPrep.model_validate(payload)
    except ValidationError as exc:
        _log_pydantic_failure(exc)
        raise LLMInvalidResponseError("LLM returned an invalid response") from exc

    parsed = _validate_project_names(parsed, record)
    return parsed.model_dump()

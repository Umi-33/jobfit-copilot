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
    raw_value = os.getenv("OPENAI_TIMEOUT_SECONDS", "30").strip()
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
        raise LLMInvalidResponseError("LLM returned an invalid response")

    for item in prep.project_talking_points:
        original_name = allowed_names.get(_normalize_project_name(item.project_name))
        if original_name is None:
            raise LLMInvalidResponseError("LLM returned an invalid response")
        item.project_name = original_name
    return prep


def generate_interview_prep(record: Dict) -> Dict:
    """Generate and validate interview preparation without changing saved analysis."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()
    if not api_key or not model:
        raise LLMConfigurationError("LLM service is not configured")

    client = OpenAI(api_key=api_key, timeout=_timeout_seconds())
    try:
        response = client.responses.parse(
            model=model,
            instructions=INTERVIEW_PREP_INSTRUCTIONS,
            input=build_interview_prep_input(record),
            text_format=InterviewPrep,
            store=False,
        )
    except OpenAIAuthenticationError as exc:
        raise LLMAuthenticationError("LLM service authentication failed") from exc
    except OpenAIRateLimitError as exc:
        raise LLMRateLimitError("LLM service is temporarily rate limited") from exc
    except APITimeoutError as exc:
        raise LLMTimeoutError("LLM service timed out") from exc
    except (APIConnectionError, OpenAIError) as exc:
        raise LLMUpstreamError("LLM service request failed") from exc
    except ValidationError as exc:
        raise LLMInvalidResponseError("LLM returned an invalid response") from exc

    try:
        parsed = response.output_parsed
        if parsed is None:
            raise LLMInvalidResponseError("LLM returned an invalid response")
        if not isinstance(parsed, InterviewPrep):
            parsed = InterviewPrep.model_validate(parsed)
        parsed = _validate_project_names(parsed, record)
    except LLMInvalidResponseError:
        raise
    except (ValidationError, TypeError, ValueError, AttributeError) as exc:
        raise LLMInvalidResponseError("LLM returned an invalid response") from exc
    return parsed.model_dump()

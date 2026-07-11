from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from .core.agent_planner import plan_next_actions
from .core.rule_scorer import score_job
from .storage.database import initialize_database, resolve_database_path
from .storage.job_record_repository import (
    ALLOWED_STATUSES,
    create_job_record,
    get_job_record,
    list_job_records,
    update_job_record_status,
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize SQLite when the service starts, not when modules are imported."""
    database_path = resolve_database_path()
    initialize_database(database_path)
    application.state.database_path = database_path
    yield


app = FastAPI(title="Jobfit Copilot API", version="1.5.0", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    profile_text: str
    jd_text: str


class CreateJobRecordRequest(BaseModel):
    company_name: str
    job_title: str
    city: str
    profile_text: str
    jd_text: str

    @field_validator("company_name", "job_title", "city", "profile_text", "jd_text", mode="before")
    @classmethod
    def validate_required_text(cls, value):
        """Trim required text and reject empty or whitespace-only values."""
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("field must not be empty")
        return value


class UpdateJobStatusRequest(BaseModel):
    status: str

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value):
        """Reject unsupported record statuses before repository access."""
        if isinstance(value, str):
            value = value.strip()
        if value not in ALLOWED_STATUSES:
            raise ValueError("unsupported job record status")
        return value


def _run_analysis(profile_text: str, jd_text: str) -> dict:
    """Run the one shared analysis and planner pipeline used by both APIs."""
    analysis = score_job(profile_text, jd_text)
    return {
        "analysis": analysis,
        "action_plan": plan_next_actions(analysis),
    }


@app.get("/api/health")
def health() -> dict:
    """Return a minimal service health check."""
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    """Run rule analysis and the human-in-the-loop planner."""
    profile_text = payload.profile_text.strip()
    jd_text = payload.jd_text.strip()
    if not profile_text:
        raise HTTPException(status_code=400, detail="profile_text must not be empty")
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text must not be empty")

    try:
        return _run_analysis(profile_text, jd_text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to analyze job") from exc


@app.post("/api/records", status_code=201)
def create_record(payload: CreateJobRecordRequest) -> dict:
    """Analyze a job once and save the complete result snapshot."""
    try:
        result = _run_analysis(payload.profile_text, payload.jd_text)
        return create_job_record(
            company_name=payload.company_name,
            job_title=payload.job_title,
            city=payload.city,
            profile_snapshot=payload.profile_text,
            jd_text=payload.jd_text,
            analysis=result["analysis"],
            action_plan=result["action_plan"],
            database_path=app.state.database_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to create job record") from exc


@app.get("/api/records")
def get_records() -> list:
    """Return compact history rows without large snapshot fields."""
    try:
        return list_job_records(app.state.database_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to list job records") from exc


@app.get("/api/records/{record_id}")
def get_record(record_id: int) -> dict:
    """Return one complete saved analysis record."""
    try:
        record = get_job_record(record_id, app.state.database_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to get job record") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="job record not found")
    return record


@app.patch("/api/records/{record_id}/status")
def update_record_status(record_id: int, payload: UpdateJobStatusRequest) -> dict:
    """Update a record to one allowed user-managed status."""
    try:
        result = update_job_record_status(
            record_id,
            payload.status,
            app.state.database_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update job record") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="job record not found")
    return result

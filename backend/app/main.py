from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .core.agent_planner import plan_next_actions
from .core.rule_scorer import score_job


app = FastAPI(title="Jobfit Copilot API", version="1.0.0")


class AnalyzeRequest(BaseModel):
    profile_text: str
    jd_text: str


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
        analysis = score_job(profile_text, jd_text)
        action_plan = plan_next_actions(analysis)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to analyze job") from exc

    return {
        "analysis": analysis,
        "action_plan": action_plan,
    }

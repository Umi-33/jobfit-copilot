import json

from app.core.agent_planner import plan_next_actions
from app.core.rule_scorer import score_job
from demo_analyze import SAMPLE_JD, SAMPLE_PROFILE


def main() -> None:
    """Run V0.2 agent planner demo without auto-applying or sending messages."""
    analysis = score_job(SAMPLE_PROFILE, SAMPLE_JD)
    action_plan = plan_next_actions(analysis)
    result = {
        "analysis": analysis,
        "action_plan": action_plan,
        "agent_trace": action_plan["agent_trace"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from typing import Dict, List


ALLOWED_ACTIONS = {
    "prepare_application",
    "ask_clarifying_questions",
    "prepare_interview",
    "cautious_pitch",
    "archive_job",
    "manual_review_required",
}

AGENT_HEAVY_RISKS = {"production_agent_heavy", "agent_keyword_trap", "backend_heavy", "rag_agent_framework_heavy"}


def _risk_types(items: List[Dict]) -> set:
    return {item.get("type") for item in items if item.get("type")}


def _has_production_agent_context(analysis: Dict) -> bool:
    """Detect Agent/RAG production pressure from existing rule analysis only."""
    soft_types = _risk_types(analysis.get("soft_risks", []))
    hard_types = _risk_types(analysis.get("hard_risks", []))
    missing_names = {item.get("item") for item in analysis.get("missing_items", [])}
    cap_text = " ".join(analysis.get("cap_reasons", []))
    parsed_tech = set(analysis.get("parsed_jd", {}).get("tech_keywords", []))
    return bool(
        {"production_agent_heavy", "agent_keyword_trap", "rag_agent_framework_heavy"} & soft_types
        or "requires_independent_full_agent_framework" in hard_types
        or "生产级 RAG/Agent 工程经验" in missing_names
        or "Agent" in cap_text
        or {"Agent", "RAG", "LangChain"} & parsed_tech
    )


def _build_human_checkpoints(primary_action: str, analysis: Dict) -> List[Dict]:
    """Create blocking human checkpoints for any next step."""
    questions = analysis.get("next_questions") or analysis.get("unknown_items", [])
    checkpoints = [
        {
            "id": "confirm_before_action",
            "question": "是否确认按当前 action_plan 继续处理该岗位？",
            "required": True,
            "blocking": True,
            "related_items": [primary_action],
        }
    ]
    if questions:
        checkpoints.append(
            {
                "id": "confirm_unknown_items",
                "question": "是否先向招聘方确认关键未知项？",
                "required": True,
                "blocking": True,
                "related_items": questions,
            }
        )
    if analysis.get("hard_risks"):
        checkpoints.append(
            {
                "id": "override_hard_risks",
                "question": "存在硬风险，如仍要推进，是否由人工明确覆盖该建议？",
                "required": True,
                "blocking": True,
                "related_items": [item.get("type") for item in analysis.get("hard_risks", [])],
            }
        )
    return checkpoints


def _build_blocked_outputs(analysis: Dict) -> List[str]:
    """List outputs this V0.2 planner must not produce."""
    blocked = [
        "不能自动投递",
        "不能自动发送消息",
        "不能绕过人工确认推进岗位",
        "不能编造技能、项目或经历",
    ]
    if _has_production_agent_context(analysis):
        blocked.append("不能声称独立负责生产级 Agent 框架")
    return blocked


def _trace(step: str, observation: str, reason: str) -> Dict:
    return {"step": step, "observation": observation, "reason": reason}


def plan_next_actions(analysis: Dict) -> Dict:
    """Plan the next human-confirmed job-search action from V0.1 analysis."""
    rating = analysis.get("rating")
    risk_level = analysis.get("risk_level")
    unknown_items = analysis.get("unknown_items", [])
    hard_risks = analysis.get("hard_risks", [])
    soft_risks = analysis.get("soft_risks", [])
    soft_types = _risk_types(soft_risks)
    trace = [
        _trace(
            "read_rule_analysis",
            f"rating={rating}, risk_level={risk_level}, unknown_count={len(unknown_items)}, hard_risk_count={len(hard_risks)}",
            "Agent planner only reads V0.1 rule analysis and does not rescore the job.",
        )
    ]

    if rating == "D" or hard_risks:
        primary_action = "archive_job"
        secondary_actions = ["manual_review_required"]
        reason = "存在 D 级结果或 hard_risks，默认归档，不自动推进。"
        trace.append(_trace("select_action", "D rating or hard_risks detected", "Use archive_job."))
    elif rating in {"B+", "B"} and len(unknown_items) >= 3:
        primary_action = "ask_clarifying_questions"
        secondary_actions = ["manual_review_required"]
        reason = "岗位方向可考虑，但 unknown_items 较多，先确认关键信息。"
        trace.append(_trace("select_action", f"unknown_count={len(unknown_items)}", "Use ask_clarifying_questions."))
    elif rating in {"C+", "C"} or soft_types & AGENT_HEAVY_RISKS:
        primary_action = "cautious_pitch"
        secondary_actions = ["ask_clarifying_questions", "prepare_interview"]
        reason = "岗位存在 C/C+ 评级或 Agent/RAG/后端偏重软风险，只能谨慎表达。"
        trace.append(_trace("select_action", f"soft_risks={sorted(soft_types)}", "Use cautious_pitch."))
    elif rating in {"A", "A-"} and risk_level == "low" and len(unknown_items) < 3:
        primary_action = "prepare_application"
        secondary_actions = ["prepare_interview"]
        reason = "岗位匹配度高、风险低、未知项少，可准备材料，但投递前仍需人工确认。"
        trace.append(_trace("select_action", "A/A- with low risk and fewer than 3 unknown items", "Use prepare_application."))
    else:
        primary_action = "manual_review_required"
        secondary_actions = ["ask_clarifying_questions"]
        reason = "当前结果不满足明确推进或归档条件，需要人工复核。"
        trace.append(_trace("select_action", "No specific planner rule matched", "Use manual_review_required."))

    suggested_next_questions = analysis.get("next_questions") or unknown_items
    allowed_outputs = [
        "整理岗位判断理由",
        "整理待确认问题",
        "整理面试准备要点",
        "整理保守项目表达",
    ]

    return {
        "primary_action": primary_action,
        "secondary_actions": [action for action in secondary_actions if action in ALLOWED_ACTIONS],
        "human_approval_required": True,
        "human_checkpoints": _build_human_checkpoints(primary_action, analysis),
        "reason": reason,
        "suggested_next_questions": suggested_next_questions,
        "allowed_outputs": allowed_outputs,
        "blocked_outputs": _build_blocked_outputs(analysis),
        "agent_trace": trace,
    }

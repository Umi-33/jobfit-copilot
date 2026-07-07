from typing import Dict, List


HARD_RISK_CONFIG = {
    "single_rest": {"penalty": 22, "reason": "岗位明确单休，属于硬性作息风险。"},
    "big_small_week": {"penalty": 18, "reason": "岗位明确大小周，属于硬性作息风险。"},
    "salary_below_floor": {"penalty": 32, "reason": "岗位薪资上限低于用户底线。"},
    "pure_sales": {"penalty": 35, "reason": "岗位含纯销售、电销、地推等强销售属性。"},
    "training_loan": {"penalty": 45, "reason": "涉及培训贷、先交费或付费培训。"},
    "unpaid_trial": {"penalty": 35, "reason": "无薪试岗属于明显用工风险。"},
    "salary_pressure": {"penalty": 25, "reason": "岗位或沟通过程存在明显压薪。"},
    "internship_first_unclear_conversion": {"penalty": 28, "reason": "先实习看看但转正路径不清。"},
    "communication_red_flag": {"penalty": 24, "reason": "沟通不尊重，属于推进风险。"},
    "requires_independent_full_agent_framework": {"penalty": 38, "reason": "要求新人独立从 0 搭生产级 Agent 框架。"},
}

SOFT_RISK_CONFIG = {
    "sales_tendency": {"penalty": 4, "reason": "岗位有销售转化或提成倾向，需要确认实际职责。"},
    "operation_ratio_high": {"penalty": 5, "reason": "运营占比可能偏高，需要确认是否偏离技术/工具落地。"},
    "strong_kpi": {"penalty": 3, "reason": "强 KPI 或业绩考核会影响岗位稳定性。"},
    "heavy_overtime": {"penalty": 3, "reason": "高压加班描述需要谨慎评估。"},
    "production_agent_heavy": {"penalty": 5, "reason": "岗位偏生产级 RAG/Agent，不应按普通 AI 应用高估。"},
    "rag_agent_framework_heavy": {"penalty": 4, "reason": "JD 对 LangChain/LangGraph/RAG 熟练度有要求。"},
    "docker_linux_deployment": {"penalty": 3, "reason": "岗位涉及 Docker/Linux/部署能力，需要补充确认。"},
    "react_next_typescript_hard": {"penalty": 3, "reason": "React/Next/TypeScript 是硬要求时不能按 Vue 经验等同。"},
    "java_backend_heavy": {"penalty": 5, "reason": "Java/SpringCloud/微服务/高并发后端要求偏重。"},
    "backend_heavy": {"penalty": 4, "reason": "后端开发或系统化落地占比偏重。"},
    "stability_evaluation_requirement": {"penalty": 4, "reason": "稳定性、评估、监控要求偏生产级。"},
    "ai_relevance_low": {"penalty": 2, "reason": "岗位主要是普通前端，AI 相关性较低。"},
    "experience_1_3_years": {"penalty": 2, "reason": "1-3 年经验要求对入门候选人仍需谨慎。"},
    "salary_too_high_for_entry_level": {"penalty": 3, "reason": "高薪区间往往对应更高生产能力要求。"},
    "remote_work_uncertainty": {"penalty": 2, "reason": "远程办公真实性和稳定性需要确认。"},
    "possible_not_junior_friendly": {"penalty": 4, "reason": "岗位可能不适合初级候选人独立承担。"},
    "agent_keyword_trap": {"penalty": 3, "reason": "Agent 关键词容易高估匹配，需要看真实工程深度。"},
    "operation_boundary_unclear": {"penalty": 3, "reason": "技术与运营边界不清，需要进一步确认。"},
}

RISK_KEYWORD_MAP = {
    "单休": ("hard", "single_rest"),
    "大小周": ("hard", "big_small_week"),
    "纯销售": ("hard", "pure_sales"),
    "培训贷": ("hard", "training_loan"),
    "无薪试岗": ("hard", "unpaid_trial"),
    "压薪明显": ("hard", "salary_pressure"),
    "先实习看看且转正不明": ("hard", "internship_first_unclear_conversion"),
    "沟通不尊重": ("hard", "communication_red_flag"),
    "独立从0搭生产级Agent框架": ("hard", "requires_independent_full_agent_framework"),
    "销售倾向": ("soft", "sales_tendency"),
    "运营占比高": ("soft", "operation_ratio_high"),
    "强 KPI": ("soft", "strong_kpi"),
    "高压加班": ("soft", "heavy_overtime"),
}


def _add_unique(items: List[Dict], risk_type: str, config: Dict) -> None:
    if any(item["type"] == risk_type for item in items):
        return
    items.append({"type": risk_type, "penalty": config["penalty"], "reason": config["reason"]})


def _add_unknown(items: List[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _has_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)


def _has_uncertainty_context(text: str) -> bool:
    return _has_any(text, ["信息不足", "未确认", "未知", "不清", "不明确", "待确认", "可能"])


def _detect_unknowns(jd: Dict, hard_risks: List[Dict]) -> List[str]:
    """Find missing JD facts that should block over-confident recommendations."""
    text = jd.get("raw_text", "")
    salary = jd.get("salary", {})
    unknown_items: List[str] = []

    if not _has_any(text, ["双休", "五天", "五天工作制", "单休", "大小周", "做六休一"]):
        _add_unknown(unknown_items, "是否双休/五天工作制")

    if salary.get("min") is None and salary.get("max") is None:
        if _has_any(text, ["正式薪资", "压薪", "薪资不清"]):
            _add_unknown(unknown_items, "正式薪资范围")
        else:
            _add_unknown(unknown_items, "薪资范围是否在8000以上")

    if _has_uncertainty_context(text) and "试用期" in text:
        _add_unknown(unknown_items, "试用期薪资比例")

    if _has_any(text, ["外包", "派遣"]):
        _add_unknown(unknown_items, "是否外包/派遣")
        _add_unknown(unknown_items, "实际用工主体是谁")

    if "校招" in text and _has_uncertainty_context(text):
        _add_unknown(unknown_items, "是否校招正式岗位")

    if "是否接受应届未确认" in text or ("应届" in text and _has_uncertainty_context(text)):
        _add_unknown(unknown_items, "是否接受应届生")

    if _has_any(text, ["技术/运营占比未确认", "运营边界不清"]):
        _add_unknown(unknown_items, "岗位是AI工具落地为主，还是运营为主")
        _add_unknown(unknown_items, "技术/工具/数据处理内容是否≥60%")

    if "后端深度未确认" in text:
        _add_unknown(unknown_items, "后端开发深度与职责边界")

    if "具体技术栈" in text:
        _add_unknown(unknown_items, "主要技术栈是否匹配 Vue/Python/FastAPI")

    if "复杂前端工程化" in text:
        _add_unknown(unknown_items, "是否需要复杂前端工程化经验")

    if "全栈" in text and _has_uncertainty_context(text):
        _add_unknown(unknown_items, "是否要求独立负责生产级全栈系统")

    if _has_any(text, ["生产级Agent", "生产级 Agent", "Agent框架", "Agent 框架", "从0搭", "从 0 搭"]):
        _add_unknown(unknown_items, "是否需要独立负责生产级Agent系统")

    if any(item["type"] == "internship_first_unclear_conversion" for item in hard_risks):
        _add_unknown(unknown_items, "试用/实习周期")
        _add_unknown(unknown_items, "转正标准")

    return unknown_items


def _detect_soft_risks(jd: Dict, profile: Dict, soft_risks: List[Dict]) -> None:
    """Add soft risks from production-level or off-target requirements."""
    text = jd.get("raw_text", "")
    text_lower = text.lower()
    tech_keywords = set(jd.get("tech_keywords", []))
    salary = jd.get("salary", {})

    has_agent = "Agent" in tech_keywords or "agent" in text_lower
    has_rag = "RAG" in tech_keywords or "rag" in text_lower
    has_production = _has_any(text, ["生产级", "系统化落地", "独立上手", "从0", "从 0", "工具调用"])

    if (has_agent or has_rag) and has_production:
        _add_unique(soft_risks, "production_agent_heavy", SOFT_RISK_CONFIG["production_agent_heavy"])

    if _has_any(text_lower, ["langchain", "langgraph"]) or (has_rag and _has_any(text, ["熟练", "框架", "系统"])):
        _add_unique(soft_risks, "rag_agent_framework_heavy", SOFT_RISK_CONFIG["rag_agent_framework_heavy"])

    if _has_any(text_lower, ["docker", "linux", "部署"]):
        _add_unique(soft_risks, "docker_linux_deployment", SOFT_RISK_CONFIG["docker_linux_deployment"])

    if _has_any(text_lower, ["react", "next", "typescript"]) and _has_any(text, ["必须", "精通", "熟练", "硬要求", "要求"]):
        _add_unique(soft_risks, "react_next_typescript_hard", SOFT_RISK_CONFIG["react_next_typescript_hard"])

    if _has_any(text_lower, ["java", "springcloud", "spring cloud", "微服务", "高并发"]):
        _add_unique(soft_risks, "java_backend_heavy", SOFT_RISK_CONFIG["java_backend_heavy"])

    if _has_any(text, ["后端开发", "后端深度", "全栈", "系统化落地"]) and (has_agent or "AI" in text or "ai" in text_lower):
        _add_unique(soft_risks, "backend_heavy", SOFT_RISK_CONFIG["backend_heavy"])

    if _has_any(text, ["稳定性", "评估", "监控"]):
        _add_unique(soft_risks, "stability_evaluation_requirement", SOFT_RISK_CONFIG["stability_evaluation_requirement"])

    if _has_any(text, ["前端", "Vue", "ECharts", "可视化"]) and not _has_any(text_lower, ["ai", "llm", "大模型", "aigc"]):
        _add_unique(soft_risks, "ai_relevance_low", SOFT_RISK_CONFIG["ai_relevance_low"])

    experience = jd.get("experience", {})
    if experience.get("min") and 1 <= experience["min"] <= 3 and (has_agent or has_rag or "全栈" in text or "生产级" in text):
        _add_unique(soft_risks, "experience_1_3_years", SOFT_RISK_CONFIG["experience_1_3_years"])

    if salary.get("min") and salary["min"] >= 15000 and (has_agent or has_rag or "全栈" in text):
        _add_unique(soft_risks, "salary_too_high_for_entry_level", SOFT_RISK_CONFIG["salary_too_high_for_entry_level"])

    if "远程" in text and _has_uncertainty_context(text):
        _add_unique(soft_risks, "remote_work_uncertainty", SOFT_RISK_CONFIG["remote_work_uncertainty"])

    if (has_agent or has_rag) and _has_any(text, ["生产级", "独立", "从0", "从 0", "15-30K", "15-30k"]):
        _add_unique(soft_risks, "possible_not_junior_friendly", SOFT_RISK_CONFIG["possible_not_junior_friendly"])
        _add_unique(soft_risks, "agent_keyword_trap", SOFT_RISK_CONFIG["agent_keyword_trap"])

    if _has_any(text, ["运营边界不清", "技术/运营占比未确认"]):
        _add_unique(soft_risks, "operation_boundary_unclear", SOFT_RISK_CONFIG["operation_boundary_unclear"])


def detect_risks(jd: Dict, profile: Dict) -> Dict:
    """Split JD risks into hard risks, soft risks and unknown items."""
    hard_risks: List[Dict] = []
    soft_risks: List[Dict] = []

    text = jd.get("raw_text", "")
    for keyword in jd.get("risk_keywords", []):
        risk_kind, risk_type = RISK_KEYWORD_MAP.get(keyword, (None, None))
        if not risk_type:
            continue
        if risk_type == "operation_ratio_high" and _has_any(text, ["运营占比未确认", "运营边界不清"]):
            continue
        if risk_kind == "hard":
            _add_unique(hard_risks, risk_type, HARD_RISK_CONFIG[risk_type])
        elif risk_kind == "soft":
            _add_unique(soft_risks, risk_type, SOFT_RISK_CONFIG[risk_type])

    salary = jd.get("salary", {})
    salary_floor = profile.get("salary_floor", 8000)
    salary_min = salary.get("min")
    salary_max = salary.get("max")
    if salary_max is not None and salary_max < salary_floor:
        config = HARD_RISK_CONFIG["salary_below_floor"].copy()
        config["reason"] = f"岗位薪资上限 {salary_max} 低于用户底线 {salary_floor}。"
        _add_unique(hard_risks, "salary_below_floor", config)
    elif salary_min is not None and salary_min < salary_floor:
        _add_unique(
            soft_risks,
            "salary_floor_uncertain",
            {"penalty": 3, "reason": f"岗位薪资下限 {salary_min} 低于用户底线 {salary_floor}，需要确认实际 offer。"},
        )

    if _has_any(text, ["独立上手", "独立负责"]) and _has_any(text, ["从0", "从 0", "Agent框架", "Agent 框架"]):
        _add_unique(hard_risks, "requires_independent_full_agent_framework", HARD_RISK_CONFIG["requires_independent_full_agent_framework"])

    _detect_soft_risks(jd, profile, soft_risks)
    unknown_items = _detect_unknowns(jd, hard_risks)

    hard_penalty = min(sum(item["penalty"] for item in hard_risks), 60)
    soft_penalty = min(sum(item["penalty"] for item in soft_risks), 10)
    risk_score = -(hard_penalty + soft_penalty)
    if hard_risks:
        risk_level = "high"
    elif soft_risks or len(unknown_items) >= 5:
        risk_level = "medium"
    else:
        risk_level = "low"

    cap_reasons: List[str] = []
    if hard_risks:
        cap_reasons.append("存在 hard_risks，不能高评级推进。")
    if len(unknown_items) >= 5:
        cap_reasons.append("unknown_items >= 5，最高 rating 不超过 B+。")
    elif len(unknown_items) >= 3:
        cap_reasons.append("unknown_items >= 3，decision 不能是强推荐。")

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_items": hard_risks + soft_risks,
        "hard_risks": hard_risks,
        "soft_risks": soft_risks,
        "unknown_items": unknown_items,
        "cap_reasons": cap_reasons,
        "next_questions": unknown_items[:],
    }

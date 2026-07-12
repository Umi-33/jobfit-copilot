import re
from typing import Dict, List, Optional


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
    "rag_agent_framework_heavy": {"penalty": 4, "reason": "JD 涉及 RAG / Agent 系统化落地，需要确认是否要求成熟框架经验。"},
    "docker_linux_deployment": {"penalty": 3, "reason": "岗位涉及 Docker/Linux/部署能力，需要补充确认。"},
    "deployment_stability_requirement": {"penalty": 3, "reason": "岗位涉及部署稳定性、线上维护或发布保障，需要确认实际工程深度。"},
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

RISK_CONFIRM_TERMS = {
    "single_rest": ["单休", "做六休一", "周休1天"],
    "big_small_week": ["大小周"],
    "pure_sales": ["纯销售", "电销", "电话销售", "地推", "陌拜"],
    "training_loan": ["培训贷", "贷款培训", "先交费", "先缴费", "付费培训"],
    "unpaid_trial": ["无薪", "试岗无薪"],
    "salary_pressure": ["压薪"],
    "internship_first_unclear_conversion": ["先实习看看", "转正不明", "转正标准不明"],
    "communication_red_flag": ["沟通不尊重", "不尊重"],
    "sales_tendency": ["销售", "客户转化", "邀约", "成单", "提成"],
    "operation_ratio_high": ["运营占比高", "主要做运营", "运营为主", "偏运营", "以运营为主", "运营占比"],
    "strong_kpi": ["kpi", "业绩指标", "强考核"],
    "heavy_overtime": ["抗压", "996", "加班严重"],
}

NEGATION_MARKERS = ["无需", "无须", "不需要", "不要求", "不设", "不是", "非销售", "了解即可"]
SENTENCE_SPLIT_PATTERN = r"[。！？!?；;\r\n]+"
CLAUSE_SPLIT_PATTERN = r"[。！？!?；;，,\r\n]+"


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


def _segments(text: str, pattern: str = CLAUSE_SPLIT_PATTERN) -> List[str]:
    return [segment.strip() for segment in re.split(pattern, text) if segment.strip()]


def _is_negated(segment: str) -> bool:
    return any(marker in segment for marker in NEGATION_MARKERS)


def _has_positive_term(text: str, terms: List[str]) -> bool:
    """Find a term in a short clause that is not explicitly negated."""
    for segment in _segments(text):
        segment_lower = segment.lower()
        if not _is_negated(segment) and any(term.lower() in segment_lower for term in terms):
            return True
    return False


def _has_java_word(text: str) -> bool:
    return re.search(r"(?<![a-z0-9])java(?![a-z0-9])", text.lower()) is not None


def _has_advanced_ai_term(text: str) -> bool:
    text_lower = text.lower()
    return bool(re.search(r"(?<![a-z0-9])(?:rag|agent)(?![a-z0-9])", text_lower)) or "智能体" in text


def _framework_risk_reason(jd: Dict) -> Optional[str]:
    """Detect mature RAG/Agent framework requirements within one sentence."""
    for sentence in _segments(jd.get("raw_text", ""), SENTENCE_SPLIT_PATTERN):
        if _is_negated(sentence):
            continue
        sentence_lower = sentence.lower()
        has_framework_name = _has_any(sentence_lower, ["langchain", "langgraph"])
        has_advanced = _has_advanced_ai_term(sentence)
        strong_framework = _has_any(
            sentence,
            ["熟练掌握", "熟练使用", "精通", "明确要求", "完整 RAG 项目经验", "完整RAG项目经验", "RAG 框架经验", "RAG框架经验"],
        )
        explicit_responsibility = has_advanced and _has_any(
            sentence,
            ["负责搭建", "负责设计", "框架设计", "系统化落地", "独立设计多 Agent", "独立设计多Agent"],
        )
        if has_framework_name and strong_framework:
            return "JD 明确要求 LangChain/LangGraph 等成熟框架经验。"
        if explicit_responsibility or (has_advanced and strong_framework):
            return SOFT_RISK_CONFIG["rag_agent_framework_heavy"]["reason"]
    return None


def has_production_rag_agent_requirement(jd: Dict) -> bool:
    """Detect explicit production RAG/Agent responsibility within one sentence."""
    for sentence in _segments(jd.get("raw_text", ""), SENTENCE_SPLIT_PATTERN):
        if _is_negated(sentence) or not _has_advanced_ai_term(sentence):
            continue
        has_responsibility = _has_any(sentence, ["负责", "承担", "涉及", "独立", "从0", "从 0", "搭建", "部署"])
        if "生产级" in sentence and has_responsibility:
            return True
        production_tasks = ["监控", "评估", "召回优化", "稳定性", "生产部署", "故障处理"]
        task_count = sum(task in sentence for task in production_tasks)
        if "负责" in sentence and task_count >= 2:
            return True
    return False


def _has_independent_from_zero_agent_requirement(jd: Dict) -> bool:
    for sentence in _segments(jd.get("raw_text", ""), SENTENCE_SPLIT_PATTERN):
        if _is_negated(sentence) or not _has_advanced_ai_term(sentence):
            continue
        has_from_zero = _has_any(sentence, ["从0", "从 0"])
        has_strong_ownership = _has_any(sentence, ["独立负责", "独立上手", "要求能独立", "生产级"])
        if has_from_zero and has_strong_ownership:
            return True
        if "独立负责" in sentence and "生产级" in sentence:
            return True
    return False


def _has_explicit_java_backend_requirement(text: str) -> bool:
    for sentence in _segments(text, SENTENCE_SPLIT_PATTERN):
        if _is_negated(sentence):
            continue
        sentence_lower = sentence.lower()
        if _has_any(sentence_lower, ["spring boot", "springboot", "spring cloud", "springcloud"]):
            return True
        if _has_java_word(sentence) and _has_any(sentence, ["后端", "服务端", "微服务", "高并发"]):
            return True
        if _has_any(sentence, ["Java 微服务", "Java微服务", "高并发后端系统", "后端架构", "服务端开发"]):
            return True
    return False


def _has_backend_responsibility(text: str) -> bool:
    for sentence in _segments(text, SENTENCE_SPLIT_PATTERN):
        if _is_negated(sentence):
            continue
        if _has_any(sentence, ["后端开发团队", "与后端协作", "和后端协作", "接口联调", "数据交互", "调用后端", "对接后端"]):
            continue
        if _has_any(
            sentence,
            ["负责后端开发", "承担后端开发", "后端开发职责", "后端架构", "服务端开发", "后端系统开发", "开发后端服务", "全栈开发"],
        ):
            return True
        if "后端开发" in sentence and _has_any(sentence, ["要求", "需要", "岗位涉及", "可能涉及", "职责包含"]):
            return True
    return False


def _detect_unknowns(jd: Dict, hard_risks: List[Dict]) -> List[str]:
    """Find missing JD facts that should block over-confident recommendations."""
    text = jd.get("raw_text", "")
    salary = jd.get("salary", {})
    unknown_items: List[str] = []

    if not _has_positive_term(text, ["双休", "五天", "五天工作制", "单休", "大小周", "做六休一"]):
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

    if _has_any(text, ["可能涉及运营支持", "运营支持"]) and _has_uncertainty_context(text):
        _add_unknown(unknown_items, "运营支持是否为主要职责")

    if "后端深度未确认" in text:
        _add_unknown(unknown_items, "后端开发深度与职责边界")

    if "具体技术栈" in text:
        _add_unknown(unknown_items, "主要技术栈是否匹配 Vue/Python/FastAPI")

    if "复杂前端工程化" in text:
        _add_unknown(unknown_items, "是否需要复杂前端工程化经验")

    if "全栈" in text and _has_uncertainty_context(text):
        _add_unknown(unknown_items, "是否要求独立负责生产级全栈系统")

    if has_production_rag_agent_requirement(jd):
        _add_unknown(unknown_items, "是否需要独立负责生产级Agent系统")
    elif _framework_risk_reason(jd):
        _add_unknown(unknown_items, "是否要求成熟RAG/Agent框架经验")

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

    has_agent = "Agent" in tech_keywords or bool(re.search(r"(?<![a-z0-9])agent(?![a-z0-9])", text_lower))
    has_rag = "RAG" in tech_keywords or bool(re.search(r"(?<![a-z0-9])rag(?![a-z0-9])", text_lower))
    has_production = has_production_rag_agent_requirement(jd)

    if has_production:
        _add_unique(soft_risks, "production_agent_heavy", SOFT_RISK_CONFIG["production_agent_heavy"])

    framework_reason = _framework_risk_reason(jd)
    if framework_reason:
        _add_unique(
            soft_risks,
            "rag_agent_framework_heavy",
            {"penalty": 4, "reason": framework_reason},
        )

    if _has_positive_term(text, ["docker", "linux", "nginx", "容器化", "服务器部署", "云服务器"]):
        _add_unique(soft_risks, "docker_linux_deployment", SOFT_RISK_CONFIG["docker_linux_deployment"])

    if _has_any(text, ["部署稳定性", "线上维护", "发布", "稳定性保障"]):
        _add_unique(soft_risks, "deployment_stability_requirement", SOFT_RISK_CONFIG["deployment_stability_requirement"])

    for clause in _segments(text):
        if not _is_negated(clause) and _has_any(clause.lower(), ["react", "next.js", "nextjs", "typescript"]):
            if _has_any(clause, ["必须", "精通", "熟练", "硬要求"]):
                _add_unique(soft_risks, "react_next_typescript_hard", SOFT_RISK_CONFIG["react_next_typescript_hard"])
                break

    if _has_explicit_java_backend_requirement(text):
        _add_unique(soft_risks, "java_backend_heavy", SOFT_RISK_CONFIG["java_backend_heavy"])

    if _has_backend_responsibility(text):
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

    if has_production:
        _add_unique(soft_risks, "possible_not_junior_friendly", SOFT_RISK_CONFIG["possible_not_junior_friendly"])
        _add_unique(soft_risks, "agent_keyword_trap", SOFT_RISK_CONFIG["agent_keyword_trap"])

    if _has_any(text, ["运营边界不清", "技术/运营占比未确认", "可能涉及运营支持"]):
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
        if risk_type == "requires_independent_full_agent_framework":
            continue
        if not _has_positive_term(text, RISK_CONFIRM_TERMS.get(risk_type, [keyword])):
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

    if _has_independent_from_zero_agent_requirement(jd):
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

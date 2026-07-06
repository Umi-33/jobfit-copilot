from typing import Dict, List, Union

from .jd_parser import parse_jd
from .profile_parser import EDUCATION_LEVELS, parse_profile
from .project_matcher import calculate_project_score, match_projects
from .risk_detector import detect_risks


PRIMARY_SKILL_WEIGHTS = {
    "Vue3": 5,
    "JavaScript": 4,
    "Python": 5,
    "FastAPI": 4,
    "LLM API": 5,
    "Prompt": 4,
    "JSON/CSV": 3,
    "ECharts": 3,
    "数据可视化": 4,
    "AI 工具落地": 5,
    "AIGC 内容管线": 4,
}

SUPPLEMENTARY_SKILLS = {"React", "Next.js", "TypeScript", "Docker", "Linux", "LangChain", "RAG", "Agent"}
PRODUCTION_RAG_AGENT_HINTS = ["生产级", "复杂 agent", "agent 框架", "rag 系统", "向量数据库", "知识库检索", "langchain"]


def _as_profile(profile: Union[str, Dict]) -> Dict:
    return parse_profile(profile) if isinstance(profile, str) else profile


def _as_jd(jd: Union[str, Dict]) -> Dict:
    return parse_jd(jd) if isinstance(jd, str) else jd


def score_skills(profile: Dict, jd: Dict) -> Dict:
    """Score direct skill overlap while keeping advanced-only items low impact."""
    profile_skills = set(profile.get("skills", []))
    jd_skills = set(jd.get("tech_keywords", []))
    matched_items: List[Dict] = []
    missing_items: List[Dict] = []
    score = 0

    for skill in sorted(jd_skills):
        if skill in profile_skills:
            if skill in PRIMARY_SKILL_WEIGHTS:
                points = PRIMARY_SKILL_WEIGHTS[skill]
                score += points
                matched_items.append({"item": skill, "points": points, "reason": "用户画像中已有该核心能力。"})
            elif skill in SUPPLEMENTARY_SKILLS:
                matched_items.append({"item": skill, "points": 1, "reason": "仅作为可补充了解项，不高估匹配度。"})
        else:
            reason = "岗位要求该能力，用户画像中未体现。"
            if skill in SUPPLEMENTARY_SKILLS:
                reason = "可补充了解项，不能包装成成熟经验。"
            missing_items.append({"item": skill, "reason": reason})

    supplementary_matches = len(jd_skills & profile_skills & SUPPLEMENTARY_SKILLS)
    score += min(supplementary_matches, 3)
    return {
        "skill_score": min(score, 30),
        "matched_items": matched_items,
        "missing_items": missing_items,
    }


def score_experience(profile: Dict, jd: Dict) -> Dict:
    """Score experience by comparing profile years with JD minimum years."""
    profile_years = float(profile.get("experience_years", 0))
    required_min = float(jd.get("experience", {}).get("min") or 0)

    if required_min <= 0:
        score = 18
        reason = "岗位经验要求不限或未明确。"
    elif profile_years >= required_min:
        score = 20
        reason = f"用户经验 {profile_years:g} 年满足岗位最低 {required_min:g} 年要求。"
    elif profile_years + 0.5 >= required_min:
        score = 14
        reason = f"用户经验 {profile_years:g} 年接近岗位最低 {required_min:g} 年要求。"
    elif required_min >= 3:
        score = 6
        reason = f"岗位要求 {required_min:g} 年以上，明显高于当前画像。"
    else:
        score = 10
        reason = f"用户经验 {profile_years:g} 年低于岗位最低 {required_min:g} 年要求。"

    return {"experience_score": score, "experience_reason": reason}


def score_basic(profile: Dict, jd: Dict) -> Dict:
    """Score city, education and salary baseline fit."""
    score = 0
    matched = []
    missing = []

    city = jd.get("city")
    preferred_cities = profile.get("preferred_cities", [])
    if not city or city in preferred_cities or "远程" in preferred_cities:
        score += 5
        matched.append({"item": "城市", "points": 5, "reason": "城市未限制或符合用户偏好。"})
    else:
        missing.append({"item": "城市", "reason": f"岗位城市 {city} 不在用户偏好城市中。"})

    jd_education = jd.get("education", "不限")
    profile_education = profile.get("education", "不限")
    if EDUCATION_LEVELS.get(profile_education, 0) >= EDUCATION_LEVELS.get(jd_education, 0):
        score += 5
        matched.append({"item": "学历", "points": 5, "reason": f"用户学历 {profile_education} 满足岗位 {jd_education} 要求。"})
    else:
        missing.append({"item": "学历", "reason": f"用户学历 {profile_education} 低于岗位 {jd_education} 要求。"})

    salary = jd.get("salary", {})
    salary_max = salary.get("max")
    salary_floor = profile.get("salary_floor", 8000)
    if salary_max is None or salary_max >= salary_floor:
        score += 5
        matched.append({"item": "薪资底线", "points": 5, "reason": "岗位薪资上限未低于用户底线。"})
    else:
        missing.append({"item": "薪资底线", "reason": f"岗位薪资上限 {salary_max} 低于用户底线 {salary_floor}。"})

    return {"basic_score": score, "matched_items": matched, "missing_items": missing}


def score_bonus(profile: Dict, jd: Dict) -> Dict:
    """Add small bonuses for practical AI, AIGC and visualization fit."""
    profile_skills = set(profile.get("skills", []))
    jd_skills = set(jd.get("tech_keywords", []))
    raw_text = jd.get("raw_text", "").lower()
    bonus_items = []
    score = 0

    if {"AI 工具落地", "LLM API", "Prompt"} & profile_skills and any(word in raw_text for word in ["ai", "大模型", "智能", "llm"]):
        score += 4
        bonus_items.append({"item": "AI 工具落地", "points": 4, "reason": "岗位与 AI 应用落地相关。"})

    if "AIGC 内容管线" in profile_skills and any(word in raw_text for word in ["aigc", "内容", "生成"]):
        score += 3
        bonus_items.append({"item": "AIGC 内容管线", "points": 3, "reason": "岗位涉及内容生成或 AIGC 流程。"})

    if {"ECharts", "数据可视化"} & profile_skills and {"ECharts", "数据可视化"} & jd_skills:
        score += 3
        bonus_items.append({"item": "数据可视化", "points": 3, "reason": "岗位需要图表或看板能力。"})

    return {"bonus_score": min(score, 10), "bonus_items": bonus_items}


def has_production_rag_agent_requirement(jd: Dict) -> bool:
    """Detect JD wording that implies mature RAG or Agent engineering expectations."""
    raw_text = jd.get("raw_text", "").lower()
    has_advanced_skill = bool({"RAG", "Agent", "LangChain"} & set(jd.get("tech_keywords", [])))
    has_production_hint = any(hint in raw_text for hint in PRODUCTION_RAG_AGENT_HINTS)
    return has_advanced_skill and has_production_hint


def build_rating(total_score: int, risk_report: Dict) -> str:
    """Convert score and hard risks into a human-readable rating."""
    if risk_report["risk_level"] == "high":
        return "高风险，不建议投递"
    if total_score >= 80:
        return "强推荐"
    if total_score >= 65:
        return "可投递"
    if total_score >= 50:
        return "谨慎尝试"
    return "不推荐"


def score_job(profile_input: Union[str, Dict], jd_input: Union[str, Dict]) -> Dict:
    """Run the full V0 deterministic scoring pipeline."""
    profile = _as_profile(profile_input)
    jd = _as_jd(jd_input)

    skill_result = score_skills(profile, jd)
    experience_result = score_experience(profile, jd)
    basic_result = score_basic(profile, jd)
    recommended_projects = match_projects(profile, jd)
    project_score = calculate_project_score(recommended_projects)
    bonus_result = score_bonus(profile, jd)
    risk_report = detect_risks(jd, profile)

    matched_items = skill_result["matched_items"] + basic_result["matched_items"] + bonus_result["bonus_items"]
    missing_items = skill_result["missing_items"] + basic_result["missing_items"]

    advanced_cap = None
    if has_production_rag_agent_requirement(jd):
        advanced_cap = 62
        missing_items.append(
            {
                "item": "生产级 RAG/Agent 工程经验",
                "reason": "JD 明确偏生产级 RAG/Agent，当前画像只能按可补充了解处理，不能包装成成熟工程经验。",
            }
        )

    subtotal = (
        skill_result["skill_score"]
        + experience_result["experience_score"]
        + project_score
        + basic_result["basic_score"]
        + bonus_result["bonus_score"]
        + risk_report["risk_score"]
    )
    total_score = max(0, min(100, int(round(subtotal))))

    if advanced_cap is not None:
        total_score = min(total_score, advanced_cap)
    if any(item["type"] in {"培训贷", "纯销售", "薪资低于底线", "无薪试岗"} for item in risk_report["risk_items"]):
        total_score = min(total_score, 45)
    elif any(item["type"] in {"单休", "大小周"} for item in risk_report["risk_items"]):
        total_score = min(total_score, 68)

    return {
        "total_score": total_score,
        "rating": build_rating(total_score, risk_report),
        "skill_score": skill_result["skill_score"],
        "experience_score": experience_result["experience_score"],
        "experience_reason": experience_result["experience_reason"],
        "project_score": project_score,
        "basic_score": basic_result["basic_score"],
        "bonus_score": bonus_result["bonus_score"],
        "risk_score": risk_report["risk_score"],
        "matched_items": matched_items,
        "missing_items": missing_items,
        "risk_items": risk_report["risk_items"],
        "recommended_projects": recommended_projects,
        "parsed_profile": profile,
        "parsed_jd": jd,
    }


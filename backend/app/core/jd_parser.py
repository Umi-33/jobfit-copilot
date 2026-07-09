import re
from typing import Dict, List, Optional, Tuple

from .profile_parser import CITIES, SKILL_ALIASES


RISK_ALIASES = {
    "单休": ["单休", "做六休一", "周休1天"],
    "大小周": ["大小周"],
    "纯销售": ["纯销售", "电销", "电话销售", "地推", "陌拜"],
    "销售倾向": ["销售", "客户转化", "邀约", "成单", "提成"],
    "运营占比高": ["运营占比高", "主要做运营", "运营为主", "偏运营", "以运营为主", "运营占比"],
    "培训贷": ["培训贷", "贷款培训", "先交费", "先缴费", "付费培训"],
    "无薪试岗": ["无薪", "试岗无薪"],
    "压薪明显": ["压薪"],
    "先实习看看且转正不明": ["先实习看看", "转正不明", "转正标准不明"],
    "沟通不尊重": ["沟通不尊重", "不尊重"],
    "独立从0搭生产级Agent框架": ["独立从0", "独立从 0", "从0搭建", "从 0 搭建", "从0搭"],
    "强 KPI": ["kpi", "业绩指标", "强考核"],
    "高压加班": ["抗压", "996", "加班严重"],
}

EDUCATION_ORDER = ["不限", "大专", "本科", "硕士", "博士"]


def _word_in_text(text_lower: str, word: str) -> bool:
    word_lower = word.lower()
    if re.fullmatch(r"[a-z0-9.+#]{1,2}", word_lower):
        return re.search(rf"(?<![a-z0-9]){re.escape(word_lower)}(?![a-z0-9])", text_lower) is not None
    return word_lower in text_lower


def _contains_any(text_lower: str, words: List[str]) -> bool:
    return any(_word_in_text(text_lower, word) for word in words)


def extract_city(text: str) -> Optional[str]:
    """Extract the first recognizable city from JD text."""
    for city in CITIES:
        if city in text:
            return city
    return None


def extract_salary(text: str) -> Dict:
    """Parse common monthly salary formats into min and max yuan values."""
    text_lower = text.lower().replace(" ", "")
    patterns: List[Tuple[str, int]] = [
        (r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)k", 1000),
        (r"(\d+(?:\.\d+)?)k-(\d+(?:\.\d+)?)k", 1000),
        (r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)千", 1000),
        (r"(\d{4,5})-(\d{4,5})", 1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, text_lower, flags=re.IGNORECASE)
        if match:
            salary_min = int(float(match.group(1)) * multiplier)
            salary_max = int(float(match.group(2)) * multiplier)
            return {
                "min": min(salary_min, salary_max),
                "max": max(salary_min, salary_max),
                "raw": match.group(0),
            }

    single_match = re.search(r"(\d+(?:\.\d+)?)k", text_lower, flags=re.IGNORECASE)
    if single_match:
        value = int(float(single_match.group(1)) * 1000)
        return {"min": value, "max": value, "raw": single_match.group(0)}

    return {"min": None, "max": None, "raw": None}


def extract_experience(text: str) -> Dict:
    """Parse minimum and maximum experience requirements from JD text."""
    if "经验不限" in text or "不限经验" in text:
        return {"min": 0.0, "max": None, "raw": "经验不限"}

    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-~至]\s*(\d+(?:\.\d+)?)\s*年", text)
    if range_match:
        return {
            "min": float(range_match.group(1)),
            "max": float(range_match.group(2)),
            "raw": range_match.group(0),
        }

    min_match = re.search(r"(\d+(?:\.\d+)?)\s*年(?:以上|及以上|\+)", text)
    if min_match:
        return {"min": float(min_match.group(1)), "max": None, "raw": min_match.group(0)}

    simple_match = re.search(r"(\d+(?:\.\d+)?)\s*年", text)
    if simple_match:
        value = float(simple_match.group(1))
        return {"min": value, "max": value, "raw": simple_match.group(0)}

    return {"min": 0.0, "max": None, "raw": None}


def extract_education(text: str) -> str:
    """Extract the highest explicit education requirement."""
    found = [level for level in EDUCATION_ORDER if level != "不限" and level in text]
    if not found or "学历不限" in text or "不限学历" in text:
        return "不限"
    return max(found, key=lambda level: EDUCATION_ORDER.index(level))


def extract_tech_keywords(text: str) -> List[str]:
    """Extract normalized technical keywords from JD text."""
    text_lower = text.lower()
    return [skill for skill, aliases in SKILL_ALIASES.items() if _contains_any(text_lower, aliases)]


def extract_risk_keywords(text: str) -> List[str]:
    """Extract normalized risk keywords from JD text."""
    text_lower = text.lower()
    return [risk for risk, aliases in RISK_ALIASES.items() if _contains_any(text_lower, aliases)]


def parse_jd(text: str) -> Dict:
    """Parse JD text into the fields required by the V0 scorer."""
    tech_keywords = extract_tech_keywords(text)
    risk_keywords = extract_risk_keywords(text)
    advanced_keywords = [item for item in ["React", "Next.js", "TypeScript", "Docker", "Linux", "LangChain", "RAG", "Agent"] if item in tech_keywords]
    return {
        "raw_text": text,
        "city": extract_city(text),
        "salary": extract_salary(text),
        "experience": extract_experience(text),
        "education": extract_education(text),
        "tech_keywords": tech_keywords,
        "risk_keywords": risk_keywords,
        "advanced_keywords": advanced_keywords,
    }

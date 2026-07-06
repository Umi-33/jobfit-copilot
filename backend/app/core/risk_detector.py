from typing import Dict, List


RISK_PENALTIES = {
    "培训贷": {"severity": "high", "penalty": 45, "reason": "涉及培训贷、先交费或付费培训，属于硬性风险。"},
    "纯销售": {"severity": "high", "penalty": 35, "reason": "岗位含纯销售、电销、地推等强销售属性。"},
    "单休": {"severity": "high", "penalty": 22, "reason": "单休会显著影响工作强度和长期稳定性。"},
    "大小周": {"severity": "medium", "penalty": 16, "reason": "大小周说明休息制度偏弱，需要谨慎。"},
    "运营占比高": {"severity": "medium", "penalty": 12, "reason": "运营占比高，可能偏离 AI 应用或研发岗位。"},
    "销售倾向": {"severity": "medium", "penalty": 10, "reason": "岗位有销售转化或提成倾向，需要确认实际职责。"},
    "无薪试岗": {"severity": "high", "penalty": 35, "reason": "无薪试岗属于明显用工风险。"},
    "强 KPI": {"severity": "medium", "penalty": 8, "reason": "强 KPI 或业绩考核会影响岗位稳定性。"},
    "高压加班": {"severity": "medium", "penalty": 8, "reason": "高压加班描述需要谨慎评估。"},
}


def detect_risks(jd: Dict, profile: Dict) -> Dict:
    """Convert JD risk keywords and salary conflicts into explicit risk items."""
    risk_items: List[Dict] = []
    seen = set()

    for keyword in jd.get("risk_keywords", []):
        config = RISK_PENALTIES.get(keyword)
        if not config or keyword in seen:
            continue
        seen.add(keyword)
        risk_items.append(
            {
                "type": keyword,
                "severity": config["severity"],
                "penalty": config["penalty"],
                "reason": config["reason"],
            }
        )

    salary = jd.get("salary", {})
    salary_floor = profile.get("salary_floor", 8000)
    salary_min = salary.get("min")
    salary_max = salary.get("max")
    if salary_max is not None and salary_max < salary_floor:
        risk_items.append(
            {
                "type": "薪资低于底线",
                "severity": "high",
                "penalty": 32,
                "reason": f"岗位薪资上限 {salary_max} 低于用户底线 {salary_floor}。",
            }
        )
    elif salary_min is not None and salary_min < salary_floor:
        risk_items.append(
            {
                "type": "薪资下限偏低",
                "severity": "medium",
                "penalty": 8,
                "reason": f"岗位薪资下限 {salary_min} 低于用户底线 {salary_floor}，需要确认实际 offer。",
            }
        )

    total_penalty = min(sum(item["penalty"] for item in risk_items), 60)
    risk_level = "high" if any(item["severity"] == "high" for item in risk_items) else "medium" if risk_items else "low"
    return {
        "risk_score": -total_penalty,
        "risk_level": risk_level,
        "risk_items": risk_items,
    }


from typing import Dict, List


def match_projects(profile: Dict, jd: Dict) -> List[Dict]:
    """Rank user projects by overlap with JD keywords and AI application needs."""
    jd_keywords = set(jd.get("tech_keywords", []))
    raw_text = jd.get("raw_text", "").lower()
    recommended = []

    for project in profile.get("projects", []):
        tags = set(project.get("tags", []))
        overlap = sorted(tags & jd_keywords)
        score = len(overlap) * 3

        if "AI 工具落地" in tags and any(word in raw_text for word in ["ai", "大模型", "智能", "llm", "aigc"]):
            score += 4
        if "数据可视化" in tags and any(word in raw_text for word in ["可视化", "看板", "图表", "echarts"]):
            score += 3
        if "AIGC 内容管线" in tags and any(word in raw_text for word in ["aigc", "内容", "生成"]):
            score += 3

        if score <= 0:
            continue

        recommended.append(
            {
                "name": project["name"],
                "match_score": min(score, 20),
                "matched_tags": overlap,
                "reason": project.get("summary", ""),
            }
        )

    return sorted(recommended, key=lambda item: item["match_score"], reverse=True)


def calculate_project_score(recommended_projects: List[Dict]) -> int:
    """Calculate a capped project score from ranked project matches."""
    if not recommended_projects:
        return 4
    top_scores = [item["match_score"] for item in recommended_projects[:2]]
    return min(sum(top_scores), 20)


from typing import Dict, List


def _item_names(items: List[Dict], key: str = "item") -> List[str]:
    return [str(item.get(key)) for item in items if item.get(key)]


def generate_mock_llm_output(analysis: Dict) -> Dict:
    """Generate deterministic interview advice without changing rule scores."""
    rating = analysis["rating"]
    total_score = analysis["total_score"]
    matched_names = _item_names(analysis.get("matched_items", []))
    missing_names = _item_names(analysis.get("missing_items", []))
    risk_names = _item_names(analysis.get("risk_items", []), key="type")
    projects = analysis.get("recommended_projects", [])

    greeting = f"这个岗位整体判断为「{rating}」，规则分数是 {total_score}。建议先看匹配项、缺口和风险项，再决定是否投递。"

    talking_points = []
    for project in projects[:3]:
        tags = "、".join(project.get("matched_tags", [])) or "岗位相关能力"
        talking_points.append(
            f"围绕「{project['name']}」说明：业务问题是什么、用了哪些能力（{tags}）、如何验证效果、遇到限制后如何复盘。"
        )
    if not talking_points:
        talking_points.append("优先选择真实做过的小工具或看板项目，讲清楚输入、处理流程、输出和边界。")

    weakness_reminders = []
    if missing_names:
        weakness_reminders.append(f"这些能力需要谨慎表达：{'、'.join(missing_names[:6])}。没有真实项目时只说正在补充了解。")
    weakness_reminders.append("不要把自己包装成成熟 Agent/RAG 工程师，也不要补造生产级经历。")
    if risk_names:
        weakness_reminders.append(f"岗位风险需要提前确认：{'、'.join(risk_names)}。")

    possible_questions = [
        "你做过的 AI 工具解决了什么具体问题？",
        "Prompt 是如何迭代的，如何判断输出质量？",
        "如果输入是 JSON/CSV，你会如何清洗和校验数据？",
        "Vue3 或 ECharts 项目中，数据流和组件拆分是怎么设计的？",
    ]
    if any(name in missing_names for name in ["RAG", "Agent", "LangChain", "生产级 RAG/Agent 工程经验"]):
        possible_questions.append("如果面试官追问 RAG/Agent，你如何说明当前边界和学习计划？")

    return {
        "greeting_message": greeting,
        "interview_talking_points": talking_points,
        "weakness_reminders": weakness_reminders,
        "possible_questions": possible_questions,
    }


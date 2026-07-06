import re
from typing import Dict, List


SKILL_ALIASES = {
    "Vue3": ["vue3", "vue 3", "vue"],
    "JavaScript": ["javascript", "js"],
    "Python": ["python"],
    "FastAPI": ["fastapi", "fast api"],
    "LLM API": ["llm api", "openai api", "大模型 api", "大模型接口", "通义", "智谱", "deepseek"],
    "Prompt": ["prompt", "提示词"],
    "JSON/CSV": ["json", "csv"],
    "ECharts": ["echarts", "e charts"],
    "数据可视化": ["数据可视化", "可视化", "图表"],
    "AI 工具落地": ["ai 工具落地", "ai工具落地", "ai 工具原型", "ai工具原型", "ai 工具", "ai工具", "ai 应用", "ai应用", "ai 助手", "ai助手"],
    "AIGC 内容管线": ["aigc 内容管线", "aigc内容管线", "内容管线", "aigc"],
    "React": ["react"],
    "Next.js": ["next.js", "nextjs", "next"],
    "TypeScript": ["typescript", "ts"],
    "Docker": ["docker"],
    "Linux": ["linux"],
    "LangChain": ["langchain"],
    "RAG": ["rag", "检索增强"],
    "Agent": ["agent", "智能体"],
}

CITIES = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "远程"]

EDUCATION_LEVELS = {
    "不限": 0,
    "大专": 1,
    "本科": 2,
    "硕士": 3,
    "博士": 4,
}


def _alias_in_text(text_lower: str, alias: str) -> bool:
    alias_lower = alias.lower()
    if re.fullmatch(r"[a-z0-9.+#]{1,2}", alias_lower):
        return re.search(rf"(?<![a-z0-9]){re.escape(alias_lower)}(?![a-z0-9])", text_lower) is not None
    return alias_lower in text_lower


def _contains_alias(text_lower: str, aliases: List[str]) -> bool:
    return any(_alias_in_text(text_lower, alias) for alias in aliases)


def extract_skills(text: str) -> List[str]:
    """Extract normalized skills from a free-form profile text."""
    text_lower = text.lower()
    return [skill for skill, aliases in SKILL_ALIASES.items() if _contains_alias(text_lower, aliases)]


def extract_experience_years(text: str) -> float:
    """Extract the largest mentioned year count as a simple experience estimate."""
    values = [float(match) for match in re.findall(r"(\d+(?:\.\d+)?)\s*年", text)]
    if not values:
        return 0.0
    return max(values)


def extract_salary_floor(text: str, default: int = 8000) -> int:
    """Extract the user's minimum acceptable monthly salary."""
    patterns = [
        r"(?:薪资底线|最低薪资|底线|低于)\s*(\d{4,5})",
        r"(\d{1,2})\s*k\s*(?:以下|以内)?\s*(?:不考虑|不接受)",
        r"(\d{1,2})\s*千\s*(?:以下|以内)?\s*(?:不考虑|不接受)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = int(match.group(1))
            return value * 1000 if value < 100 else value
    return default


def extract_education(text: str) -> str:
    """Find the highest education level mentioned in the profile."""
    found = [level for level in EDUCATION_LEVELS if level != "不限" and level in text]
    if not found:
        return "不限"
    return max(found, key=lambda item: EDUCATION_LEVELS[item])


def extract_preferred_cities(text: str) -> List[str]:
    """Extract city preferences from the profile."""
    return [city for city in CITIES if city in text]


def extract_projects(text: str, skills: List[str]) -> List[Dict]:
    """Build lightweight project cards from recognizable project descriptions."""
    projects = []
    text_lower = text.lower()

    if any(word in text_lower for word in ["岗位筛选", "简历", "面试", "jobfit", "ai助手", "ai 助手"]):
        projects.append(
            {
                "name": "AI 岗位筛选与面试准备助手",
                "tags": [tag for tag in ["Python", "FastAPI", "LLM API", "Prompt", "JSON/CSV", "AI 工具落地"] if tag in skills],
                "summary": "围绕岗位 JD 解析、规则评分和面试准备建议做 AI 应用原型。",
            }
        )

    if any(word in text_lower for word in ["aigc", "内容管线", "小红书", "公众号", "短视频"]):
        projects.append(
            {
                "name": "AIGC 内容管线工具",
                "tags": [tag for tag in ["Python", "Prompt", "LLM API", "AIGC 内容管线", "JSON/CSV"] if tag in skills],
                "summary": "将选题、素材整理、提示词生成和内容质检串成可复用流程。",
            }
        )

    if any(word in text_lower for word in ["echarts", "数据可视化", "看板", "图表"]):
        projects.append(
            {
                "name": "Vue3 数据可视化看板",
                "tags": [tag for tag in ["Vue3", "JavaScript", "ECharts", "数据可视化", "JSON/CSV"] if tag in skills],
                "summary": "使用 Vue3 和 ECharts 展示业务数据，处理 JSON/CSV 数据源。",
            }
        )

    if not projects:
        projects.append(
            {
                "name": "通用 Web 工具原型",
                "tags": skills[:5],
                "summary": "基于已有技能完成轻量 Web 工具或自动化脚本。",
            }
        )

    return projects


def parse_profile(text: str) -> Dict:
    """Parse the fixed user profile used by the V0 command-line prototype."""
    skills = extract_skills(text)
    return {
        "raw_text": text,
        "skills": skills,
        "experience_years": extract_experience_years(text),
        "education": extract_education(text),
        "preferred_cities": extract_preferred_cities(text),
        "salary_floor": extract_salary_floor(text),
        "projects": extract_projects(text, skills),
    }

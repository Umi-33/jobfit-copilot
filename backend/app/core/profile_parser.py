import re
from typing import Dict, List


SKILL_ALIASES = {
    "Vue3": ["vue3", "vue 3", "vue"],
    "JavaScript": ["javascript", "js"],
    "Python": ["python"],
    "FastAPI": ["fastapi", "fast api"],
    "LLM API": ["llm api", "openai api", "大模型 api", "大模型接口", "llm", "大模型", "通义", "智谱", "deepseek"],
    "Prompt": ["prompt", "提示词"],
    "JSON/CSV": ["json", "csv", "结构化输出", "数据处理"],
    "ECharts": ["echarts", "e charts"],
    "数据可视化": ["数据可视化", "可视化", "图表"],
    "AI 工具落地": [
        "ai 工具落地",
        "ai工具落地",
        "ai 工具原型",
        "ai工具原型",
        "ai 工具",
        "ai工具",
        "ai 应用",
        "ai应用",
        "ai 助手",
        "ai助手",
        "workflow",
        "工作流",
        "自动化流程",
        "业务自动化",
        "自动化提效",
        "流程优化",
        "codex工作流",
    ],
    "AIGC 内容管线": ["aigc 内容管线", "aigc内容管线", "内容管线", "aigc"],
    "React": ["react"],
    "Next.js": ["next.js", "nextjs"],
    "TypeScript": ["typescript", "ts"],
    "Docker": ["docker"],
    "Linux": ["linux"],
    "LangChain": ["langchain"],
    "RAG": ["rag", "检索增强"],
    "Agent": ["agent", "智能体", "agentic workflow", "agent workflow", "agent 工作流"],
}

CITIES = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "远程"]

EDUCATION_LEVELS = {
    "不限": 0,
    "大专": 1,
    "本科": 2,
    "硕士": 3,
    "博士": 4,
}

NEGATION_MARKERS = ["没有", "无", "未掌握", "不具备", "未使用", "不熟悉", "不了解", "缺乏", "不会"]
CLAUSE_SPLIT_PATTERN = r"(?:但是|不过|然而|但)|[\r\n。；;，,]"
TOP_LEVEL_PROFILE_SECTIONS = {
    "用户画像",
    "能力边界",
    "求职偏好",
    "技能",
    "项目能力",
    "城市偏好",
    "学历",
    "经验",
    "薪资底线",
    "补充了解",
    "求职方向",
}


def _alias_in_text(text_lower: str, alias: str) -> bool:
    alias_lower = alias.lower()
    if re.fullmatch(r"[a-z0-9.+# ]+", alias_lower):
        return re.search(rf"(?<![a-z0-9]){re.escape(alias_lower)}(?![a-z0-9])", text_lower) is not None
    return alias_lower in text_lower


def _contains_alias(text_lower: str, aliases: List[str]) -> bool:
    return any(_alias_in_text(text_lower, alias) for alias in aliases)


def extract_skills(text: str) -> List[str]:
    """Extract skills from affirmative profile clauses without promoting negations."""
    clauses = [clause.strip() for clause in re.split(CLAUSE_SPLIT_PATTERN, text.lower()) if clause.strip()]
    affirmative_clauses = [
        clause for clause in clauses if not any(marker in clause for marker in NEGATION_MARKERS)
    ]
    return [
        skill
        for skill, aliases in SKILL_ALIASES.items()
        if any(_contains_alias(clause, aliases) for clause in affirmative_clauses)
    ]


def extract_experience_years(text: str) -> float:
    """Extract plausible experience years while ignoring dates and project duration."""
    patterns = [
        r"(?:工作|开发|全职|相关)?经验\s*[:：]?\s*(\d{1,2}(?:\.\d+)?)\s*年",
        r"(\d{1,2}(?:\.\d+)?)\s*年[^。；;，,\r\n]{0,30}?经验",
    ]
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            clause_start = max(text.rfind(separator, 0, match.start()) for separator in ["。", "；", ";", "，", ",", "\n"])
            clause = text[clause_start + 1 : match.end()]
            if any(marker in clause for marker in ["项目持续", "项目周期", "项目历时", "入学", "毕业"]):
                continue
            value = float(match.group(1))
            if 0 <= value <= 50:
                values.append(value)
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
    """Build project cards from explicit declarations and their following lines."""
    blocks = []
    current = None

    for raw_line in text.splitlines():
        line = re.sub(r"^\s*[-*]\s*", "", raw_line).strip()
        if not line:
            continue

        project_content = None
        prefixed = re.match(r"^(?:项目|作品|毕设)\s*[：:]\s*(.+)$", line)
        completed = re.match(r"^(?:我)?(?:做过|开发过)\s*(.+)$", line)
        named = re.search(r"项目名称\s*[：:]?\s*(《[^》]+》|[^，,：:]+)", line)

        if prefixed:
            project_content = prefixed.group(1).strip()
        elif completed:
            project_content = completed.group(1).strip()
        elif named:
            project_content = line

        if project_content is not None:
            if current:
                blocks.append(current)

            named_content = re.search(r"项目名称\s*[：:]?\s*(《[^》]+》|[^，,：:]+)", project_content)
            if named_content:
                name = named_content.group(1).strip()
                trailing = project_content[named_content.end() :].lstrip("：:，, ").strip()
            else:
                parts = re.split(r"[，,]", project_content, maxsplit=1)
                name = parts[0].strip()
                trailing = parts[1].strip() if len(parts) > 1 else ""

            current = {"name": name, "descriptions": [trailing] if trailing else []}
            continue

        section = re.match(r"^([^：:]+)\s*[：:]", line)
        if section and section.group(1).strip() in TOP_LEVEL_PROFILE_SECTIONS:
            if current:
                blocks.append(current)
                current = None
            continue

        if current:
            current["descriptions"].append(line)

    if current:
        blocks.append(current)

    projects = []
    seen_names = set()
    for block in blocks:
        name = block["name"]
        if not name or name in seen_names:
            continue
        descriptions = [item for item in block["descriptions"] if item]
        block_text = "\n".join([name] + descriptions)
        declared_skills = set(extract_skills(block_text))
        projects.append(
            {
                "name": name,
                "tags": [skill for skill in skills if skill in declared_skills],
                "summary": "；".join(descriptions),
            }
        )
        seen_names.add(name)

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

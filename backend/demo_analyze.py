import json

from app.core.mock_llm_generator import generate_mock_llm_output
from app.core.rule_scorer import score_job


SAMPLE_PROFILE = """
用户画像：
- 城市偏好：上海、杭州、远程。
- 学历：本科。
- 经验：1.5 年 Web / AI 工具原型经验。
- 薪资底线：8000。
- 技能：Vue3、JavaScript、Python、FastAPI、LLM API、Prompt、JSON/CSV、ECharts、数据可视化。
- 项目：AI 岗位筛选与面试准备助手，包含 JD 解析、规则评分、Prompt 建议和命令行 demo。
- 项目：AIGC 内容管线工具，用 Python 处理选题、素材、提示词和结果表格。
- 项目：Vue3 数据可视化看板，用 ECharts 展示业务指标，处理 JSON/CSV 数据。
- 补充了解：React、TypeScript、Docker、Linux、LangChain、RAG，但没有生产级 Agent/RAG 项目。
"""


SAMPLE_JD = """
岗位：AI 应用开发助理
城市：上海
薪资：10-15k
经验：1-3 年
学历：本科及以上
职责：
1. 参与大模型 AI 工具落地，包括 Prompt 编写、LLM API 调用和业务流程梳理。
2. 使用 Python / FastAPI 开发轻量接口，处理 JSON/CSV 数据。
3. 配合前端用 Vue3、ECharts 完成数据可视化页面。
4. 有 AIGC 内容管线或自动化工具经验加分。
"""


def main() -> None:
    """Run the V0 analysis demo and print the full command-line result."""
    analysis = score_job(SAMPLE_PROFILE, SAMPLE_JD)
    mock_llm = generate_mock_llm_output(analysis)
    result = {
        "analysis": analysis,
        "mock_llm": mock_llm,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


import unittest

from backend.app.core.rule_scorer import score_job


CALIBRATION_PROFILE = """
用户画像：
- 城市偏好：上海、杭州、远程。
- 学历：本科。
- 经验：1.5 年 Web / AI 工具原型经验。
- 薪资底线：8000。
- 技能：Vue3、JavaScript、Python、FastAPI、LLM API、Prompt、JSON/CSV、ECharts、数据可视化、AI 工具落地、AIGC 内容管线。
- 项目：AI岗位筛选与面试准备助手MVP，包含 JD 解析、规则评分、Prompt 建议和命令行 demo。
- 项目：《绛珠踪》LLM API评估 + Prompt约束 + 结构化输出，用 Python 处理大模型输出质量和人工复核。
- 项目：Vue3 + FastAPI 毕设情感计算可视化系统，用 ECharts 展示业务指标，处理 JSON/CSV 数据。
- 项目：《筋缮》p5.js交互Web视觉实验。
- 项目：《绛珠踪》数据驱动视觉生成项目。
- 补充了解：React、TypeScript、Docker、Linux、LangChain、RAG，但没有生产级 Agent/RAG 项目。
"""


def risk_types(items):
    return {item["type"] for item in items}


class RuleScorerTests(unittest.TestCase):
    def test_high_match_ai_application_job_can_reach_a(self):
        jd = """
        AI 应用开发助理，上海，10-15k，本科，1-3 年。
        需要 Python、FastAPI、LLM API、Prompt、JSON/CSV、Vue3、ECharts、数据可视化。
        有 AI 工具落地和 AIGC 内容管线经验加分。
        """
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertEqual(result["rating"], "A")
        self.assertEqual(result["decision"], "可投但需确认")
        self.assertIn("是否双休/五天工作制", result["unknown_items"])
        self.assertFalse(result["hard_risks"])

    def test_tc_01_ai_tool_landing_high_match_but_unknown_capped(self):
        jd = "负责跨境电商业务场景中的AI工具落地，可能涉及Prompt、Workflow、AI工具使用、业务流程优化、内容/数据处理和自动化提效。JD信息不足：工作制、薪资、试用期、技术/运营占比未确认。"
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertEqual(result["rating"], "B+")
        self.assertEqual(result["decision"], "可投但需确认")
        self.assertFalse(result["hard_risks"])
        self.assertIn("技术/工具/数据处理内容是否≥60%", result["unknown_items"])
        self.assertIn("AI岗位筛选与面试准备助手MVP", [item["name"] for item in result["recommended_projects"]])

    def test_tc_02_ai_fullstack_school_recruiting_keeps_unknowns(self):
        jd = "AI全栈开发方向，校招岗位，可能涉及AI应用、前后端功能开发、接口联调、AI相关工具或系统开发。JD信息不足：是否外包/派遣、实际用工主体、工作制、薪资、后端深度未确认。"
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertEqual(result["rating"], "B-")
        self.assertEqual(result["decision"], "可投但需确认")
        self.assertIn("是否外包/派遣", result["unknown_items"])
        self.assertIn("实际用工主体是谁", result["unknown_items"])
        self.assertNotIn("backend_heavy", risk_types(result["soft_risks"]))

    def test_tc_03_vue_echarts_visualization_is_core_window(self):
        jd = "前端开发岗位，方向包含Vue、ECharts、大屏/数据可视化或相关前端页面开发。适合用Vue3、ECharts、前后端接口联调和可视化项目经验切入。JD信息不足：工作制、薪资、具体技术栈、是否接受应届未确认。"
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertEqual(result["rating"], "A-")
        self.assertEqual(result["decision"], "可投但需确认")
        self.assertIn("ai_relevance_low", risk_types(result["soft_risks"]))
        self.assertEqual(result["recommended_projects"][0]["name"], "Vue3 + FastAPI 毕设情感计算可视化系统")

    def test_tc_04_agent_production_requirement_is_capped(self):
        jd = "AI Agent工程师，1-3年经验，薪资约15-30K，可远程办公。岗位可能涉及生产级Agent、后端开发、Agent评估、稳定性、工具调用、系统化落地。JD信息不足：具体框架、部署要求、是否接受应届未确认。"
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertEqual(result["rating"], "C")
        self.assertNotEqual(result["decision"], "强推荐")
        soft = risk_types(result["soft_risks"])
        self.assertTrue({"production_agent_heavy", "backend_heavy", "agent_keyword_trap"} <= soft)
        self.assertIn("生产级 RAG/Agent 工程经验", [item["item"] for item in result["missing_items"]])

    def test_tc_05_agent_workflow_with_hard_risks_is_d(self):
        jd = "岗位表面描述包括Codex工作流、AI Agent搭建、自动化流程，可能围绕招聘/候选人筛选场景搭建AI工作流。面试后确认真实需求偏从0搭建招聘/候选人筛选类AI Agent框架，要求能独立上手；存在压薪、薪资不清、先实习看看、运营边界不清、沟通不尊重等风险。"
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertEqual(result["rating"], "D")
        self.assertEqual(result["decision"], "不建议推进")
        hard = risk_types(result["hard_risks"])
        self.assertTrue(
            {
                "salary_pressure",
                "internship_first_unclear_conversion",
                "communication_red_flag",
                "requires_independent_full_agent_framework",
            }
            <= hard
        )

    def test_salary_below_floor_is_hard_risk(self):
        jd = "初级前端开发，远程，5-7k，经验不限，学历不限。使用 Vue3 和 JavaScript 做简单后台页面。"
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertEqual(result["rating"], "D")
        self.assertEqual(result["decision"], "不建议推进")
        self.assertIn("salary_below_floor", risk_types(result["hard_risks"]))

    def test_work_schedule_unknown_blocks_strong_decision(self):
        jd = """
        AI 应用开发，上海，12-16k，本科，经验不限。
        需要 Python、FastAPI、LLM API、Prompt、JSON/CSV、Vue3、ECharts、数据可视化。
        """
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertIn(result["rating"], {"A", "A-"})
        self.assertIn("是否双休/五天工作制", result["unknown_items"])
        self.assertEqual(result["decision"], "可投但需确认")

    def test_deployment_stability_does_not_imply_docker_linux(self):
        jd = "AI 后端应用岗位，上海，12-18k，负责部署稳定性、线上维护和发布保障。"
        result = score_job(CALIBRATION_PROFILE, jd)
        soft = risk_types(result["soft_risks"])
        self.assertIn("deployment_stability_requirement", soft)
        self.assertNotIn("docker_linux_deployment", soft)

    def test_explicit_docker_linux_hits_docker_linux_deployment(self):
        jd = "AI 后端应用岗位，上海，12-18k，要求 Docker、Linux、Nginx 和服务器部署经验。"
        result = score_job(CALIBRATION_PROFILE, jd)
        self.assertIn("docker_linux_deployment", risk_types(result["soft_risks"]))

    def test_rag_agent_reason_does_not_invent_langchain_langgraph(self):
        jd = "AI RAG 应用岗位，上海，12-18k，负责 RAG 系统化落地和知识库检索效果优化。"
        result = score_job(CALIBRATION_PROFILE, jd)
        reasons = [item["reason"] for item in result["soft_risks"] if item["type"] == "rag_agent_framework_heavy"]
        self.assertTrue(reasons)
        self.assertFalse(any("LangChain" in reason or "LangGraph" in reason for reason in reasons))

    def test_explicit_langchain_langgraph_allows_framework_reason(self):
        jd = "AI RAG 应用岗位，上海，12-18k，明确要求 LangChain、LangGraph 和 RAG 框架经验。"
        result = score_job(CALIBRATION_PROFILE, jd)
        reasons = [item["reason"] for item in result["soft_risks"] if item["type"] == "rag_agent_framework_heavy"]
        self.assertTrue(any("LangChain" in reason or "LangGraph" in reason for reason in reasons))

    def test_possible_operation_support_is_boundary_unknown_not_ratio_high(self):
        jd = "AI 工具落地岗位，上海，10-15k，可能涉及运营支持和业务流程协同。"
        result = score_job(CALIBRATION_PROFILE, jd)
        soft = risk_types(result["soft_risks"])
        self.assertNotIn("operation_ratio_high", soft)
        self.assertIn("operation_boundary_unclear", soft)
        self.assertIn("运营支持是否为主要职责", result["unknown_items"])


if __name__ == "__main__":
    unittest.main()

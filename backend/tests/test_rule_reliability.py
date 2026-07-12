import unittest

from backend.app.core.agent_planner import plan_next_actions
from backend.app.core.rule_scorer import score_job


PROFILE = """
用户画像：
- 城市偏好：上海、杭州、远程。
- 学历：本科。
- 经验：2026届应届生，无正式全职开发经验。
- 薪资底线：8000。
- 技能：Vue3、JavaScript、Python、FastAPI、LLM API、Prompt、JSON/CSV、ECharts、数据可视化、AI 工具落地、AIGC 内容管线。
- 项目：AI岗位筛选与面试准备助手MVP，包含 JD 解析、规则评分和命令行 demo。
- 补充了解：React、TypeScript、Docker、Linux、LangChain、RAG，但没有生产级 Agent/RAG 项目。
"""


def risk_types(result, field="soft_risks"):
    return {item["type"] for item in result[field]}


def bonus_names(result):
    return {item["item"] for item in result["matched_items"] if item.get("points")}


class RiskReliabilityTests(unittest.TestCase):
    def test_javascript_and_backend_collaboration_are_not_backend_risks(self):
        jd = "AI 前端开发，上海，10-15K，使用 JavaScript，与后端开发团队协作，负责前后端接口联调、调用后端 API，并与服务端进行数据交互。"
        result = score_job(PROFILE, jd)
        soft = risk_types(result)
        self.assertNotIn("java_backend_heavy", soft)
        self.assertNotIn("backend_heavy", soft)

    def test_explicit_java_and_spring_backend_requirements_still_trigger(self):
        for jd in [
            "负责 Java 后端开发，使用 Spring Boot。",
            "要求 SpringCloud 微服务和高并发后端系统经验。",
        ]:
            with self.subTest(jd=jd):
                result = score_job(PROFILE, jd)
                self.assertIn("java_backend_heavy", risk_types(result))

    def test_explicit_backend_responsibility_still_triggers(self):
        result = score_job(PROFILE, "AI 全栈岗位，明确负责后端开发和服务端开发。")
        self.assertIn("backend_heavy", risk_types(result))

    def test_basic_rag_integration_does_not_trigger_heavy_or_cap(self):
        jd = "AI 前端岗位，负责对接 RAG 服务、调用 RAG 接口，了解 RAG 基本概念并调用 AI 平台 SDK。"
        result = score_job(PROFILE, jd)
        soft = risk_types(result)
        self.assertNotIn("rag_agent_framework_heavy", soft)
        self.assertNotIn("production_agent_heavy", soft)
        self.assertFalse(any("RAG/Agent" in reason for reason in result["cap_reasons"]))

    def test_agent_as_product_scenario_is_not_production_risk(self):
        result = score_job(PROFILE, "AI 前端产品岗位，Agent 是产品场景之一，前端负责集成 Agent 能力。")
        self.assertNotIn("production_agent_heavy", risk_types(result))
        self.assertNotIn("rag_agent_framework_heavy", risk_types(result))

    def test_mature_langgraph_rag_requirement_triggers_framework_risk(self):
        jd = "要求熟练掌握 LangGraph，并负责搭建 RAG 系统，具备完整 RAG 项目经验。"
        result = score_job(PROFILE, jd)
        self.assertIn("rag_agent_framework_heavy", risk_types(result))
        self.assertTrue(any("成熟 RAG/Agent 框架" in reason for reason in result["cap_reasons"]))

    def test_independent_production_agent_still_triggers_strict_limits(self):
        jd = "要求候选人独立负责生产级 Agent 系统，包括生产部署和故障处理。"
        result = score_job(PROFILE, jd)
        self.assertIn("requires_independent_full_agent_framework", risk_types(result, "hard_risks"))
        self.assertIn("production_agent_heavy", risk_types(result))
        self.assertEqual(result["rating"], "D")

    def test_from_zero_non_agent_work_does_not_trigger_agent_hard_risk(self):
        for jd in ["从 0 搭建前端页面", "从0搭建 Web 工具", "从 0 到 1 推进普通业务系统"]:
            with self.subTest(jd=jd):
                result = score_job(PROFILE, jd)
                self.assertNotIn(
                    "requires_independent_full_agent_framework",
                    risk_types(result, "hard_risks"),
                )

    def test_negated_requirements_do_not_trigger_risks(self):
        jd = "无需 Docker / Linux 经验，不要求容器化部署。React 了解即可，不要求 LangChain 项目经验。非销售岗，不设销售 KPI，不是单休。"
        result = score_job(PROFILE, jd)
        soft = risk_types(result)
        hard = risk_types(result, "hard_risks")
        self.assertFalse(
            {"docker_linux_deployment", "react_next_typescript_hard", "rag_agent_framework_heavy", "sales_tendency", "strong_kpi"} & soft
        )
        self.assertNotIn("single_rest", hard)

    def test_explicit_docker_linux_requirement_still_triggers(self):
        result = score_job(PROFILE, "明确要求 Docker、Linux、Nginx 和服务器部署经验。")
        self.assertIn("docker_linux_deployment", risk_types(result))

    def test_generative_ai_frontend_has_no_aigc_content_bonus(self):
        result = score_job(PROFILE, "生成式 AI 前端岗位，负责自动生成结果和生成页面。")
        self.assertNotIn("AIGC 内容管线", bonus_names(result))

    def test_explicit_aigc_content_pipeline_keeps_bonus(self):
        result = score_job(PROFILE, "负责 AIGC 内容管线和批量内容生产，覆盖文案生成与审核。")
        self.assertIn("AIGC 内容管线", bonus_names(result))

    def test_plain_integration_does_not_get_ai_landing_bonus(self):
        result = score_job(PROFILE, "普通全栈岗位，负责接口联调和智能页面展示。")
        self.assertNotIn("AI 工具落地", bonus_names(result))

    def test_explicit_ai_api_integration_keeps_ai_landing_bonus(self):
        result = score_job(PROFILE, "AI 应用开发岗位，负责大模型 API 和 AI 平台集成。")
        self.assertIn("AI 工具落地", bonus_names(result))

    def test_remote_preference_does_not_match_unrelated_onsite_city(self):
        result = score_job(PROFILE, "北京线下办公的 AI 前端岗位，薪资10-15K。")
        city_matches = [item for item in result["matched_items"] if item["item"] == "城市"]
        city_missing = [item for item in result["missing_items"] if item["item"] == "城市"]
        self.assertFalse(city_matches)
        self.assertTrue(city_missing)

    def test_basic_rag_job_has_no_production_planner_warning(self):
        analysis = score_job(PROFILE, "AI 前端岗位，对接 RAG 服务并了解 RAG 基本概念。")
        plan = plan_next_actions(analysis)
        self.assertNotIn("不能声称独立负责生产级 Agent 框架", plan["blocked_outputs"])

    def test_production_agent_job_keeps_planner_warning(self):
        analysis = score_job(PROFILE, "独立负责生产级 Agent 系统的生产部署、监控和故障处理。")
        plan = plan_next_actions(analysis)
        self.assertIn("不能声称独立负责生产级 Agent 框架", plan["blocked_outputs"])

    def test_school_recruit_ai_frontend_regression(self):
        jd = """
        某游戏公司校招 AI 前端开发，上海，10-15K，本科及以上，面向2026届毕业生。
        使用 JavaScript、React 和 TypeScript 开发 AI 产品前端，与后端开发团队协作，完成前后端接口联调和数据交互。
        负责对接大模型 API、RAG 服务和 AI 平台 SDK；了解 RAG 基本概念，Agent 是产品场景之一。
        无需 Docker / Linux 运维部署经验。
        """
        result = score_job(PROFILE, jd)
        soft = risk_types(result)
        self.assertFalse(
            {"java_backend_heavy", "backend_heavy", "rag_agent_framework_heavy", "production_agent_heavy", "docker_linux_deployment"} & soft
        )
        self.assertFalse(any("RAG/Agent" in reason for reason in result["cap_reasons"]))
        self.assertNotIn("AIGC 内容管线", bonus_names(result))
        self.assertIn("是否双休/五天工作制", result["unknown_items"])
        self.assertEqual(result["decision"], "可投但需确认")
        self.assertNotEqual(result["rating"], "C+")


if __name__ == "__main__":
    unittest.main()

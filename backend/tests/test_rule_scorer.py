import unittest

from backend.app.core.rule_scorer import score_job


BASE_PROFILE = """
用户画像：
- 城市偏好：上海、杭州、远程。
- 学历：本科。
- 经验：1.5 年 Web / AI 工具原型经验。
- 薪资底线：8000。
- 技能：Vue3、JavaScript、Python、FastAPI、LLM API、Prompt、JSON/CSV、ECharts、数据可视化、AI 工具落地、AIGC 内容管线。
- 项目：AI 岗位筛选与面试准备助手，包含 JD 解析、规则评分、Prompt 建议和命令行 demo。
- 项目：AIGC 内容管线工具，用 Python 处理选题、素材、提示词和结果表格。
- 项目：Vue3 数据可视化看板，用 ECharts 展示业务指标，处理 JSON/CSV 数据。
- 补充了解：React、TypeScript、Docker、Linux、LangChain、RAG，但没有生产级 Agent/RAG 项目。
"""


class RuleScorerTests(unittest.TestCase):
    def test_high_match_ai_application_job(self):
        jd = """
        AI 应用开发助理，上海，10-15k，本科，1-3 年。
        需要 Python、FastAPI、LLM API、Prompt、JSON/CSV、Vue3、ECharts、数据可视化。
        有 AI 工具落地和 AIGC 内容管线经验加分。
        """
        result = score_job(BASE_PROFILE, jd)
        self.assertGreaterEqual(result["total_score"], 80)
        self.assertEqual(result["rating"], "强推荐")
        self.assertTrue(any(item["name"] == "AI 岗位筛选与面试准备助手" for item in result["recommended_projects"]))

    def test_normal_vue_frontend_job(self):
        jd = """
        Vue 前端开发，杭州，8-12k，本科，1 年以上。
        负责 Vue3、JavaScript 页面开发，使用 ECharts 做数据可视化，处理 JSON 数据。
        React、TypeScript 了解即可。
        """
        result = score_job(BASE_PROFILE, jd)
        self.assertGreaterEqual(result["total_score"], 65)
        self.assertLess(result["total_score"], 90)
        self.assertIn(result["rating"], {"可投递", "强推荐"})
        self.assertGreaterEqual(result["skill_score"], 15)

    def test_rag_agent_production_requirement_is_not_overrated(self):
        jd = """
        生产级 RAG / Agent 工程师，北京，18-30k，本科，3 年以上。
        要求 LangChain、RAG 系统、复杂 Agent 框架、向量数据库、Docker、Linux 生产部署经验。
        """
        result = score_job(BASE_PROFILE, jd)
        self.assertLessEqual(result["total_score"], 62)
        self.assertNotEqual(result["rating"], "强推荐")
        self.assertTrue(any(item["item"] == "生产级 RAG/Agent 工程经验" for item in result["missing_items"]))

    def test_single_rest_sales_operation_risk_job(self):
        jd = """
        AI 运营销售，上海，10-20k，经验不限，学历不限。
        工作内容包含电话销售、客户邀约、社群运营、内容运营，单休，强 KPI，提成制。
        """
        result = score_job(BASE_PROFILE, jd)
        self.assertEqual(result["rating"], "高风险，不建议投递")
        self.assertLessEqual(result["total_score"], 45)
        risk_types = {item["type"] for item in result["risk_items"]}
        self.assertTrue({"单休", "纯销售"} <= risk_types)

    def test_salary_below_floor_job(self):
        jd = """
        初级前端开发，远程，5-7k，经验不限，学历不限。
        使用 Vue3 和 JavaScript 做简单后台页面。
        """
        result = score_job(BASE_PROFILE, jd)
        self.assertEqual(result["rating"], "高风险，不建议投递")
        self.assertLessEqual(result["total_score"], 45)
        self.assertTrue(any(item["type"] == "薪资低于底线" for item in result["risk_items"]))


if __name__ == "__main__":
    unittest.main()


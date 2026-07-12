import unittest

from backend.app.core.agent_planner import plan_next_actions
from backend.app.core.rule_scorer import score_job


PROFILE = """
用户画像：
- 城市偏好：上海、杭州、远程。
- 学历：本科。
- 经验：2026届应届生，无正式全职开发经验；有课程项目、毕业设计、个人项目和 AI 工具辅助开发原型经验。
- 薪资底线：8000。
- 技能：Vue3、JavaScript、Python、FastAPI、LLM API、Prompt、JSON/CSV、ECharts、数据可视化、AI 工具落地、AIGC 内容管线。
- 项目：AI岗位筛选与面试准备助手MVP，包含 JD 解析、规则评分、Prompt 建议和命令行 demo。
- 项目：Vue3 + FastAPI 毕设情感计算可视化系统，用 ECharts 展示业务指标，处理 JSON/CSV 数据。
- 补充了解：React、TypeScript、Docker、Linux、LangChain、RAG，但没有生产级 Agent/RAG 项目。
"""


def plan_for(jd: str):
    analysis = score_job(PROFILE, jd)
    return analysis, plan_next_actions(analysis)


class AgentPlannerTests(unittest.TestCase):
    def assert_human_approval(self, plan):
        self.assertTrue(plan["human_approval_required"])

    def test_high_match_job_prepares_application(self):
        jd = """
        AI 应用开发助理，上海，10-15k，本科，1-3 年。
        需要 Python、FastAPI、LLM API、Prompt、JSON/CSV、Vue3、ECharts、数据可视化。
        有 AI 工具落地和 AIGC 内容管线经验加分。
        """
        analysis, plan = plan_for(jd)
        self.assertEqual(analysis["rating"], "A")
        self.assertEqual(plan["primary_action"], "prepare_application")
        self.assertIn("prepare_interview", plan["secondary_actions"])
        self.assert_human_approval(plan)

    def test_many_unknowns_with_lower_fit_requires_manual_review(self):
        jd = "AI全栈开发方向，校招岗位，可能涉及AI应用、前后端功能开发、接口联调、AI相关工具或系统开发。JD信息不足：是否外包/派遣、实际用工主体、工作制、薪资、后端深度未确认。"
        analysis, plan = plan_for(jd)
        self.assertGreaterEqual(len(analysis["unknown_items"]), 3)
        self.assertEqual(plan["primary_action"], "manual_review_required")
        self.assert_human_approval(plan)

    def test_agent_rag_heavy_with_d_rating_is_archived(self):
        jd = "AI Agent工程师，1-3年经验，薪资约15-30K，可远程办公。岗位可能涉及生产级Agent、后端开发、Agent评估、稳定性、工具调用、系统化落地。JD信息不足：具体框架、部署要求、是否接受应届未确认。"
        analysis, plan = plan_for(jd)
        soft_types = {item["type"] for item in analysis["soft_risks"]}
        self.assertIn("production_agent_heavy", soft_types)
        self.assertEqual(plan["primary_action"], "archive_job")
        self.assertIn("不能声称独立负责生产级 Agent 框架", plan["blocked_outputs"])
        self.assert_human_approval(plan)

    def test_hard_risk_archives_job(self):
        jd = "岗位表面描述包括Codex工作流、AI Agent搭建。真实需求偏从0搭建招聘筛选类AI Agent框架，要求能独立上手；存在压薪、先实习看看、运营边界不清、沟通不尊重等风险。"
        analysis, plan = plan_for(jd)
        self.assertTrue(analysis["hard_risks"])
        self.assertEqual(plan["primary_action"], "archive_job")
        self.assertIn("manual_review_required", plan["secondary_actions"])
        self.assert_human_approval(plan)

    def test_all_plans_require_human_approval(self):
        jds = [
            "AI 应用开发助理，上海，10-15k，本科，1-3 年。需要 Python、FastAPI、LLM API、Prompt、JSON/CSV、Vue3、ECharts、数据可视化。",
            "AI全栈开发方向，校招岗位。JD信息不足：是否外包/派遣、实际用工主体、工作制、薪资、后端深度未确认。",
            "AI Agent工程师，1-3年经验，薪资约15-30K，可远程办公。岗位可能涉及生产级Agent、后端开发、稳定性。",
            "初级前端开发，远程，5-7k，经验不限，学历不限。使用 Vue3 和 JavaScript 做简单后台页面。",
        ]
        for jd in jds:
            with self.subTest(jd=jd):
                _, plan = plan_for(jd)
                self.assert_human_approval(plan)


if __name__ == "__main__":
    unittest.main()

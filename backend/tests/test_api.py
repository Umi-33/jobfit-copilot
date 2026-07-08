import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


PROFILE_TEXT = """
用户画像：
- 城市偏好：上海、杭州、远程。
- 学历：本科。
- 经验：2026届应届生，无正式全职开发经验；有课程项目、毕业设计、个人项目和 AI 工具辅助开发原型经验。
- 薪资底线：8000。
- 技能：Vue3、JavaScript、Python、FastAPI、LLM API、Prompt、JSON/CSV、ECharts、数据可视化、AI 工具落地。
- 项目：AI岗位筛选与面试准备助手MVP，包含 JD 解析、规则评分、Prompt 建议和命令行 demo。
"""

JD_TEXT = """
AI 应用开发助理，上海，10-15k，本科，经验不限。
需要 Python、FastAPI、LLM API、Prompt、JSON/CSV、Vue3、ECharts、数据可视化。
"""


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_returns_ok(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_analyze_returns_analysis_and_action_plan(self):
        response = self.client.post(
            "/api/analyze",
            json={"profile_text": PROFILE_TEXT, "jd_text": JD_TEXT},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("analysis", data)
        self.assertIn("action_plan", data)
        self.assertIn("rating", data["analysis"])
        self.assertIn("primary_action", data["action_plan"])

    def test_action_plan_requires_human_approval(self):
        response = self.client.post(
            "/api/analyze",
            json={"profile_text": PROFILE_TEXT, "jd_text": JD_TEXT},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["action_plan"]["human_approval_required"])

    def test_analyze_rejects_empty_text(self):
        response = self.client.post(
            "/api/analyze",
            json={"profile_text": " ", "jd_text": JD_TEXT},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

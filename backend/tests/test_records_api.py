import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.storage.database import DATABASE_ENV_VAR


PROFILE_TEXT = """
用户画像：
- 城市偏好：上海、杭州、远程。
- 学历：本科。
- 经验：2026届应届生，无正式全职开发经验。
- 薪资底线：8000。
- 技能：Vue3、JavaScript、Python、FastAPI、LLM API、Prompt、JSON/CSV、ECharts、数据可视化、AI 工具落地。
- 项目：AI岗位筛选与面试准备助手MVP，包含 JD 解析、规则评分和命令行 demo。
"""

JD_TEXT = """
AI 应用开发助理，上海，10-15k，本科，经验不限。
需要 Python、FastAPI、LLM API、Prompt、JSON/CSV、Vue3 和数据可视化。
"""


class RecordsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "records_api.sqlite3"
        self.environment = patch.dict(os.environ, {DATABASE_ENV_VAR: str(self.database_path)})
        self.environment.start()
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()
        self.payload = {
            "company_name": " 示例公司 ",
            "job_title": " AI 应用开发助理 ",
            "city": " 上海，支持远程 ",
            "profile_text": PROFILE_TEXT,
            "jd_text": JD_TEXT,
        }

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.environment.stop()
        self.temp_directory.cleanup()

    def create_record(self):
        response = self.client.post("/api/records", json=self.payload)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_record_returns_deserialized_analysis_and_plan(self):
        record = self.create_record()

        self.assertEqual(record["company_name"], "示例公司")
        self.assertEqual(record["job_title"], "AI 应用开发助理")
        self.assertEqual(record["city"], "上海，支持远程")
        self.assertIsInstance(record["analysis"], dict)
        self.assertIsInstance(record["action_plan"], dict)
        self.assertIsInstance(record["unknown_items"], list)
        self.assertTrue(record["action_plan"]["human_approval_required"])

    def test_list_returns_summary_only(self):
        self.create_record()
        response = self.client.get("/api/records")

        self.assertEqual(response.status_code, 200)
        record = response.json()[0]
        self.assertIn("rating", record)
        for large_field in ("jd_text", "profile_snapshot", "analysis", "action_plan", "unknown_items"):
            self.assertNotIn(large_field, record)

    def test_get_complete_record(self):
        created = self.create_record()
        response = self.client.get(f"/api/records/{created['id']}")

        self.assertEqual(response.status_code, 200)
        record = response.json()
        self.assertEqual(record["id"], created["id"])
        self.assertIn("jd_text", record)
        self.assertIn("profile_snapshot", record)
        self.assertIsInstance(record["analysis"], dict)

    def test_update_valid_status(self):
        created = self.create_record()
        response = self.client.patch(
            f"/api/records/{created['id']}/status",
            json={"status": "applied"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "applied")

    def test_invalid_status_returns_422(self):
        created = self.create_record()
        response = self.client.patch(
            f"/api/records/{created['id']}/status",
            json={"status": "unknown_status"},
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_record_returns_404(self):
        self.assertEqual(self.client.get("/api/records/999").status_code, 404)
        response = self.client.patch("/api/records/999/status", json={"status": "archived"})
        self.assertEqual(response.status_code, 404)

    def test_required_text_fields_reject_empty_or_whitespace(self):
        for field in ("company_name", "job_title", "city", "profile_text", "jd_text"):
            for invalid_value in ("", "   "):
                with self.subTest(field=field, value=repr(invalid_value)):
                    payload = self.payload.copy()
                    payload[field] = invalid_value
                    response = self.client.post("/api/records", json=payload)
                    self.assertEqual(response.status_code, 422)

    def test_uses_temporary_database_path(self):
        self.assertEqual(app.state.database_path, self.database_path)
        self.assertTrue(self.database_path.exists())


if __name__ == "__main__":
    unittest.main()

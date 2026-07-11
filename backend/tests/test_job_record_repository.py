import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from backend.app.storage.database import initialize_database
from backend.app.storage.job_record_repository import (
    create_job_record,
    get_job_record,
    list_job_records,
    update_job_record_status,
)


ANALYSIS = {
    "rating": "A-",
    "decision": "可投但需确认",
    "risk_level": "low",
    "unknown_items": ["是否双休/五天工作制"],
    "matched_items": [{"item": "Python", "reason": "技能匹配"}],
}
ACTION_PLAN = {
    "primary_action": "prepare_application",
    "human_approval_required": True,
    "agent_trace": [{"step": "select_action", "reason": "高匹配但需人工确认"}],
}


class JobRecordRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "repository.sqlite3"
        initialize_database(self.database_path)

    def tearDown(self):
        self.temp_directory.cleanup()

    def create_record(self):
        return create_job_record(
            company_name="杭州示例科技",
            job_title="AI 应用开发助理",
            city="杭州，支持远程",
            profile_snapshot="应届生，Python、Vue3、FastAPI。",
            jd_text="负责 AI 工具落地，工作制待确认。",
            analysis=ANALYSIS,
            action_plan=ACTION_PLAN,
            database_path=self.database_path,
        )

    def test_initialize_database_creates_table(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
                ("job_records",),
            ).fetchone()
        self.assertEqual(row[0], "job_records")

    def test_create_and_get_complete_record(self):
        created = self.create_record()
        loaded = get_job_record(created["id"], self.database_path)

        self.assertEqual(loaded["company_name"], "杭州示例科技")
        self.assertEqual(loaded["analysis"], ANALYSIS)
        self.assertEqual(loaded["action_plan"], ACTION_PLAN)
        self.assertEqual(loaded["unknown_items"], ANALYSIS["unknown_items"])

    def test_chinese_json_is_saved_without_ascii_escaping(self):
        created = self.create_record()
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT analysis_json FROM job_records WHERE id = ?",
                (created["id"],),
            ).fetchone()

        self.assertIn("可投但需确认", row[0])
        self.assertNotIn("\\u", row[0])
        self.assertEqual(json.loads(row[0]), ANALYSIS)

    def test_list_returns_summary_fields_only(self):
        self.create_record()
        rows = list_job_records(self.database_path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            set(rows[0]),
            {
                "id",
                "company_name",
                "job_title",
                "city",
                "rating",
                "decision",
                "risk_level",
                "status",
                "created_at",
                "updated_at",
            },
        )

    def test_update_valid_status(self):
        created = self.create_record()
        updated = update_job_record_status(created["id"], "applied", self.database_path)

        self.assertEqual(updated["status"], "applied")
        self.assertEqual(get_job_record(created["id"], self.database_path)["status"], "applied")

    def test_update_rejects_invalid_status(self):
        created = self.create_record()
        with self.assertRaises(ValueError):
            update_job_record_status(created["id"], "invalid", self.database_path)

    def test_missing_record_returns_none(self):
        self.assertIsNone(get_job_record(999, self.database_path))
        self.assertIsNone(update_job_record_status(999, "archived", self.database_path))


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.storage.database import DATABASE_ENV_VAR


LOCAL_ORIGIN = "http://localhost:5173"
UNTRUSTED_ORIGIN = "https://untrusted.example"
DEMO_CODE = "test-demo-code-never-log"
ANALYZE_PAYLOAD = {
    "profile_text": "技能：Vue3、Python、FastAPI。学历：本科。薪资底线：8000。",
    "jd_text": "AI 应用岗位，经验不限，需要 Vue3、Python、FastAPI，10-15k。",
}


class DeploymentSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "deployment_security.sqlite3"
        self.environment = patch.dict(
            os.environ,
            {
                DATABASE_ENV_VAR: str(self.database_path),
                "DEMO_ACCESS_CODE": "",
            },
        )
        self.environment.start()
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.environment.stop()
        self.temp_directory.cleanup()

    def test_api_remains_available_when_demo_code_is_not_configured(self):
        response = self.client.post("/api/analyze", json=ANALYZE_PAYLOAD)

        self.assertEqual(response.status_code, 200)
        self.assertIn("analysis", response.json())
        self.assertIn("action_plan", response.json())

    def test_missing_demo_code_is_rejected_when_protection_is_enabled(self):
        with patch.dict(os.environ, {"DEMO_ACCESS_CODE": DEMO_CODE}):
            response = self.client.get(
                "/api/access-check",
                headers={"Origin": LOCAL_ORIGIN},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Demo access code required or invalid"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), LOCAL_ORIGIN)
        self.assertNotIn(DEMO_CODE, response.text)

    def test_incorrect_demo_code_is_rejected(self):
        with patch.dict(os.environ, {"DEMO_ACCESS_CODE": DEMO_CODE}):
            response = self.client.get(
                "/api/access-check",
                headers={"X-Demo-Access-Code": "incorrect-code"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn(DEMO_CODE, response.text)

    def test_correct_demo_code_can_access_check_endpoint(self):
        with patch.dict(os.environ, {"DEMO_ACCESS_CODE": DEMO_CODE}):
            response = self.client.get(
                "/api/access-check",
                headers={"X-Demo-Access-Code": DEMO_CODE},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_does_not_require_demo_code(self):
        with patch.dict(os.environ, {"DEMO_ACCESS_CODE": DEMO_CODE}):
            response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_options_preflight_is_not_blocked_and_has_cors_headers(self):
        with patch.dict(os.environ, {"DEMO_ACCESS_CODE": DEMO_CODE}):
            response = self.client.options(
                "/api/access-check",
                headers={
                    "Origin": LOCAL_ORIGIN,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "X-Demo-Access-Code",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), LOCAL_ORIGIN)
        self.assertIn(
            "x-demo-access-code",
            response.headers.get("access-control-allow-headers", "").lower(),
        )

    def test_allowed_local_origin_gets_cors_response_header(self):
        response = self.client.get("/api/health", headers={"Origin": LOCAL_ORIGIN})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), LOCAL_ORIGIN)

    def test_untrusted_origin_does_not_get_cors_response_header(self):
        response = self.client.get("/api/health", headers={"Origin": UNTRUSTED_ORIGIN})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_access_denial_does_not_echo_or_log_demo_code(self):
        with patch.dict(os.environ, {"DEMO_ACCESS_CODE": DEMO_CODE}):
            with self.assertNoLogs("backend.app.main", level="DEBUG"):
                response = self.client.get(
                    "/api/access-check",
                    headers={"X-Demo-Access-Code": "wrong-value"},
                )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn(DEMO_CODE, response.text)
        self.assertNotIn("wrong-value", response.text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from datetime import date
import json
import tempfile
import threading
import unittest
from urllib import error, request

from app.config import Settings
from app.server import create_server


class ProductTelemetrySmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.settings = Settings(
            db_path=f"{cls.temp_dir.name}/integration.sqlite3",
            auth_secret="integration-secret",
            token_ttl_seconds=3600,
        )
        cls.server = create_server(settings=cls.settings, host="127.0.0.1", port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp_dir.cleanup()

    def test_signup_to_activation_dashboard(self) -> None:
        signup_status, signup_payload = self._request_json(
            "POST",
            "/api/v1/signup",
            {
                "email": "owner@acme.test",
                "password": "owner-password-123",
                "workspaceName": "Acme HQ",
                "accountName": "Acme",
            },
        )
        self.assertEqual(201, signup_status)
        owner_token = signup_payload["token"]
        workspace_id = signup_payload["workspace"]["id"]

        workspace_status, _ = self._request_json(
            "GET",
            f"/api/v1/workspaces/{workspace_id}",
            token=owner_token,
        )
        self.assertEqual(200, workspace_status)
        workspace_status_again, _ = self._request_json(
            "GET",
            f"/api/v1/workspaces/{workspace_id}",
            token=owner_token,
        )
        self.assertEqual(200, workspace_status_again)

        telemetry_status, telemetry_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/telemetry/events",
            body={
                "eventName": "onboarding.activation_completed",
                "properties": {"trigger": "integration-smoke"},
                "dedupeKey": f"activation:{workspace_id}",
            },
            token=owner_token,
        )
        self.assertEqual(202, telemetry_status)
        self.assertTrue(telemetry_payload["accepted"])

        telemetry_status_repeat, telemetry_payload_repeat = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/telemetry/events",
            body={
                "eventName": "onboarding.activation_completed",
                "dedupeKey": f"activation:{workspace_id}",
            },
            token=owner_token,
        )
        self.assertEqual(202, telemetry_status_repeat)
        self.assertFalse(telemetry_payload_repeat["accepted"])

        today = date.today().isoformat()
        dashboard_status, dashboard_payload = self._request_json(
            "GET",
            (
                f"/api/v1/workspaces/{workspace_id}/telemetry/funnel/daily"
                f"?from={today}&to={today}"
            ),
            token=owner_token,
        )
        self.assertEqual(200, dashboard_status)
        self.assertEqual(workspace_id, dashboard_payload["workspaceId"])
        self.assertEqual(today, dashboard_payload["from"])
        self.assertEqual(today, dashboard_payload["to"])

        self.assertEqual(1, len(dashboard_payload["days"]))
        steps = {
            step["eventName"]: step
            for step in dashboard_payload["days"][0]["steps"]
        }
        self.assertEqual(1, steps["onboarding.signup_completed"]["count"])
        self.assertEqual(1, steps["onboarding.workspace_first_accessed"]["count"])
        self.assertEqual(1, steps["onboarding.activation_completed"]["count"])
        self.assertEqual(100.0, steps["onboarding.activation_completed"]["conversionFromSignupPct"])

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, object] | None = None,
        token: str | None = None,
    ) -> tuple[int, dict[str, object]]:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = None
        headers = {"Content-Type": "application/json"}

        if body is not None:
            data = json.dumps(body).encode("utf-8")

        if token is not None:
            headers["Authorization"] = f"Bearer {token}"

        req = request.Request(url=url, data=data, method=method, headers=headers)

        try:
            with request.urlopen(req, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return response.status, payload
        except error.HTTPError as http_error:
            payload = json.loads(http_error.read().decode("utf-8"))
            return http_error.code, payload


if __name__ == "__main__":
    unittest.main()

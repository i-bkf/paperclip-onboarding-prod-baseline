from __future__ import annotations

import json
import tempfile
import threading
import unittest
from urllib import error, request

from app.config import Settings
from app.server import create_server


class ClosedBetaOnboardingSmokeTests(unittest.TestCase):
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

    def test_closed_beta_invite_onboarding_feedback_flow(self) -> None:
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

        invite_1_status, invite_1_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/beta/invitations",
            {
                "email": "pilot-user@acme.test",
                "role": "member",
                "cohort": "wave-1",
            },
            token=owner_token,
        )
        self.assertEqual(201, invite_1_status)
        invitation_1_id = invite_1_payload["invitation"]["id"]

        revoke_status, revoke_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/beta/invitations/{invitation_1_id}/revoke",
            token=owner_token,
        )
        self.assertEqual(200, revoke_status)
        self.assertEqual("revoked", revoke_payload["invitation"]["status"])

        invite_2_status, invite_2_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/beta/invitations",
            {
                "email": "pilot-user@acme.test",
                "role": "member",
                "cohort": "wave-1",
            },
            token=owner_token,
        )
        self.assertEqual(201, invite_2_status)
        invite_2_token = invite_2_payload["invitation"]["invitation_token"]

        accept_status, accept_payload = self._request_json(
            "POST",
            f"/api/v1/beta/invitations/{invite_2_token}/accept",
            {
                "email": "pilot-user@acme.test",
                "password": "pilot-password-123",
            },
        )
        self.assertEqual(201, accept_status)
        self.assertEqual("wave-1", accept_payload["cohort"])

        pilot_token = accept_payload["token"]
        self.assertEqual("member", accept_payload["membership"]["role"])

        step_1_status, step_1_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/onboarding/checklist/complete",
            {"stepKey": "profile_completed"},
            token=pilot_token,
        )
        self.assertEqual(202, step_1_status)
        self.assertTrue(step_1_payload["accepted"])
        self.assertEqual("wave-1", step_1_payload["cohort"])

        step_2_status, step_2_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/onboarding/checklist/complete",
            {"stepKey": "workspace_customized"},
            token=pilot_token,
        )
        self.assertEqual(202, step_2_status)
        self.assertTrue(step_2_payload["accepted"])
        self.assertEqual(2, len(step_2_payload["completedSteps"]))

        step_2_repeat_status, step_2_repeat_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/onboarding/checklist/complete",
            {"stepKey": "workspace_customized"},
            token=pilot_token,
        )
        self.assertEqual(202, step_2_repeat_status)
        self.assertFalse(step_2_repeat_payload["accepted"])

        progress_status, progress_payload = self._request_json(
            "GET",
            f"/api/v1/workspaces/{workspace_id}/onboarding/checklist/cohorts",
            token=owner_token,
        )
        self.assertEqual(200, progress_status)

        wave_1 = next(
            cohort
            for cohort in progress_payload["cohorts"]
            if cohort["cohort"] == "wave-1"
        )
        self.assertEqual(1, wave_1["membersCount"])

        wave_steps = {
            step["stepKey"]: step["completedUsers"]
            for step in wave_1["steps"]
        }
        self.assertEqual(1, wave_steps["profile_completed"])
        self.assertEqual(1, wave_steps["workspace_customized"])
        self.assertEqual(0, wave_steps["first_feedback_shared"])

        feedback_status, feedback_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/feedback",
            {
                "category": "bug",
                "message": "Onboarding hint tooltip overlaps the continue button on mobile.",
                "context": {"screen": "onboarding-checklist"},
            },
            token=pilot_token,
        )
        self.assertEqual(201, feedback_status)
        self.assertEqual("wave-1", feedback_payload["feedback"]["cohort"])
        self.assertTrue(feedback_payload["onboardingStepAccepted"])

        triage_ticket = feedback_payload["triageTicket"]
        self.assertEqual("open", triage_ticket["status"])
        self.assertEqual(
            feedback_payload["feedback"]["id"],
            triage_ticket["feedback_submission_id"],
        )

        progress_after_feedback_status, progress_after_feedback_payload = self._request_json(
            "GET",
            f"/api/v1/workspaces/{workspace_id}/onboarding/checklist/cohorts",
            token=owner_token,
        )
        self.assertEqual(200, progress_after_feedback_status)
        wave_1_after_feedback = next(
            cohort
            for cohort in progress_after_feedback_payload["cohorts"]
            if cohort["cohort"] == "wave-1"
        )
        wave_steps_after_feedback = {
            step["stepKey"]: step["completedUsers"]
            for step in wave_1_after_feedback["steps"]
        }
        self.assertEqual(1, wave_steps_after_feedback["first_feedback_shared"])
        self.assertEqual(1, wave_1_after_feedback["fullyCompletedUsers"])

    def test_idempotency_key_replays_mutating_workflow_steps(self) -> None:
        signup_status, signup_payload = self._request_json(
            "POST",
            "/api/v1/signup",
            {
                "email": "owner-idempotency@acme.test",
                "password": "owner-password-123",
                "workspaceName": "Acme Idempotency",
                "accountName": "Acme",
            },
        )
        self.assertEqual(201, signup_status)
        owner_token = signup_payload["token"]
        workspace_id = signup_payload["workspace"]["id"]

        invite_body = {
            "email": "pilot-idempotency@acme.test",
            "role": "member",
            "cohort": "wave-idempotency",
        }
        invite_status_1, invite_payload_1 = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/beta/invitations",
            invite_body,
            token=owner_token,
            extra_headers={"Idempotency-Key": "invite-idempotency-key"},
        )
        self.assertEqual(201, invite_status_1)
        invite_status_2, invite_payload_2 = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/beta/invitations",
            invite_body,
            token=owner_token,
            extra_headers={"Idempotency-Key": "invite-idempotency-key"},
        )
        self.assertEqual(201, invite_status_2)
        self.assertEqual(invite_payload_1, invite_payload_2)

        invite_conflict_status, invite_conflict_payload = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/beta/invitations",
            {
                "email": "pilot-idempotency@acme.test",
                "role": "member",
                "cohort": "wave-different",
            },
            token=owner_token,
            extra_headers={"Idempotency-Key": "invite-idempotency-key"},
        )
        self.assertEqual(400, invite_conflict_status)
        self.assertIn("Idempotency-Key", invite_conflict_payload["message"])

        invitation_token = invite_payload_1["invitation"]["invitation_token"]
        accept_body = {
            "email": "pilot-idempotency@acme.test",
            "password": "pilot-password-123",
        }
        accept_status_1, accept_payload_1 = self._request_json(
            "POST",
            f"/api/v1/beta/invitations/{invitation_token}/accept",
            accept_body,
            extra_headers={"Idempotency-Key": "accept-idempotency-key"},
        )
        self.assertEqual(201, accept_status_1)
        accept_status_2, accept_payload_2 = self._request_json(
            "POST",
            f"/api/v1/beta/invitations/{invitation_token}/accept",
            accept_body,
            extra_headers={"Idempotency-Key": "accept-idempotency-key"},
        )
        self.assertEqual(201, accept_status_2)
        self.assertEqual(accept_payload_1, accept_payload_2)

        pilot_token = accept_payload_1["token"]
        feedback_body = {
            "category": "feature_request",
            "message": "Please auto-save checklist preferences between sessions.",
            "context": {"source": "idempotency-test"},
        }
        feedback_status_1, feedback_payload_1 = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/feedback",
            feedback_body,
            token=pilot_token,
            extra_headers={"Idempotency-Key": "feedback-idempotency-key"},
        )
        self.assertEqual(201, feedback_status_1)

        feedback_status_2, feedback_payload_2 = self._request_json(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/feedback",
            feedback_body,
            token=pilot_token,
            extra_headers={"Idempotency-Key": "feedback-idempotency-key"},
        )
        self.assertEqual(201, feedback_status_2)
        self.assertEqual(feedback_payload_1, feedback_payload_2)

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, object] | None = None,
        token: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, object]]:
        url = f"http://127.0.0.1:{self.port}{path}"
        data = None
        headers = {"Content-Type": "application/json"}

        if body is not None:
            data = json.dumps(body).encode("utf-8")

        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers is not None:
            headers.update(extra_headers)

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

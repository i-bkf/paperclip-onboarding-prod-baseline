from __future__ import annotations

import json
import tempfile
import threading
import unittest
from urllib import error, request

from app.auth import create_access_token, hash_password
from app.config import Settings
from app.db import connect
from app.repository import Repository
from app.server import create_server


class AuthWorkspaceSmokeTests(unittest.TestCase):
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

    def test_signup_workspace_access_and_rbac_guard(self) -> None:
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

        workspace_status, workspace_payload = self._request_json(
            "GET",
            f"/api/v1/workspaces/{workspace_id}",
            token=owner_token,
        )
        self.assertEqual(200, workspace_status)
        self.assertEqual(workspace_id, workspace_payload["workspace"]["id"])

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            member = repo.create_user("member@acme.test", hash_password("member-password-123"))
            repo.add_membership(workspace_id, member.id, "member")
            conn.commit()
        finally:
            conn.close()

        member_token = create_access_token(
            {"sub": member.id, "email": member.email},
            secret=self.settings.auth_secret,
            ttl_seconds=self.settings.token_ttl_seconds,
        )

        members_status_as_member, _ = self._request_json(
            "GET",
            f"/api/v1/workspaces/{workspace_id}/members",
            token=member_token,
        )
        self.assertEqual(403, members_status_as_member)

        members_status_as_owner, members_payload_as_owner = self._request_json(
            "GET",
            f"/api/v1/workspaces/{workspace_id}/members",
            token=owner_token,
        )
        self.assertEqual(200, members_status_as_owner)
        self.assertGreaterEqual(len(members_payload_as_owner["members"]), 2)

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

from __future__ import annotations

import tempfile
import unittest

from app.auth import TokenError, create_access_token, decode_access_token, hash_password, verify_password
from app.db import connect, migrate
from app.domain import WorkspaceMembership
from app.guards import AuthorizationError, require_workspace_role
from app.repository import Repository
from app.services import signup_user


class AuthWorkspaceUnitTests(unittest.TestCase):
    def test_password_hash_round_trip(self) -> None:
        encoded = hash_password("super-secret-123")
        self.assertTrue(verify_password("super-secret-123", encoded))
        self.assertFalse(verify_password("wrong-pass", encoded))

    def test_token_tampering_is_rejected(self) -> None:
        token = create_access_token(
            {"sub": "user-1"},
            secret="test-secret",
            ttl_seconds=3600,
        )
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

        with self.assertRaises(TokenError):
            decode_access_token(tampered, secret="test-secret")

    def test_signup_creates_owner_membership(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = f"{temp_dir}/app.sqlite3"
            migrate(db_path)
            conn = connect(db_path)
            try:
                result = signup_user(
                    conn,
                    email="owner@example.com",
                    password="secure-pass-123",
                    workspace_name="Acme Workspace",
                    account_name=None,
                )

                repo = Repository(conn)
                membership = repo.get_membership(result.workspace.id, result.user.id)

                self.assertIsNotNone(membership)
                self.assertEqual("owner", membership.role)
                self.assertEqual("acme-workspace", result.workspace.slug)
            finally:
                conn.close()

    def test_role_guard_rejects_insufficient_role(self) -> None:
        membership = WorkspaceMembership(
            id="m-1",
            workspace_id="w-1",
            user_id="u-1",
            role="member",
        )

        with self.assertRaises(AuthorizationError):
            require_workspace_role(membership, minimum_role="admin")


if __name__ == "__main__":
    unittest.main()

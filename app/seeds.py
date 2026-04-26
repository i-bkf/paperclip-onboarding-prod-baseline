from __future__ import annotations

import sqlite3

from .auth import hash_password
from .repository import Repository


def seed_local_dev(conn: sqlite3.Connection) -> None:
    repo = Repository(conn)
    with conn:
        existing_admin = repo.find_user_by_email("owner@local.paperclip")
        if existing_admin is not None:
            return

        account = repo.create_account("Local Demo Account")
        workspace = repo.create_workspace(account.id, "Local Demo Workspace", "local-demo")

        owner = repo.create_user("owner@local.paperclip", hash_password("owner-pass-123"))
        member = repo.create_user("member@local.paperclip", hash_password("member-pass-123"))

        repo.add_membership(workspace.id, owner.id, "owner")
        repo.add_membership(workspace.id, member.id, "member")

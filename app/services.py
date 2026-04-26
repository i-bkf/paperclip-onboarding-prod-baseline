from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from .auth import hash_password
from .domain import Account, User, Workspace, WorkspaceMembership
from .repository import DuplicateEmailError, Repository, slugify
from .telemetry import TELEMETRY_EVENT_SIGNUP_COMPLETED


@dataclass(frozen=True)
class SignupResult:
    account: Account
    user: User
    workspace: Workspace
    membership: WorkspaceMembership


def signup_user(
    conn: sqlite3.Connection,
    *,
    email: str,
    password: str,
    workspace_name: str,
    account_name: str | None,
) -> SignupResult:
    if not email or "@" not in email:
        raise ValueError("email must be a valid address")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if not workspace_name.strip():
        raise ValueError("workspace name is required")

    repo = Repository(conn)
    display_account_name = account_name.strip() if account_name else workspace_name.strip()

    try:
        with conn:
            account = repo.create_account(display_account_name)
            user = repo.create_user(email.strip(), hash_password(password))
            workspace = repo.create_workspace(
                account.id,
                workspace_name.strip(),
                slugify(workspace_name),
            )
            membership = repo.add_membership(workspace.id, user.id, "owner")
            repo.record_product_event(
                event_name=TELEMETRY_EVENT_SIGNUP_COMPLETED,
                source="backend",
                actor_user_id=user.id,
                workspace_id=workspace.id,
                properties={"accountId": account.id},
                dedupe_key=f"{TELEMETRY_EVENT_SIGNUP_COMPLETED}:{workspace.id}",
            )
    except DuplicateEmailError as exc:
        raise ValueError("email already exists") from exc

    return SignupResult(
        account=account,
        user=user,
        workspace=workspace,
        membership=membership,
    )

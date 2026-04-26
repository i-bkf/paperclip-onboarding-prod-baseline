from __future__ import annotations

from datetime import date, timedelta
import json
import re
import sqlite3
from uuid import uuid4

from .domain import Account, User, Workspace, WorkspaceMembership


class DuplicateEmailError(ValueError):
    pass


class DuplicateTelemetryEventError(ValueError):
    pass


class DuplicateMembershipError(ValueError):
    pass


class DuplicatePendingInvitationError(ValueError):
    pass


class DuplicateIdempotencyKeyError(ValueError):
    pass


class Repository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_account(self, name: str) -> Account:
        account = Account(id=str(uuid4()), name=name)
        self.conn.execute(
            "INSERT INTO accounts (id, name) VALUES (?, ?)",
            (account.id, account.name),
        )
        return account

    def create_user(self, email: str, password_hash: str) -> User:
        user = User(id=str(uuid4()), email=email.lower(), password_hash=password_hash)
        try:
            self.conn.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user.id, user.email, user.password_hash),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateEmailError(email) from exc
        return user

    def create_workspace(self, account_id: str, name: str, slug: str) -> Workspace:
        workspace = Workspace(id=str(uuid4()), account_id=account_id, name=name, slug=slug)
        self.conn.execute(
            "INSERT INTO workspaces (id, account_id, name, slug) VALUES (?, ?, ?, ?)",
            (workspace.id, workspace.account_id, workspace.name, workspace.slug),
        )
        return workspace

    def add_membership(self, workspace_id: str, user_id: str, role: str) -> WorkspaceMembership:
        membership = WorkspaceMembership(
            id=str(uuid4()), workspace_id=workspace_id, user_id=user_id, role=role
        )
        try:
            self.conn.execute(
                """
                INSERT INTO workspace_memberships (id, workspace_id, user_id, role)
                VALUES (?, ?, ?, ?)
                """,
                (membership.id, membership.workspace_id, membership.user_id, membership.role),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateMembershipError(
                f"membership already exists for workspace={workspace_id} user={user_id}"
            ) from exc
        return membership

    def find_user_by_email(self, email: str) -> User | None:
        row = self.conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
        )

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        row = self.conn.execute(
            "SELECT id, account_id, name, slug FROM workspaces WHERE id = ?",
            (workspace_id,),
        ).fetchone()
        if row is None:
            return None
        return Workspace(
            id=row["id"],
            account_id=row["account_id"],
            name=row["name"],
            slug=row["slug"],
        )

    def get_workspace_with_membership(
        self, workspace_id: str, user_id: str
    ) -> tuple[Workspace, WorkspaceMembership | None] | None:
        row = self.conn.execute(
            """
            SELECT w.id AS workspace_id,
                   w.account_id AS workspace_account_id,
                   w.name AS workspace_name,
                   w.slug AS workspace_slug,
                   m.id AS membership_id,
                   m.workspace_id AS membership_workspace_id,
                   m.user_id AS membership_user_id,
                   m.role AS membership_role
            FROM workspaces w
            LEFT JOIN workspace_memberships m
              ON m.workspace_id = w.id
             AND m.user_id = ?
            WHERE w.id = ?
            """,
            (user_id, workspace_id),
        ).fetchone()
        if row is None:
            return None

        workspace = Workspace(
            id=row["workspace_id"],
            account_id=row["workspace_account_id"],
            name=row["workspace_name"],
            slug=row["workspace_slug"],
        )
        membership: WorkspaceMembership | None = None
        if row["membership_id"] is not None:
            membership = WorkspaceMembership(
                id=row["membership_id"],
                workspace_id=row["membership_workspace_id"],
                user_id=row["membership_user_id"],
                role=row["membership_role"],
            )
        return workspace, membership

    def get_membership(self, workspace_id: str, user_id: str) -> WorkspaceMembership | None:
        row = self.conn.execute(
            """
            SELECT id, workspace_id, user_id, role
            FROM workspace_memberships
            WHERE workspace_id = ? AND user_id = ?
            """,
            (workspace_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return WorkspaceMembership(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            role=row["role"],
        )

    def list_workspace_members(self, workspace_id: str) -> list[dict[str, str]]:
        rows = self.conn.execute(
            """
            SELECT m.user_id, u.email, m.role
            FROM workspace_memberships m
            JOIN users u ON u.id = m.user_id
            WHERE m.workspace_id = ?
            ORDER BY u.email ASC
            """,
            (workspace_id,),
        ).fetchall()
        return [
            {"userId": row["user_id"], "email": row["email"], "role": row["role"]}
            for row in rows
        ]

    def create_beta_invitation(
        self,
        *,
        workspace_id: str,
        invited_email: str,
        invited_by_user_id: str,
        role: str,
        cohort: str,
    ) -> dict[str, object]:
        invitation_id = str(uuid4())
        invitation_token = str(uuid4())
        normalized_email = invited_email.lower()
        try:
            self.conn.execute(
                """
                INSERT INTO beta_invitations (
                    id,
                    workspace_id,
                    invited_email,
                    invited_by_user_id,
                    role,
                    cohort,
                    invitation_token,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    invitation_id,
                    workspace_id,
                    normalized_email,
                    invited_by_user_id,
                    role,
                    cohort,
                    invitation_token,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicatePendingInvitationError(
                f"pending invitation already exists for {normalized_email}"
            ) from exc

        created = self.get_beta_invitation(workspace_id, invitation_id)
        if created is None:
            raise ValueError("invitation creation failed")
        return created

    def get_beta_invitation(
        self, workspace_id: str, invitation_id: str
    ) -> dict[str, object] | None:
        row = self.conn.execute(
            """
            SELECT id,
                   workspace_id,
                   invited_email,
                   invited_by_user_id,
                   role,
                   cohort,
                   invitation_token,
                   status,
                   accepted_user_id,
                   accepted_at,
                   revoked_by_user_id,
                   revoked_at,
                   created_at
            FROM beta_invitations
            WHERE workspace_id = ? AND id = ?
            """,
            (workspace_id, invitation_id),
        ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)

    def get_beta_invitation_by_token(self, invitation_token: str) -> dict[str, object] | None:
        row = self.conn.execute(
            """
            SELECT id,
                   workspace_id,
                   invited_email,
                   invited_by_user_id,
                   role,
                   cohort,
                   invitation_token,
                   status,
                   accepted_user_id,
                   accepted_at,
                   revoked_by_user_id,
                   revoked_at,
                   created_at
            FROM beta_invitations
            WHERE invitation_token = ?
            """,
            (invitation_token,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)

    def revoke_beta_invitation(
        self,
        *,
        workspace_id: str,
        invitation_id: str,
        revoked_by_user_id: str,
    ) -> dict[str, object]:
        invitation = self.get_beta_invitation(workspace_id, invitation_id)
        if invitation is None:
            raise ValueError("invitation not found")
        if invitation["status"] != "pending":
            raise ValueError("only pending invitations can be revoked")

        self.conn.execute(
            """
            UPDATE beta_invitations
            SET status = 'revoked',
                revoked_by_user_id = ?,
                revoked_at = (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            WHERE workspace_id = ? AND id = ?
            """,
            (revoked_by_user_id, workspace_id, invitation_id),
        )
        revoked = self.get_beta_invitation(workspace_id, invitation_id)
        if revoked is None:
            raise ValueError("invitation update failed")
        return revoked

    def accept_beta_invitation(
        self,
        *,
        invitation_id: str,
        accepted_user_id: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE beta_invitations
            SET status = 'accepted',
                accepted_user_id = ?,
                accepted_at = (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            WHERE id = ?
            """,
            (accepted_user_id, invitation_id),
        )

    def upsert_beta_cohort_membership(
        self,
        *,
        workspace_id: str,
        user_id: str,
        cohort: str,
        source_invitation_id: str | None,
    ) -> None:
        existing = self.conn.execute(
            """
            SELECT id
            FROM beta_cohort_memberships
            WHERE workspace_id = ? AND user_id = ?
            """,
            (workspace_id, user_id),
        ).fetchone()
        if existing is None:
            self.conn.execute(
                """
                INSERT INTO beta_cohort_memberships (
                    id,
                    workspace_id,
                    user_id,
                    cohort,
                    source_invitation_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid4()), workspace_id, user_id, cohort, source_invitation_id),
            )
            return

        self.conn.execute(
            """
            UPDATE beta_cohort_memberships
            SET cohort = ?, source_invitation_id = ?
            WHERE workspace_id = ? AND user_id = ?
            """,
            (cohort, source_invitation_id, workspace_id, user_id),
        )

    def get_user_cohort(self, workspace_id: str, user_id: str) -> str | None:
        row = self.conn.execute(
            """
            SELECT cohort
            FROM beta_cohort_memberships
            WHERE workspace_id = ? AND user_id = ?
            """,
            (workspace_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return str(row["cohort"])

    def record_onboarding_step_completion(
        self,
        *,
        workspace_id: str,
        user_id: str,
        cohort: str,
        step_key: str,
    ) -> bool:
        try:
            self.conn.execute(
                """
                INSERT INTO onboarding_checklist_progress (
                    id,
                    workspace_id,
                    user_id,
                    cohort,
                    step_key
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid4()), workspace_id, user_id, cohort, step_key),
            )
        except sqlite3.IntegrityError:
            return False
        return True

    def list_user_completed_onboarding_steps(
        self,
        *,
        workspace_id: str,
        user_id: str,
    ) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT step_key
            FROM onboarding_checklist_progress
            WHERE workspace_id = ? AND user_id = ?
            ORDER BY completed_at ASC
            """,
            (workspace_id, user_id),
        ).fetchall()
        return [str(row["step_key"]) for row in rows]

    def list_onboarding_completion_by_cohort(
        self,
        *,
        workspace_id: str,
        checklist_steps: tuple[str, ...],
    ) -> list[dict[str, object]]:
        rows = self.conn.execute(
            """
            SELECT cohort,
                   step_key,
                   COUNT(DISTINCT user_id) AS completed_count
            FROM onboarding_checklist_progress
            WHERE workspace_id = ?
            GROUP BY cohort, step_key
            ORDER BY cohort ASC, step_key ASC
            """,
            (workspace_id,),
        ).fetchall()
        completions: dict[str, dict[str, int]] = {}
        for row in rows:
            cohort = str(row["cohort"])
            step_key = str(row["step_key"])
            count = int(row["completed_count"])
            completions.setdefault(cohort, {})[step_key] = count

        member_rows = self.conn.execute(
            """
            SELECT cohort, COUNT(DISTINCT user_id) AS members_count
            FROM beta_cohort_memberships
            WHERE workspace_id = ?
            GROUP BY cohort
            ORDER BY cohort ASC
            """,
            (workspace_id,),
        ).fetchall()
        members_by_cohort = {str(row["cohort"]): int(row["members_count"]) for row in member_rows}
        required_steps = len(checklist_steps)
        fully_completed_rows = self.conn.execute(
            """
            SELECT cohort,
                   COUNT(*) AS fully_completed_count
            FROM (
                SELECT cohort,
                       user_id,
                       COUNT(DISTINCT step_key) AS completed_steps
                FROM onboarding_checklist_progress
                WHERE workspace_id = ?
                GROUP BY cohort, user_id
                HAVING COUNT(DISTINCT step_key) >= ?
            ) completed_users
            GROUP BY cohort
            """,
            (workspace_id, required_steps),
        ).fetchall()
        fully_completed_by_cohort = {
            str(row["cohort"]): int(row["fully_completed_count"]) for row in fully_completed_rows
        }

        all_cohorts = sorted(set(completions.keys()) | set(members_by_cohort.keys()))
        result: list[dict[str, object]] = []
        for cohort in all_cohorts:
            step_counts = completions.get(cohort, {})
            steps = [
                {
                    "stepKey": step_key,
                    "completedUsers": step_counts.get(step_key, 0),
                }
                for step_key in checklist_steps
            ]
            result.append(
                {
                    "cohort": cohort,
                    "membersCount": members_by_cohort.get(cohort, 0),
                    "fullyCompletedUsers": fully_completed_by_cohort.get(cohort, 0),
                    "steps": steps,
                }
            )
        return result

    def create_feedback_submission(
        self,
        *,
        workspace_id: str,
        submitted_by_user_id: str,
        cohort: str,
        category: str,
        message: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        feedback_id = str(uuid4())
        self.conn.execute(
            """
            INSERT INTO feedback_submissions (
                id,
                workspace_id,
                submitted_by_user_id,
                cohort,
                category,
                message,
                context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                workspace_id,
                submitted_by_user_id,
                cohort,
                category,
                message,
                json.dumps(context, separators=(",", ":"), sort_keys=True),
            ),
        )
        created = self.conn.execute(
            """
            SELECT id,
                   workspace_id,
                   submitted_by_user_id,
                   cohort,
                   category,
                   message,
                   context_json,
                   created_at
            FROM feedback_submissions
            WHERE id = ?
            """,
            (feedback_id,),
        ).fetchone()
        if created is None:
            raise ValueError("feedback creation failed")
        payload = _row_to_dict(created)
        payload["context"] = json.loads(str(payload.pop("context_json")))
        return payload

    def create_triage_ticket_for_feedback(
        self,
        *,
        workspace_id: str,
        feedback_submission_id: str,
        title: str,
    ) -> dict[str, object]:
        triage_id = str(uuid4())
        self.conn.execute(
            """
            INSERT INTO triage_tickets (
                id,
                workspace_id,
                feedback_submission_id,
                title,
                status
            ) VALUES (?, ?, ?, ?, 'open')
            """,
            (triage_id, workspace_id, feedback_submission_id, title),
        )
        created = self.conn.execute(
            """
            SELECT id,
                   workspace_id,
                   feedback_submission_id,
                   title,
                   status,
                   created_at
            FROM triage_tickets
            WHERE id = ?
            """,
            (triage_id,),
        ).fetchone()
        if created is None:
            raise ValueError("triage ticket creation failed")
        return _row_to_dict(created)

    def record_product_event(
        self,
        *,
        event_name: str,
        source: str,
        actor_user_id: str | None,
        workspace_id: str | None,
        properties: dict[str, object] | None = None,
        dedupe_key: str | None = None,
        ignore_duplicates: bool = False,
    ) -> bool:
        try:
            self.conn.execute(
                """
                INSERT INTO product_events (
                    id,
                    event_name,
                    source,
                    actor_user_id,
                    workspace_id,
                    properties_json,
                    dedupe_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    event_name,
                    source,
                    actor_user_id,
                    workspace_id,
                    json.dumps(properties or {}, separators=(",", ":"), sort_keys=True),
                    dedupe_key,
                ),
            )
        except sqlite3.IntegrityError as exc:
            is_dedupe_conflict = "product_events.dedupe_key" in str(exc)
            if ignore_duplicates and dedupe_key and is_dedupe_conflict:
                return False
            raise DuplicateTelemetryEventError(event_name) from exc
        return True

    def get_idempotency_record(self, *, scope: str, idempotency_key: str) -> dict[str, object] | None:
        row = self.conn.execute(
            """
            SELECT scope,
                   idempotency_key,
                   request_hash,
                   response_status,
                   response_body_json
            FROM idempotency_records
            WHERE scope = ? AND idempotency_key = ?
            """,
            (scope, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)

    def create_idempotency_record(
        self,
        *,
        scope: str,
        idempotency_key: str,
        request_hash: str,
        response_status: int,
        response_body: dict[str, object],
    ) -> None:
        try:
            self.conn.execute(
                """
                INSERT INTO idempotency_records (
                    id,
                    scope,
                    idempotency_key,
                    request_hash,
                    response_status,
                    response_body_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    scope,
                    idempotency_key,
                    request_hash,
                    response_status,
                    json.dumps(response_body, separators=(",", ":"), sort_keys=True),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateIdempotencyKeyError(idempotency_key) from exc

    def list_workspace_funnel_daily(
        self,
        *,
        workspace_id: str,
        start_date: date,
        end_date: date,
        funnel_events: tuple[str, ...],
    ) -> list[dict[str, object]]:
        if start_date > end_date:
            raise ValueError("from must be on or before to")
        if not funnel_events:
            return []

        placeholders = ",".join("?" for _ in funnel_events)
        query_params: list[object] = [
            workspace_id,
            *funnel_events,
            start_date.isoformat(),
            (end_date + timedelta(days=1)).isoformat(),
        ]
        rows = self.conn.execute(
            f"""
            SELECT substr(emitted_at, 1, 10) AS event_date,
                   event_name,
                   (
                       COUNT(DISTINCT actor_user_id)
                       + SUM(CASE WHEN actor_user_id IS NULL THEN 1 ELSE 0 END)
                   ) AS total
            FROM product_events
            WHERE workspace_id = ?
              AND event_name IN ({placeholders})
              AND emitted_at >= ?
              AND emitted_at < ?
            GROUP BY event_date, event_name
            ORDER BY event_date ASC
            """,
            query_params,
        ).fetchall()

        totals: dict[str, dict[str, int]] = {}
        for row in rows:
            event_date = row["event_date"]
            event_name = row["event_name"]
            count = int(row["total"])
            totals.setdefault(event_date, {})[event_name] = count

        result: list[dict[str, object]] = []
        current_day = start_date
        signup_event = funnel_events[0]
        while current_day <= end_date:
            day_key = current_day.isoformat()
            day_totals = totals.get(day_key, {})
            signup_count = day_totals.get(signup_event, 0)
            steps: list[dict[str, object]] = []
            for event_name in funnel_events:
                count = day_totals.get(event_name, 0)
                conversion = (
                    round((count / signup_count) * 100, 2)
                    if signup_count > 0
                    else 0.0
                )
                steps.append(
                    {
                        "eventName": event_name,
                        "count": count,
                        "conversionFromSignupPct": conversion,
                    }
                )
            result.append({"date": day_key, "steps": steps})
            current_day = current_day + timedelta(days=1)

        return result


def slugify(value: str) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return candidate or "workspace"


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}

from __future__ import annotations

from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import re
import sqlite3
from typing import Any
from urllib.parse import parse_qs, urlparse

from .auth import TokenError, create_access_token, decode_access_token, hash_password
from .config import Settings
from .db import connect, migrate
from .guards import AuthorizationError, require_workspace_role
from .repository import (
    DuplicateEmailError,
    DuplicateIdempotencyKeyError,
    DuplicateMembershipError,
    DuplicatePendingInvitationError,
    Repository,
)
from .services import signup_user
from .telemetry import (
    CLIENT_EVENT_NAMES,
    FEEDBACK_CATEGORIES,
    FUNNEL_EVENT_SEQUENCE,
    ONBOARDING_CHECKLIST_STEPS,
    TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
)

WORKSPACE_ROUTE = re.compile(r"^/api/v1/workspaces/([^/]+)$")
WORKSPACE_MEMBERS_ROUTE = re.compile(r"^/api/v1/workspaces/([^/]+)/members$")
WORKSPACE_TELEMETRY_EVENTS_ROUTE = re.compile(r"^/api/v1/workspaces/([^/]+)/telemetry/events$")
WORKSPACE_TELEMETRY_DASHBOARD_ROUTE = re.compile(
    r"^/api/v1/workspaces/([^/]+)/telemetry/funnel/daily$"
)
WORKSPACE_BETA_INVITATIONS_ROUTE = re.compile(
    r"^/api/v1/workspaces/([^/]+)/beta/invitations$"
)
WORKSPACE_BETA_INVITATION_REVOKE_ROUTE = re.compile(
    r"^/api/v1/workspaces/([^/]+)/beta/invitations/([^/]+)/revoke$"
)
BETA_INVITATION_ACCEPT_ROUTE = re.compile(r"^/api/v1/beta/invitations/([^/]+)/accept$")
WORKSPACE_ONBOARDING_CHECKLIST_COMPLETE_ROUTE = re.compile(
    r"^/api/v1/workspaces/([^/]+)/onboarding/checklist/complete$"
)
WORKSPACE_ONBOARDING_COHORT_PROGRESS_ROUTE = re.compile(
    r"^/api/v1/workspaces/([^/]+)/onboarding/checklist/cohorts$"
)
WORKSPACE_FEEDBACK_ROUTE = re.compile(r"^/api/v1/workspaces/([^/]+)/feedback$")


class AuthenticationError(PermissionError):
    pass


class App:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        migrate(settings.db_path)

    def _idempotency_key_from_headers(self, headers: Any) -> str | None:
        raw = headers.get("Idempotency-Key")
        if raw is None:
            return None
        key = str(raw).strip()
        if not key:
            raise ValueError("Idempotency-Key header must not be empty")
        if len(key) > 128:
            raise ValueError("Idempotency-Key header must be at most 128 characters")
        return key

    def _idempotency_request_hash(self, payload: dict[str, Any]) -> str:
        encoded_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(encoded_payload.encode("utf-8")).hexdigest()

    def _load_idempotent_response(
        self,
        *,
        repo: Repository,
        scope: str,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[int, dict[str, Any]] | None:
        existing = repo.get_idempotency_record(scope=scope, idempotency_key=idempotency_key)
        if existing is None:
            return None
        existing_hash = str(existing["request_hash"])
        if existing_hash != request_hash:
            raise ValueError("Idempotency-Key cannot be reused with a different request payload")
        try:
            response_body = json.loads(str(existing["response_body_json"]))
        except json.JSONDecodeError as exc:
            raise ValueError("stored idempotency response is invalid") from exc
        if not isinstance(response_body, dict):
            raise ValueError("stored idempotency response is invalid")
        return int(existing["response_status"]), response_body

    def _persist_idempotent_response(
        self,
        *,
        repo: Repository,
        scope: str,
        idempotency_key: str,
        request_hash: str,
        response: tuple[int, dict[str, Any]],
    ) -> tuple[int, dict[str, Any]]:
        status, payload = response
        try:
            repo.create_idempotency_record(
                scope=scope,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_status=status,
                response_body=payload,
            )
            return response
        except DuplicateIdempotencyKeyError:
            replay = self._load_idempotent_response(
                repo=repo,
                scope=scope,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if replay is None:
                raise ValueError("idempotency record already exists")
            return replay

    def dispatch(
        self,
        *,
        method: str,
        raw_path: str,
        headers: Any,
        rfile: Any,
    ) -> tuple[int, dict[str, Any]]:
        parsed_url = urlparse(raw_path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}

        if method == "POST" and path == "/api/v1/signup":
            payload = _read_json_body(headers, rfile)
            return self._signup(payload)

        beta_invite_accept_match = BETA_INVITATION_ACCEPT_ROUTE.match(path)
        if method == "POST" and beta_invite_accept_match:
            payload = _read_json_body(headers, rfile)
            return self._accept_beta_invitation(
                beta_invite_accept_match.group(1),
                headers,
                payload,
            )

        workspace_match = WORKSPACE_ROUTE.match(path)
        if method == "GET" and workspace_match:
            return self._workspace_details(workspace_match.group(1), headers)

        members_match = WORKSPACE_MEMBERS_ROUTE.match(path)
        if method == "GET" and members_match:
            return self._workspace_members(members_match.group(1), headers)

        telemetry_events_match = WORKSPACE_TELEMETRY_EVENTS_ROUTE.match(path)
        if method == "POST" and telemetry_events_match:
            payload = _read_json_body(headers, rfile)
            return self._workspace_telemetry_event(
                telemetry_events_match.group(1),
                headers,
                payload,
            )

        telemetry_dashboard_match = WORKSPACE_TELEMETRY_DASHBOARD_ROUTE.match(path)
        if method == "GET" and telemetry_dashboard_match:
            return self._workspace_telemetry_funnel_daily(
                telemetry_dashboard_match.group(1),
                headers,
                query,
            )

        beta_invitations_match = WORKSPACE_BETA_INVITATIONS_ROUTE.match(path)
        if method == "POST" and beta_invitations_match:
            payload = _read_json_body(headers, rfile)
            return self._workspace_beta_invite(
                beta_invitations_match.group(1),
                headers,
                payload,
            )

        beta_invitation_revoke_match = WORKSPACE_BETA_INVITATION_REVOKE_ROUTE.match(path)
        if method == "POST" and beta_invitation_revoke_match:
            return self._workspace_beta_revoke_invitation(
                beta_invitation_revoke_match.group(1),
                beta_invitation_revoke_match.group(2),
                headers,
            )

        checklist_complete_match = WORKSPACE_ONBOARDING_CHECKLIST_COMPLETE_ROUTE.match(path)
        if method == "POST" and checklist_complete_match:
            payload = _read_json_body(headers, rfile)
            return self._workspace_complete_onboarding_step(
                checklist_complete_match.group(1),
                headers,
                payload,
            )

        checklist_cohort_progress_match = WORKSPACE_ONBOARDING_COHORT_PROGRESS_ROUTE.match(path)
        if method == "GET" and checklist_cohort_progress_match:
            return self._workspace_onboarding_progress_by_cohort(
                checklist_cohort_progress_match.group(1),
                headers,
            )

        workspace_feedback_match = WORKSPACE_FEEDBACK_ROUTE.match(path)
        if method == "POST" and workspace_feedback_match:
            payload = _read_json_body(headers, rfile)
            return self._workspace_feedback_submit(
                workspace_feedback_match.group(1),
                headers,
                payload,
            )

        return 404, {"error": "not_found", "message": f"Route {method} {path} was not found"}

    def _signup(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        email = str(payload.get("email", "")).strip()
        password = str(payload.get("password", ""))
        workspace_name = str(payload.get("workspaceName", "")).strip()
        account_name = payload.get("accountName")
        account_name_text = str(account_name).strip() if account_name is not None else None

        conn = connect(self.settings.db_path)
        try:
            result = signup_user(
                conn,
                email=email,
                password=password,
                workspace_name=workspace_name,
                account_name=account_name_text,
            )
        finally:
            conn.close()

        token = create_access_token(
            {
                "sub": result.user.id,
                "email": result.user.email,
            },
            secret=self.settings.auth_secret,
            ttl_seconds=self.settings.token_ttl_seconds,
        )

        return 201, {
            "token": token,
            "user": {"id": result.user.id, "email": result.user.email},
            "workspace": {
                "id": result.workspace.id,
                "name": result.workspace.name,
                "slug": result.workspace.slug,
            },
            "membership": {
                "role": result.membership.role,
                "workspaceId": result.membership.workspace_id,
            },
        }

    def _accept_beta_invitation(
        self,
        invitation_token: str,
        headers: Any,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        if not email or "@" not in email:
            raise ValueError("email must be a valid address")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        idempotency_key = self._idempotency_key_from_headers(headers)
        request_hash = self._idempotency_request_hash(
            {
                "invitationToken": invitation_token,
                "email": email,
            }
        )
        idempotency_scope = f"beta_invitation_accept:{invitation_token}"

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            if idempotency_key is not None:
                replay = self._load_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return replay

            invitation = repo.get_beta_invitation_by_token(invitation_token)
            if invitation is None:
                return 404, {"error": "not_found", "message": "invitation not found"}
            if str(invitation["invited_email"]).lower() != email:
                raise ValueError("invitation email does not match request email")

            workspace_id = str(invitation["workspace_id"])
            workspace = repo.get_workspace(workspace_id)
            if workspace is None:
                return 404, {"error": "not_found", "message": "workspace not found"}

            status_value = str(invitation["status"])
            if status_value not in {"pending", "accepted"}:
                raise ValueError("invitation is no longer active")

            with conn:
                user = repo.find_user_by_email(email)
                if user is None:
                    user = repo.create_user(email, hash_password(password))

                membership = repo.get_membership(workspace_id, user.id)
                created_membership = False
                if membership is None:
                    membership = repo.add_membership(
                        workspace_id,
                        user.id,
                        str(invitation["role"]),
                    )
                    created_membership = True

                accepted_user_id = invitation.get("accepted_user_id")
                if status_value == "accepted":
                    if accepted_user_id and str(accepted_user_id) != user.id:
                        raise ValueError("invitation was accepted by a different user")
                else:
                    repo.accept_beta_invitation(
                        invitation_id=str(invitation["id"]),
                        accepted_user_id=user.id,
                    )

                repo.upsert_beta_cohort_membership(
                    workspace_id=workspace_id,
                    user_id=user.id,
                    cohort=str(invitation["cohort"]),
                    source_invitation_id=str(invitation["id"]),
                )
                response_status = 201 if created_membership else 200
                response = _build_beta_accept_response(
                    response_status=response_status,
                    token=create_access_token(
                        {
                            "sub": user.id,
                            "email": user.email,
                        },
                        secret=self.settings.auth_secret,
                        ttl_seconds=self.settings.token_ttl_seconds,
                    ),
                    user_id=user.id,
                    user_email=user.email,
                    workspace_id=workspace.id,
                    workspace_name=workspace.name,
                    workspace_slug=workspace.slug,
                    membership_role=membership.role,
                    cohort=str(invitation["cohort"]),
                    invitation_id=str(invitation["id"]),
                )
                if idempotency_key is not None:
                    response = self._persist_idempotent_response(
                        repo=repo,
                        scope=idempotency_scope,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                        response=response,
                    )
        except DuplicateEmailError as exc:
            raise ValueError("email already exists") from exc
        except DuplicateMembershipError as exc:
            raise ValueError(str(exc)) from exc
        finally:
            conn.close()

        return response

    def _workspace_beta_invite(
        self,
        workspace_id: str,
        headers: Any,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)
        invited_email = str(payload.get("email", "")).strip().lower()
        role = str(payload.get("role", "member")).strip().lower()
        cohort = str(payload.get("cohort", "")).strip()

        if not invited_email or "@" not in invited_email:
            raise ValueError("email must be a valid address")
        if role not in {"member", "admin"}:
            raise ValueError("role must be one of: member, admin")
        if not cohort:
            raise ValueError("cohort is required")
        idempotency_key = self._idempotency_key_from_headers(headers)
        request_hash = self._idempotency_request_hash(
            {
                "workspaceId": workspace_id,
                "email": invited_email,
                "role": role,
                "cohort": cohort,
            }
        )

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="admin")

            idempotency_scope = f"workspace_beta_invite:{workspace_id}:{user_id}"
            if idempotency_key is not None:
                replay = self._load_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return replay

            invitation = repo.create_beta_invitation(
                workspace_id=workspace_id,
                invited_email=invited_email,
                invited_by_user_id=user_id,
                role=role,
                cohort=cohort,
            )
            response = (201, {"invitation": invitation})
            if idempotency_key is not None:
                response = self._persist_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response=response,
                )
            conn.commit()
            return response
        except DuplicatePendingInvitationError as exc:
            raise ValueError(str(exc)) from exc
        finally:
            conn.close()

    def _workspace_beta_revoke_invitation(
        self,
        workspace_id: str,
        invitation_id: str,
        headers: Any,
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)
        idempotency_key = self._idempotency_key_from_headers(headers)
        request_hash = self._idempotency_request_hash(
            {
                "workspaceId": workspace_id,
                "invitationId": invitation_id,
            }
        )
        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="admin")
            idempotency_scope = f"workspace_beta_revoke:{workspace_id}:{user_id}"
            if idempotency_key is not None:
                replay = self._load_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return replay

            invitation = repo.revoke_beta_invitation(
                workspace_id=workspace_id,
                invitation_id=invitation_id,
                revoked_by_user_id=user_id,
            )
            response = (200, {"invitation": invitation})
            if idempotency_key is not None:
                response = self._persist_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response=response,
                )
            conn.commit()
            return response
        finally:
            conn.close()

    def _workspace_complete_onboarding_step(
        self,
        workspace_id: str,
        headers: Any,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)
        step_key = str(payload.get("stepKey", "")).strip()
        if step_key not in ONBOARDING_CHECKLIST_STEPS:
            raise ValueError("stepKey is not allowed")
        idempotency_key = self._idempotency_key_from_headers(headers)
        request_hash = self._idempotency_request_hash(
            {
                "workspaceId": workspace_id,
                "stepKey": step_key,
            }
        )

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="member")

            idempotency_scope = f"onboarding_step_complete:{workspace_id}:{user_id}"
            if idempotency_key is not None:
                replay = self._load_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return replay

            cohort = repo.get_user_cohort(workspace_id, user_id) or "unassigned"
            inserted = repo.record_onboarding_step_completion(
                workspace_id=workspace_id,
                user_id=user_id,
                cohort=cohort,
                step_key=step_key,
            )
            completed_steps = repo.list_user_completed_onboarding_steps(
                workspace_id=workspace_id,
                user_id=user_id,
            )
            completion_pct = round(
                (len(completed_steps) / len(ONBOARDING_CHECKLIST_STEPS)) * 100, 2
            )
            response = (
                202,
                {
                    "accepted": inserted,
                    "cohort": cohort,
                    "stepKey": step_key,
                    "completedSteps": completed_steps,
                    "completionPct": completion_pct,
                    "totalSteps": len(ONBOARDING_CHECKLIST_STEPS),
                },
            )
            if idempotency_key is not None:
                response = self._persist_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response=response,
                )
            conn.commit()
            return response
        finally:
            conn.close()

    def _workspace_onboarding_progress_by_cohort(
        self,
        workspace_id: str,
        headers: Any,
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)
        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="admin")

            cohorts = repo.list_onboarding_completion_by_cohort(
                workspace_id=workspace_id,
                checklist_steps=ONBOARDING_CHECKLIST_STEPS,
            )
            return 200, {
                "workspaceId": workspace_id,
                "steps": ONBOARDING_CHECKLIST_STEPS,
                "cohorts": cohorts,
            }
        finally:
            conn.close()

    def _workspace_feedback_submit(
        self,
        workspace_id: str,
        headers: Any,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)
        message = str(payload.get("message", "")).strip()
        category = str(payload.get("category", "general")).strip().lower()
        context_value = payload.get("context")

        if not message:
            raise ValueError("message is required")
        if category not in FEEDBACK_CATEGORIES:
            raise ValueError("category is not allowed")
        if context_value is None:
            context: dict[str, object] = {}
        elif isinstance(context_value, dict):
            context = context_value
        else:
            raise ValueError("context must be an object when provided")
        idempotency_key = self._idempotency_key_from_headers(headers)
        request_hash = self._idempotency_request_hash(
            {
                "workspaceId": workspace_id,
                "category": category,
                "message": message,
                "context": context,
            }
        )

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="member")

            idempotency_scope = f"feedback_submit:{workspace_id}:{user_id}"
            if idempotency_key is not None:
                replay = self._load_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return replay

            cohort = repo.get_user_cohort(workspace_id, user_id) or "unassigned"
            feedback = repo.create_feedback_submission(
                workspace_id=workspace_id,
                submitted_by_user_id=user_id,
                cohort=cohort,
                category=category,
                message=message,
                context=context,
            )
            triage_ticket = repo.create_triage_ticket_for_feedback(
                workspace_id=workspace_id,
                feedback_submission_id=str(feedback["id"]),
                title=_build_feedback_triage_title(category=category, message=message),
            )
            checklist_step_recorded = repo.record_onboarding_step_completion(
                workspace_id=workspace_id,
                user_id=user_id,
                cohort=cohort,
                step_key="first_feedback_shared",
            )
            response = (
                201,
                {
                    "feedback": feedback,
                    "triageTicket": triage_ticket,
                    "onboardingStepAccepted": checklist_step_recorded,
                },
            )
            if idempotency_key is not None:
                response = self._persist_idempotent_response(
                    repo=repo,
                    scope=idempotency_scope,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response=response,
                )
            conn.commit()
            return response
        finally:
            conn.close()

    def _workspace_details(
        self,
        workspace_id: str,
        headers: Any,
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            workspace, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="member")
            repo.record_product_event(
                event_name=TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED,
                source="backend",
                actor_user_id=user_id,
                workspace_id=workspace_id,
                properties={"route": "GET /api/v1/workspaces/{workspaceId}"},
                dedupe_key=(
                    f"{TELEMETRY_EVENT_WORKSPACE_FIRST_ACCESSED}:"
                    f"{workspace_id}:{user_id}"
                ),
                ignore_duplicates=True,
            )
            conn.commit()

            return 200, {
                "workspace": {
                    "id": workspace.id,
                    "accountId": workspace.account_id,
                    "name": workspace.name,
                    "slug": workspace.slug,
                },
                "role": membership.role,
            }
        finally:
            conn.close()

    def _workspace_members(
        self,
        workspace_id: str,
        headers: Any,
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="admin")

            return 200, {
                "workspaceId": workspace_id,
                "members": repo.list_workspace_members(workspace_id),
            }
        finally:
            conn.close()

    def _workspace_telemetry_event(
        self,
        workspace_id: str,
        headers: Any,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)
        event_name = str(payload.get("eventName", "")).strip()
        if event_name not in CLIENT_EVENT_NAMES:
            raise ValueError("eventName is not allowed")

        properties = payload.get("properties")
        if properties is None:
            properties_map: dict[str, Any] = {}
        elif isinstance(properties, dict):
            properties_map = properties
        else:
            raise ValueError("properties must be an object when provided")

        dedupe_value = payload.get("dedupeKey")
        dedupe_key = str(dedupe_value).strip() if dedupe_value is not None else None
        if dedupe_key == "":
            dedupe_key = None

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="member")

            inserted = repo.record_product_event(
                event_name=event_name,
                source="frontend",
                actor_user_id=user_id,
                workspace_id=workspace_id,
                properties=properties_map,
                dedupe_key=dedupe_key,
                ignore_duplicates=True,
            )
            conn.commit()
            return 202, {"accepted": inserted, "eventName": event_name}
        finally:
            conn.close()

    def _workspace_telemetry_funnel_daily(
        self,
        workspace_id: str,
        headers: Any,
        query: dict[str, list[str]],
    ) -> tuple[int, dict[str, Any]]:
        user_id = self._authenticate(headers)
        range_from, range_to = _resolve_funnel_date_range(query)

        conn = connect(self.settings.db_path)
        try:
            repo = Repository(conn)
            workspace_bundle = repo.get_workspace_with_membership(workspace_id, user_id)
            if workspace_bundle is None:
                return 404, {"error": "not_found", "message": "workspace not found"}
            _, membership = workspace_bundle
            require_workspace_role(membership, minimum_role="admin")

            daily = repo.list_workspace_funnel_daily(
                workspace_id=workspace_id,
                start_date=range_from,
                end_date=range_to,
                funnel_events=FUNNEL_EVENT_SEQUENCE,
            )
            return 200, {
                "workspaceId": workspace_id,
                "from": range_from.isoformat(),
                "to": range_to.isoformat(),
                "days": daily,
            }
        finally:
            conn.close()

    def _authenticate(self, headers: Any) -> str:
        authorization = headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            raise AuthenticationError("missing bearer token")

        token = authorization[len("Bearer ") :]

        try:
            payload = decode_access_token(token, secret=self.settings.auth_secret)
        except TokenError as exc:
            raise AuthenticationError(str(exc)) from exc

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthenticationError("token subject missing")

        return subject


class AppRequestHandler(BaseHTTPRequestHandler):
    server_version = "PaperclipAuthScaffold/0.1"

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle(self) -> None:
        app: App = self.server.app  # type: ignore[attr-defined]
        try:
            status, payload = app.dispatch(
                method=self.command,
                raw_path=self.path,
                headers=self.headers,
                rfile=self.rfile,
            )
        except AuthenticationError as exc:
            _write_json(self, 401, {"error": "unauthorized", "message": str(exc)})
            return
        except AuthorizationError as exc:
            _write_json(self, 403, {"error": "forbidden", "message": str(exc)})
            return
        except ValueError as exc:
            _write_json(self, 400, {"error": "bad_request", "message": str(exc)})
            return
        except sqlite3.OperationalError:
            _write_json(
                self,
                503,
                {
                    "error": "temporarily_unavailable",
                    "message": "temporary database issue; retry the request",
                },
            )
            return

        _write_json(self, status, payload)


def _read_json_body(headers: Any, rfile: Any) -> dict[str, Any]:
    length_header = headers.get("Content-Length", "0")
    try:
        length = int(length_header)
    except ValueError as exc:
        raise ValueError("content-length must be a number") from exc

    if length <= 0:
        return {}

    raw = rfile.read(length)
    if not raw:
        return {}

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("request body must be valid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("request JSON must be an object")

    return parsed


def _resolve_funnel_date_range(query: dict[str, list[str]]) -> tuple[date, date]:
    today = date.today()
    from_values = query.get("from", [])
    to_values = query.get("to", [])

    from_value = from_values[0].strip() if from_values else ""
    to_value = to_values[0].strip() if to_values else ""

    if from_value:
        try:
            range_from = date.fromisoformat(from_value)
        except ValueError as exc:
            raise ValueError("from must use YYYY-MM-DD format") from exc
    else:
        range_from = today - timedelta(days=6)

    if to_value:
        try:
            range_to = date.fromisoformat(to_value)
        except ValueError as exc:
            raise ValueError("to must use YYYY-MM-DD format") from exc
    else:
        range_to = today

    if range_from > range_to:
        raise ValueError("from must be on or before to")

    return range_from, range_to


def _build_feedback_triage_title(*, category: str, message: str) -> str:
    normalized_message = " ".join(message.split())
    prefix = f"[{category}] "
    max_message_length = 80 - len(prefix)
    if len(normalized_message) > max_message_length:
        normalized_message = normalized_message[: max_message_length - 3].rstrip() + "..."
    return prefix + normalized_message


def _build_beta_accept_response(
    *,
    response_status: int,
    token: str,
    user_id: str,
    user_email: str,
    workspace_id: str,
    workspace_name: str,
    workspace_slug: str,
    membership_role: str,
    cohort: str,
    invitation_id: str,
) -> tuple[int, dict[str, Any]]:
    return response_status, {
        "token": token,
        "user": {"id": user_id, "email": user_email},
        "workspace": {
            "id": workspace_id,
            "name": workspace_name,
            "slug": workspace_slug,
        },
        "membership": {
            "workspaceId": workspace_id,
            "role": membership_role,
        },
        "cohort": cohort,
        "invitation": {
            "id": invitation_id,
            "status": "accepted",
        },
    }


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def create_server(
    *,
    settings: Settings | None = None,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> ThreadingHTTPServer:
    app_settings = settings or Settings.from_env()
    app = App(app_settings)
    server = ThreadingHTTPServer((host, port), AppRequestHandler)
    server.app = app  # type: ignore[attr-defined]
    return server


def main() -> None:
    settings = Settings.from_env()
    host = "0.0.0.0"
    port = 8080

    server = create_server(settings=settings, host=host, port=port)
    print(f"listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

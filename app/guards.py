from __future__ import annotations

from .domain import ROLES, WorkspaceMembership

ROLE_ORDER = {"member": 1, "admin": 2, "owner": 3}


class AuthorizationError(PermissionError):
    pass


def require_workspace_role(
    membership: WorkspaceMembership | None,
    *,
    minimum_role: str,
) -> None:
    if minimum_role not in ROLES:
        raise ValueError(f"unknown role: {minimum_role}")

    if membership is None:
        raise AuthorizationError("workspace membership required")

    current_rank = ROLE_ORDER.get(membership.role)
    required_rank = ROLE_ORDER[minimum_role]

    if current_rank is None or current_rank < required_rank:
        raise AuthorizationError(
            f"role {membership.role!r} cannot access {minimum_role!r} endpoint"
        )

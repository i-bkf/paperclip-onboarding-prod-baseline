from __future__ import annotations

from dataclasses import dataclass

ROLES = ("member", "admin", "owner")


@dataclass(frozen=True)
class Account:
    id: str
    name: str


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str


@dataclass(frozen=True)
class Workspace:
    id: str
    account_id: str
    name: str
    slug: str


@dataclass(frozen=True)
class WorkspaceMembership:
    id: str
    workspace_id: str
    user_id: str
    role: str

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    db_path: str
    auth_secret: str
    token_ttl_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("APP_DB_PATH", "data/dev.sqlite3"),
            auth_secret=os.environ.get("APP_AUTH_SECRET", "dev-insecure-secret"),
            token_ttl_seconds=int(os.environ.get("APP_TOKEN_TTL_SECONDS", "3600")),
        )

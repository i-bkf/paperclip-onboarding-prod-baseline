from __future__ import annotations

from pathlib import Path
import sqlite3


DEFAULT_MIGRATIONS_DIR = Path("db/migrations")


def connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if path.parent and str(path.parent) != ".":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate(db_path: str, migrations_dir: Path = DEFAULT_MIGRATIONS_DIR) -> None:
    conn = connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )
            """
        )

        applied = {
            row["name"]
            for row in conn.execute("SELECT name FROM schema_migrations").fetchall()
        }

        for migration_path in sorted(migrations_dir.glob("*.sql")):
            if migration_path.name in applied:
                continue
            sql = migration_path.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)",
                (migration_path.name,),
            )

        conn.commit()
    finally:
        conn.close()

from __future__ import annotations

import argparse

from .config import Settings
from .db import connect, migrate
from .seeds import seed_local_dev


def run_bootstrap(*, db_path: str, with_seed: bool) -> None:
    migrate(db_path)
    if with_seed:
        conn = connect(db_path)
        try:
            seed_local_dev(conn)
        finally:
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap local Paperclip auth/workspace data")
    parser.add_argument("--db-path", default=Settings.from_env().db_path)
    parser.add_argument("--seed", action="store_true", help="Load local seed data")
    args = parser.parse_args()

    run_bootstrap(db_path=args.db_path, with_seed=args.seed)


if __name__ == "__main__":
    main()

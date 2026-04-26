#!/usr/bin/env bash
set -euo pipefail

export APP_DB_PATH="${APP_DB_PATH:-data/dev.sqlite3}"
python3 -m app.bootstrap --db-path "$APP_DB_PATH"

echo "migrations applied to $APP_DB_PATH"

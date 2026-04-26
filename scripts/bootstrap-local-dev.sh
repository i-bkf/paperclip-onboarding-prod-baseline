#!/usr/bin/env bash
set -euo pipefail

export APP_DB_PATH="${APP_DB_PATH:-data/dev.sqlite3}"
export APP_AUTH_SECRET="${APP_AUTH_SECRET:-dev-insecure-secret}"

python3 -m app.bootstrap --db-path "$APP_DB_PATH" --seed

echo "bootstrapped local database at $APP_DB_PATH"

# Data Model Migration Path

Migrations are SQL files in `db/migrations`, applied in lexical order and tracked in `schema_migrations`.

## Current Baseline

- `001_core_domain.sql` creates:
  - `accounts`
  - `users`
  - `workspaces`
  - `workspace_memberships`
  - membership lookup indexes

## Applying Migrations

```bash
./scripts/migrate.sh
```

You can override the target database file:

```bash
APP_DB_PATH=data/staging.sqlite3 ./scripts/migrate.sh
```

## Creating the Next Migration

1. Add a new file with an incremental prefix, e.g. `002_add_invites.sql`.
2. Keep migrations forward-only and idempotent (`IF NOT EXISTS` where possible).
3. Run unit + integration smoke tests after migration changes:

```bash
make ci
```

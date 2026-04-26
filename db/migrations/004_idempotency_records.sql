CREATE TABLE IF NOT EXISTS idempotency_records (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_status INTEGER NOT NULL,
    response_body_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (scope, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_records_created_at
ON idempotency_records(created_at);

CREATE TABLE IF NOT EXISTS product_events (
    id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('backend', 'frontend')),
    actor_user_id TEXT,
    workspace_id TEXT,
    properties_json TEXT NOT NULL DEFAULT '{}',
    dedupe_key TEXT,
    emitted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_product_events_workspace_emitted
ON product_events(workspace_id, emitted_at);

CREATE INDEX IF NOT EXISTS idx_product_events_name_emitted
ON product_events(event_name, emitted_at);

CREATE INDEX IF NOT EXISTS idx_product_events_actor_emitted
ON product_events(actor_user_id, emitted_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_events_dedupe_unique
ON product_events(dedupe_key)
WHERE dedupe_key IS NOT NULL;

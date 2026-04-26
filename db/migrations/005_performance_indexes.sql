CREATE INDEX IF NOT EXISTS idx_product_events_workspace_name_emitted_actor
ON product_events(workspace_id, event_name, emitted_at, actor_user_id);

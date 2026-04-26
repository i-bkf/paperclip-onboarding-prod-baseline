CREATE TABLE IF NOT EXISTS beta_invitations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    invited_email TEXT NOT NULL,
    invited_by_user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('member', 'admin')),
    cohort TEXT NOT NULL,
    invitation_token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'revoked')),
    accepted_user_id TEXT,
    accepted_at TEXT,
    revoked_by_user_id TEXT,
    revoked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (accepted_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (revoked_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_beta_invitations_workspace_email_pending
ON beta_invitations(workspace_id, invited_email)
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_beta_invitations_workspace_status
ON beta_invitations(workspace_id, status);

CREATE TABLE IF NOT EXISTS beta_cohort_memberships (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    cohort TEXT NOT NULL,
    source_invitation_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (workspace_id, user_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (source_invitation_id) REFERENCES beta_invitations(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_beta_cohort_memberships_workspace_cohort
ON beta_cohort_memberships(workspace_id, cohort);

CREATE TABLE IF NOT EXISTS onboarding_checklist_progress (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    cohort TEXT NOT NULL,
    step_key TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (workspace_id, user_id, step_key),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_onboarding_progress_workspace_cohort_step
ON onboarding_checklist_progress(workspace_id, cohort, step_key);

CREATE TABLE IF NOT EXISTS feedback_submissions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    submitted_by_user_id TEXT NOT NULL,
    cohort TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feedback_submissions_workspace_created
ON feedback_submissions(workspace_id, created_at);

CREATE TABLE IF NOT EXISTS triage_tickets (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    feedback_submission_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'triaged', 'closed')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (feedback_submission_id) REFERENCES feedback_submissions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_triage_tickets_workspace_status
ON triage_tickets(workspace_id, status);

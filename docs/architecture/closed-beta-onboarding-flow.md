# Closed Beta Onboarding Flow

Milestone `M2-S1` introduces closed beta controls and cohort-aware onboarding.

## Scope

- Admin can invite and revoke beta users per workspace.
- Invitees can accept an invitation and join the workspace with a cohort assignment.
- Onboarding checklist progress is recorded per user and aggregated by cohort.
- Feedback submissions automatically create internal triage tickets.
- Feedback submissions also advance checklist step `first_feedback_shared`.

## API Summary

- `POST /api/v1/workspaces/{workspaceId}/beta/invitations`
  - Auth: workspace `admin+`
  - Creates a pending invitation with `email`, `role`, and `cohort`.
- `POST /api/v1/workspaces/{workspaceId}/beta/invitations/{invitationId}/revoke`
  - Auth: workspace `admin+`
  - Revokes a pending invitation.
- `POST /api/v1/beta/invitations/{invitationToken}/accept`
  - Auth: public
  - Accepts invitation and creates workspace membership.
- `POST /api/v1/workspaces/{workspaceId}/onboarding/checklist/complete`
  - Auth: workspace `member+`
  - Marks one allowed checklist step as completed.
- `GET /api/v1/workspaces/{workspaceId}/onboarding/checklist/cohorts`
  - Auth: workspace `admin+`
  - Returns cohort-level completion metrics.
- `POST /api/v1/workspaces/{workspaceId}/feedback`
  - Auth: workspace `member+`
  - Records feedback and auto-creates a triage ticket.

## Data Model Additions

Migration: `db/migrations/003_closed_beta_onboarding.sql`

- `beta_invitations`
- `beta_cohort_memberships`
- `onboarding_checklist_progress`
- `feedback_submissions`
- `triage_tickets`

## Onboarding Checklist Steps

The default progressive steps are:

- `profile_completed`
- `workspace_customized`
- `first_feedback_shared`

These are tracked as unique `(workspace, user, step)` completions.

## Validation Coverage

Integration smoke coverage includes:

- invite and revoke flow
- invitation acceptance into a cohort
- per-cohort onboarding progress aggregation
- feedback submission producing an open triage ticket

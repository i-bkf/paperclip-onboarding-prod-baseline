# Core Value Workflow v1 Hardening

Milestone `M2-S2` hardens the first value-producing onboarding workflow by adding retry-safe semantics and predictable failure behavior.

## Hardened behaviors

- Idempotency replay support for user-triggered mutating routes using `Idempotency-Key`:
  - `POST /api/v1/workspaces/{workspaceId}/beta/invitations`
  - `POST /api/v1/workspaces/{workspaceId}/beta/invitations/{invitationId}/revoke`
  - `POST /api/v1/beta/invitations/{invitationToken}/accept`
  - `POST /api/v1/workspaces/{workspaceId}/onboarding/checklist/complete`
  - `POST /api/v1/workspaces/{workspaceId}/feedback`
- Reusing the same key with the same payload returns the original response body and status.
- Reusing the same key with a different payload returns `400`.
- Invitation acceptance is now replay-safe for already-accepted invites tied to the same user.
- Transient sqlite operational failures return a recoverable `503 temporarily_unavailable` response.
- DB connections use `PRAGMA busy_timeout = 5000` to reduce lock-related flakiness under bursty writes.

## Data model

Migration `004_idempotency_records.sql` adds durable idempotency response storage.

- Unique key: `(scope, idempotency_key)`
- Stored fields: request hash, response status, response body, creation timestamp

## Recovery semantics

Known failure mode handling:

- Duplicate network retries after a successful write: safe replay via idempotency table.
- Client-side retries after transient DB contention: bounded lock wait + explicit `503` for retry.
- Partial duplicate invitation acceptance attempts: existing accepted membership returns success instead of unrecoverable failure.

## Regression coverage

Integration tests validate replay behavior and payload conflict rejection for invite, invitation accept, and feedback submission paths.

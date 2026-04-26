# Product Telemetry Foundation (M1-S3)

This document defines the event taxonomy, event ownership, and dashboard contract
for signup-to-activation visibility.

## Funnel Scope

The first funnel covers `signup -> workspace first access -> activation`.

### Canonical events

| Event name | Trigger | Source | Primary owner |
| --- | --- | --- | --- |
| `onboarding.signup_completed` | Successful `POST /api/v1/signup` | backend | Backend engineering |
| `onboarding.workspace_first_accessed` | First successful `GET /api/v1/workspaces/{workspaceId}` by user/workspace | backend | Backend engineering |
| `onboarding.activation_completed` | Frontend onboarding completion hook (`POST /api/v1/workspaces/{workspaceId}/telemetry/events`) | frontend | Product + frontend engineering |

### Naming rules

- Namespace by domain (`onboarding.*`).
- Use past-tense event verbs for state transitions (`*_completed`, `*_accessed`).
- Preserve backwards compatibility once consumed by dashboard queries.

## Emission and Dedupe

- All events are persisted in `product_events`.
- `onboarding.workspace_first_accessed` is deduped per `workspaceId + userId`.
- Frontend events may include `dedupeKey`; duplicate keys are accepted but ignored.

## Dashboard API

Endpoint:

- `GET /api/v1/workspaces/{workspaceId}/telemetry/funnel/daily?from=YYYY-MM-DD&to=YYYY-MM-DD`

Behavior:

- Returns one row per day with all funnel steps in fixed order.
- `conversionFromSignupPct` is computed per day from the signup count baseline.
- Requires `admin+` workspace role.

## Data Ownership and Operations

- Backend engineering owns schema integrity and event write paths.
- Product analytics owns funnel interpretation and KPI definitions.
- Frontend engineering owns onboarding hook placement for client-emitted events.

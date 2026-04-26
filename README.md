# Paperclip Production Baseline

This repository defines the production baseline for delivery standards, CI gates, staged deployments, and the initial auth/workspace domain scaffold.

## Branch Strategy

- `main`: production branch, protected.
- `develop`: integration branch for pre-production readiness.
- `feature/<ticket-id>-<slug>`: short-lived branches merged into `develop`.
- Promotion flow: `feature/* -> develop -> main`.

## Required Checks for `main`

The following checks are required before merge:

- `lint`
- `unit-tests`
- `integration-smoke`
- `release-quality-gates`

See [Branch Protection Setup](docs/operations/branch-protection.md).

## CI/CD Workflows

- CI: `.github/workflows/ci.yml`
- Staging deploy (one-click): `.github/workflows/deploy-staging.yml`
- Production deploy: `.github/workflows/deploy-production.yml`

## Local Validation

```bash
make ci
make quality-gates
make bootstrap-local
make migrate
make deploy-staging
make deploy-production
make rollback TARGET_ENV=production RELEASE_ID=staging-<id>
make slo-dashboard
make reliability-drill
make cost-alerts
```

## Auth/Workspace Skeleton

Milestone `M1-S2` introduces:

- Core domain entities: `accounts`, `users`, `workspaces`, `workspace_memberships`
- Signup flow: `POST /api/v1/signup`
- Protected endpoints with role guards:
  - `GET /api/v1/workspaces/{workspaceId}` (`member+`)
  - `GET /api/v1/workspaces/{workspaceId}/members` (`admin+`)
- Local DB bootstrap and seed flow (`./scripts/bootstrap-local-dev.sh`)
- SQL migration path (`db/migrations` + `docs/operations/data-model-migrations.md`)

See [Core Domain Skeleton](docs/architecture/core-domain-skeleton.md) and
[Data Model Migration Path](docs/operations/data-model-migrations.md).

## Product Telemetry Foundation

Milestone `M1-S3` adds:

- Canonical onboarding funnel events:
  - `onboarding.signup_completed`
  - `onboarding.workspace_first_accessed`
  - `onboarding.activation_completed`
- Frontend event ingestion route:
  - `POST /api/v1/workspaces/{workspaceId}/telemetry/events`
- Daily funnel dashboard route:
  - `GET /api/v1/workspaces/{workspaceId}/telemetry/funnel/daily?from=YYYY-MM-DD&to=YYYY-MM-DD`

See [Product Telemetry Foundation](docs/architecture/product-telemetry-foundation.md).

## Closed Beta Enablement and Onboarding Flow

Milestone `M2-S1` adds:

- Admin invitation controls for closed beta cohorts:
  - `POST /api/v1/workspaces/{workspaceId}/beta/invitations`
  - `POST /api/v1/workspaces/{workspaceId}/beta/invitations/{invitationId}/revoke`
  - `POST /api/v1/beta/invitations/{invitationToken}/accept`
- Progressive onboarding checklist tracking by cohort:
  - `POST /api/v1/workspaces/{workspaceId}/onboarding/checklist/complete`
  - `GET /api/v1/workspaces/{workspaceId}/onboarding/checklist/cohorts`
- Feedback capture with automatic triage ticket creation:
  - `POST /api/v1/workspaces/{workspaceId}/feedback`

See [Closed Beta Onboarding Flow](docs/architecture/closed-beta-onboarding-flow.md).

## Core Value Workflow v1 Hardening

Milestone `M2-S2` adds:

- idempotency-key replay handling for mutating onboarding and beta invitation routes
- deterministic conflict handling for idempotency key reuse with different payloads
- replay-safe invitation acceptance semantics
- transient DB contention hardening (`busy_timeout` + retryable `503` response)
- regression coverage for retry/replay behavior on critical path flows

See [Core Value Workflow Hardening](docs/architecture/core-value-workflow-hardening.md).

## Release Quality Gates + UAT Routine

Milestone `M2-S3` adds:

- auto-generated release checklist and go/no-go artifact for every deployment
- weekly UAT/bug-bash cadence with per-release result logs
- defect severity policy with same-day owner + ETA enforcement for high severity issues
- release quality gate validation script and CI check (`release-quality-gates`)

See [Release Quality Gates and UAT Routine](docs/operations/release-quality-gates.md).

## Rollback

Rollback runbook: [Rollback Procedure](docs/operations/rollback.md)
Rollback drill evidence: [Rollback Test Log](docs/operations/rollback-test-log.md)

## Reliability, SLOs, and Incident Response

Milestone `M3-S1` adds:

- service level objectives for signup availability, workspace latency, and activation completion
- leadership-friendly SLO dashboard artifact generation
- alert drill flow for latency/error-budget breaches with pager event evidence
- incident runbook, escalation path, and reusable incident template

See [Reliability SLOs and Alert Policy](docs/operations/reliability-slos.md),
[Incident Response Runbook](docs/operations/incident-response.md), and
[Incident Template](docs/operations/incident-template.md).
Drill evidence: [Incident Drill Log](docs/operations/incident-drill-log.md).

## Performance and Cost Optimization

Milestone `M3-S2` adds:

- p95 latency target definitions and repeatable local profiling for top API routes
- query optimization pass across authorization, onboarding cohorts, and funnel analytics
- monthly infra budget guardrails with warning/critical thresholds and alert routes

See [Performance and Cost Optimization](docs/operations/performance-cost-optimization.md).

## Founding Engineer Handoff Sprint Plan

Milestone `M3-S3` adds:

- two-sprint (10-ticket) execution backlog ordered by impact and risk
- reusable definition of ready/done templates for ticket quality and handoff consistency
- architecture decision log and day-by-day onboarding map for fast context transfer

See [Founding Engineer Handoff Sprint Plan](docs/operations/founding-engineer-handoff-sprint-plan.md),
[Engineering Delivery Templates](docs/operations/engineering-delivery-templates.md),
[Architecture Decision Log](docs/architecture/decision-log.md), and
[Founding Engineer Onboarding Map](docs/operations/founding-engineer-onboarding-map.md).

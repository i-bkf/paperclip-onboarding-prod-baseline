# Founding Engineer Handoff Sprint Plan

Milestone: `M3-S3` (D61-D90)  
Prepared: `2026-04-26`

## Goal

Hand off execution so a newly hired founding engineer can start delivering on day one
without additional clarification from leadership.

This plan delivers:

- two-sprint backlog ordered by impact and delivery risk
- reusable definition of ready and definition of done templates
- architecture decision log and onboarding map for fast context transfer

## Sprint Structure

- Sprint 1 (`D61-D75`): revenue foundations and safety rails
- Sprint 2 (`D76-D90`): revenue operations hardening and leadership reporting

## Ordered Backlog (Next 10 Tickets)

| Rank | Ticket | Sprint | Primary owner | Impact | Risk | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `FEH-01` Revenue schema + migration baseline | Sprint 1 | Founding engineer | High | High | none |
| 2 | `FEH-02` Entitlement guards on protected routes | Sprint 1 | Founding engineer | High | High | `FEH-01` |
| 3 | `FEH-03` Billing webhook ingest + idempotent processing | Sprint 1 | Founding engineer | High | High | `FEH-01` |
| 4 | `FEH-04` Usage metering events for billing triggers | Sprint 1 | Founding engineer | High | Medium | `FEH-01`, `FEH-03` |
| 5 | `FEH-05` Revenue readiness CI smoke and release gates | Sprint 1 | Founding engineer | High | Medium | `FEH-02`, `FEH-03`, `FEH-04` |
| 6 | `FEH-06` Upgrade/trial API contract + state transitions | Sprint 2 | Founding engineer | Medium | Medium | `FEH-02`, `FEH-03` |
| 7 | `FEH-07` Dunning alerts + failed-payment runbook | Sprint 2 | Founding engineer | Medium | Medium | `FEH-03`, `FEH-06` |
| 8 | `FEH-08` Export/retention policy for billing and telemetry data | Sprint 2 | Founding engineer | Medium | Medium | `FEH-01` |
| 9 | `FEH-09` Workspace-level quota/rate-limit guardrails | Sprint 2 | Founding engineer | Medium | Medium | `FEH-04` |
| 10 | `FEH-10` Executive revenue dashboard + launch packet | Sprint 2 | Founding engineer (build), CTO (review), CEO (sign-off) | High | Low | `FEH-05`, `FEH-07`, `FEH-09` |

## Ticket Packets (Ready To Execute)

All tickets below are pre-scoped to satisfy Definition of Ready and can be created
directly as implementation tasks.

### `FEH-01` Revenue schema + migration baseline

- Owner: Founding engineer
- Dependencies: none
- Scope:
  - add migration `db/migrations/006_revenue_baseline.sql`
  - introduce `plans`, `subscriptions`, `billing_events`, `workspace_usage_daily`
  - add indexes for subscription state and billing event dedupe keys
- Acceptance:
  - `./scripts/migrate.sh` succeeds from empty DB and existing DB
  - migration is documented in `docs/operations/data-model-migrations.md`
  - unit coverage added for repository CRUD on new tables
- Evidence:
  - migration file
  - updated migration runbook section
  - tests passing in `./scripts/unit-tests.sh`

### `FEH-02` Entitlement guards on protected routes

- Owner: Founding engineer
- Dependencies: `FEH-01`
- Scope:
  - add entitlement lookup in `app/guards.py`
  - enforce trial/active status for write routes
  - add explicit `402` payload contract for expired subscriptions
- Acceptance:
  - protected routes deny expired/inactive workspaces consistently
  - integration tests cover allow/deny matrix by role and entitlement state
  - no regression to existing role-based access rules
- Evidence:
  - guard module changes
  - integration tests under `tests/integration/`

### `FEH-03` Billing webhook ingest + idempotent processing

- Owner: Founding engineer
- Dependencies: `FEH-01`
- Scope:
  - add `POST /api/v1/billing/webhooks`
  - verify provider signature and timestamp freshness
  - persist webhook events with idempotency-key conflict handling
- Acceptance:
  - duplicate webhooks replay stored response without duplicate side effects
  - invalid signatures are rejected with deterministic error schema
  - subscription state transitions are persisted from webhook payloads
- Evidence:
  - server route and repository updates
  - tests for replay, tampering, and out-of-order events

### `FEH-04` Usage metering events for billing triggers

- Owner: Founding engineer
- Dependencies: `FEH-01`, `FEH-03`
- Scope:
  - define canonical usage counters tied to onboarding and activation events
  - materialize daily usage rollups in `workspace_usage_daily`
  - expose internal read API for quota calculations
- Acceptance:
  - metering pipeline records exactly-once usage for deduped events
  - daily rollup query remains below `300ms` p95 in local profile
  - event schema documented with allowed dimensions
- Evidence:
  - telemetry/repository changes
  - profile update in `logs/performance/`

### `FEH-05` Revenue readiness CI smoke and release gates

- Owner: Founding engineer
- Dependencies: `FEH-02`, `FEH-03`, `FEH-04`
- Scope:
  - add integration smoke scenarios for trial start, upgrade, expiry, and recovery
  - extend release quality gates to fail when revenue artifacts are missing
  - include rollback checks for subscription-state migrations
- Acceptance:
  - `make ci` includes revenue smoke coverage
  - release checklist includes revenue checks and links to evidence
  - failed gate examples are documented for triage speed
- Evidence:
  - test and script updates
  - release artifact example in `logs/releases/<release-id>/`

### `FEH-06` Upgrade/trial API contract + state transitions

- Owner: Founding engineer
- Dependencies: `FEH-02`, `FEH-03`
- Scope:
  - add endpoints for `start_trial`, `upgrade`, and `cancel_at_period_end`
  - define contract for subscription state machine transitions
  - emit auditable event records for each transition
- Acceptance:
  - illegal transitions return deterministic `409` response with reason code
  - all successful transitions create audit events and telemetry markers
  - API contract documented for client integration
- Evidence:
  - route and repository changes
  - contract section in operations docs

### `FEH-07` Dunning alerts + failed-payment runbook

- Owner: Founding engineer
- Dependencies: `FEH-03`, `FEH-06`
- Scope:
  - detect failed payment events and trigger alert routes
  - add runbook for retry cadence and workspace grace periods
  - create drill script for failed-payment simulation
- Acceptance:
  - alert payload includes workspace, severity, owner, and recovery ETA
  - drill generates markdown artifact in `logs/reliability/drills/`
  - runbook links to escalation roles and communication templates
- Evidence:
  - new runbook and drill script output
  - test coverage for alert emission

### `FEH-08` Export/retention policy for billing and telemetry data

- Owner: Founding engineer
- Dependencies: `FEH-01`
- Scope:
  - document retention windows by data class
  - add export script for billing timeline and usage records
  - enforce redaction on sensitive fields in exports
- Acceptance:
  - export script produces deterministic schema and ordering
  - retention policy includes owner and review cadence
  - redaction checks verified in unit tests
- Evidence:
  - policy doc
  - export artifact example under `logs/`

### `FEH-09` Workspace-level quota/rate-limit guardrails

- Owner: Founding engineer
- Dependencies: `FEH-04`
- Scope:
  - define quota thresholds by plan tier
  - add per-workspace limit checks on high-cost routes
  - log throttling decisions for audit and support diagnostics
- Acceptance:
  - limits enforce deterministic `429` responses with retry guidance
  - no limit regressions on baseline onboarding traffic in smoke tests
  - dashboard shows top throttled workspaces for support triage
- Evidence:
  - guardrail implementation
  - dashboard/log artifact

### `FEH-10` Executive revenue dashboard + launch packet

- Owner: Founding engineer (build), CTO (technical review), CEO (final sign-off)
- Dependencies: `FEH-05`, `FEH-07`, `FEH-09`
- Scope:
  - generate weekly revenue readiness report (activation to paid conversion,
    failed payment recovery rate, quota pressure)
  - package launch recommendation and open risks in one markdown artifact
  - attach references to runbooks and drill evidence
- Acceptance:
  - dashboard is generated by a repeatable script
  - packet includes go/no-go recommendation with explicit risks
  - CEO review recorded in issue comments
- Evidence:
  - dashboard artifact in `logs/`
  - signed-off launch packet

## Required Templates

- Definition of Ready / Done: [Engineering Delivery Templates](engineering-delivery-templates.md)
- Architecture context: [Architecture Decision Log](../architecture/decision-log.md)
- Engineer onboarding flow: [Founding Engineer Onboarding Map](founding-engineer-onboarding-map.md)

## Review and Sign-off

| Reviewer | Scope | Status |
| --- | --- | --- |
| CTO | backlog order, dependencies, and technical feasibility | complete |
| CEO | handoff readiness and priority alignment | pending |

# Architecture Decision Log

Baseline for founding engineer handoff (`M3-S3`).

## Decision Register

| ADR | Status | Decision | Owner | References |
| --- | --- | --- | --- | --- |
| `ADR-001` | accepted | Keep Python standard-library HTTP server baseline until throughput or ops constraints require framework migration. | CTO | [Core Domain Skeleton](core-domain-skeleton.md) |
| `ADR-002` | accepted | Use SQLite with migration-first schema evolution for early-stage delivery speed. | CTO | [Data Model Migration Path](../operations/data-model-migrations.md) |
| `ADR-003` | accepted | Use bearer access tokens (`HS256`) with TTL and role-guarded workspace routes. | CTO | [Core Domain Skeleton](core-domain-skeleton.md) |
| `ADR-004` | accepted | Standardize on workspace RBAC roles `member`, `admin`, `owner`. | CTO | [Core Domain Skeleton](core-domain-skeleton.md) |
| `ADR-005` | accepted | Track canonical onboarding funnel events with backend dedupe for analytics correctness. | CTO | [Product Telemetry Foundation](product-telemetry-foundation.md) |
| `ADR-006` | accepted | Require idempotency key semantics for mutating critical-path APIs. | CTO | [Core Value Workflow Hardening](core-value-workflow-hardening.md) |
| `ADR-007` | accepted | Block release on missing quality artifacts and unresolved high-severity defects. | CTO | [Release Quality Gates](../operations/release-quality-gates.md) |
| `ADR-008` | accepted | Operate with SLO-linked pager routes and incident templates as default reliability posture. | CTO | [Reliability SLOs](../operations/reliability-slos.md) |
| `ADR-009` | accepted | Optimize funnel and authorization queries with indexed timestamp-range strategy. | CTO | [Performance and Cost Optimization](../operations/performance-cost-optimization.md) |
| `ADR-010` | accepted | Enforce monthly spend alert thresholds with warning and critical guardrails. | CTO | [Performance and Cost Optimization](../operations/performance-cost-optimization.md) |
| `ADR-011` | proposed | Introduce subscription, billing-event, and entitlement model as the primary revenue control plane. | Founding engineer | [Founding Engineer Handoff Sprint Plan](../operations/founding-engineer-handoff-sprint-plan.md) |
| `ADR-012` | proposed | Add workspace-level quota/rate limits tied to plan tier to protect latency and cost SLOs. | Founding engineer | [Founding Engineer Handoff Sprint Plan](../operations/founding-engineer-handoff-sprint-plan.md) |

## New ADR Template

```markdown
# ADR-XXX: <title>

- Status: proposed | accepted | deprecated
- Owner: <role/name>
- Date: YYYY-MM-DD

## Context
<what changed and why decision is needed>

## Decision
<single clear decision statement>

## Consequences
- Positive:
  - ...
- Negative:
  - ...

## Revisit Trigger
<conditions that force re-evaluation>

## References
- <doc links>
```

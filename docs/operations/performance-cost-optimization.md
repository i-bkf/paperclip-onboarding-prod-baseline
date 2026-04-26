# Performance and Cost Optimization

Milestone: `M3-S2`

## Scope

This milestone introduces three outcomes:

- baseline p95 latency targets for key API routes and repeatable local measurement
- query-level optimization for top backend hotspots with before/after evidence
- monthly infrastructure budget guardrails and alert thresholds

## p95 Targets

| Endpoint | p95 target |
| --- | --- |
| `GET /api/v1/workspaces/{workspaceId}` | `<= 120ms` |
| `GET /api/v1/workspaces/{workspaceId}/onboarding/checklist/cohorts` | `<= 250ms` |
| `GET /api/v1/workspaces/{workspaceId}/telemetry/funnel/daily` | `<= 300ms` |

## Reproducible Profiling

Generate an updated benchmark report:

```bash
./scripts/performance-profile.py
```

Default report path:

- `logs/performance/m3-s2-performance-profile.md`

Current evidence:

- [M3-S2 performance profile](../../logs/performance/m3-s2-performance-profile.md)

## Query/Hotspot Optimizations

1. Workspace authorization lookups
- Consolidated `workspace` + `membership` checks into one repository query for protected workspace routes.

2. Onboarding cohort aggregation
- Replaced per-cohort user-step fan-out query loop with grouped aggregate query.

3. Funnel analytics
- Replaced `date(emitted_at)` filtering with indexed timestamp range bounds.
- Fixed distinct counting semantics for anonymous events.
- Added supporting index:
  - `db/migrations/005_performance_indexes.sql`

## Cost Guardrails and Monthly Budget Alerts

Threshold and spend inputs:

- `data/cost/monthly-budget-thresholds.tsv`
- `data/cost/monthly-spend-snapshot.tsv`

Generate budget alert output:

```bash
make cost-alerts
# or
./scripts/cost-budget-alerts.sh
```

Default output:

- `logs/cost/monthly-budget-alerts.md`

Current evidence:

- [Monthly budget alert snapshot](../../logs/cost/monthly-budget-alerts.md)

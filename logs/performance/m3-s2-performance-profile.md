# M3-S2 Performance and Cost Optimization Report

- Generated at (UTC): 2026-04-26T13:13:19Z
- Profile dataset: 1 workspace, 900 members, 6 cohorts, 10,000+ funnel events with 180-day history tail
- Measurement method: local synthetic benchmark with p95 latency focus

## p95 Latency Targets and Measurements

| Endpoint | p95 target (ms) | Measured p95 (ms) | Status |
| --- | --- | --- | --- |
| `/api/v1/workspaces/{id}` | 120.00 | 0.61 | **pass** |
| `/api/v1/workspaces/{id}/onboarding/checklist/cohorts` | 250.00 | 1.86 | **pass** |
| `/api/v1/workspaces/{id}/telemetry/funnel/daily` | 300.00 | 1.68 | **pass** |

## Top 3 Hotspots: Before vs After

| Hotspot | Before p95 (ms) | After p95 (ms) | p95 improvement |
| --- | --- | --- | --- |
| Workspace authorization lookup (2 queries -> 1 query) | 0.01 | 0.01 | 36.37% |
| Onboarding cohort aggregation (N+1 -> grouped query) | 2.19 | 1.14 | 47.73% |
| Funnel analytics date filter/distinct counting rewrite | 2.52 | 1.13 | 55.22% |

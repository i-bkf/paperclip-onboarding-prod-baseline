# Reliability SLOs and Alert Policy

Milestone: `M3-S1`

## Core User Journey SLOs (30-day rolling window)

| SLO ID | User journey | SLI | Target | Pager route |
| --- | --- | --- | --- | --- |
| `signup_request_success` | Signup API availability | Percent of `POST /api/v1/signup` responses that are non-`5xx` | `>= 99.90%` | `pager-growth` |
| `workspace_first_access_latency` | First workspace access latency | Percent of `GET /api/v1/workspaces/{id}` responses under `800ms` | `>= 99.00%` | `pager-platform` |
| `activation_completion_rate` | Activation completion | Percent of signups that fire `onboarding.activation_completed` within `24h` | `>= 90.00%` | `pager-growth` |

## Dashboard and Leadership Visibility

Generate the SLO dashboard as markdown:

```bash
./scripts/slo-dashboard.sh
```

Default output:

- `logs/reliability/slo-dashboard.md`

This artifact is designed to be shared directly in leadership updates.

## Alerting for Error-Budget or Latency Breaches

Run a drill simulation that evaluates SLOs, emits pager alerts for breaches, and
opens an incident record from the template:

```bash
./scripts/reliability-alert-drill.sh
```

Drill outputs:

- `logs/reliability/drills/<drill-id>/slo-dashboard.md`
- `logs/reliability/drills/<drill-id>/pager-alerts.tsv`
- `logs/reliability/drills/<drill-id>/incident-<drill-id>.md`
- `logs/reliability/drills/<drill-id>/drill-summary.md`

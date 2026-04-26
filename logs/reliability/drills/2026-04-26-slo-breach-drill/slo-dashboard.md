# SLO Dashboard

- Generated at (UTC): 2026-04-26T13:02:04Z
- Snapshot: `data/slo/drill-breach-sli-snapshot.tsv`
- Healthy SLOs: 1
- Breached SLOs: 2

| SLO ID | Core journey | SLI | Target | Actual | Error budget remaining (pp) | Window | Owner | Pager route | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `signup_request_success` | Signup API availability | Percent of POST /api/v1/signup responses that are non-5xx. | 99.90% | 98.10% | -1.80 | 30d | `growth-oncall` | `pager-growth` | **breached** |
| `workspace_first_access_latency` | First workspace access latency | Percent of GET /api/v1/workspaces/{id} responses under 800ms. | 99.00% | 97.40% | -1.60 | 30d | `platform-oncall` | `pager-platform` | **breached** |
| `activation_completion_rate` | Activation completion | Percent of signups that fire onboarding.activation_completed within 24h. | 90.00% | 90.60% | +0.60 | 30d | `product-oncall` | `pager-growth` | **healthy** |

# Incident Report: INC-20260426130204-SLO-DRILL

## Metadata

- Incident ID: INC-20260426130204-SLO-DRILL
- Severity: SEV-2 (drill)
- Status: resolved
- Started at (UTC): 2026-04-26T13:02:04Z
- Commander: platform-oncall
- Communications channel: #incidents-simulated
- Detection source: Pager alert from SLO breach drill

## Impact

- Affected users/workspaces: simulated workspace cohort only
- User-visible symptoms: synthetic degradation for reliability rehearsal
- Current blast radius: simulation only

## Timeline (UTC)

- 13:02 - Detection via pager alert
- 13:02 - Incident declared
- 13:02 - Mitigation started
- 13:02 - Recovery validated

## Mitigation and Recovery

- Immediate mitigations: failover playbook walkthrough and rollback rehearsal
- Validation checks: dashboard regenerated and alerts acknowledged
- Recovery complete at (UTC): 2026-04-26T13:02:04Z

## Root Cause

- Triggering change or condition: injected SLO regression for drill on `signup_request_success`
- Contributing factors: none (controlled simulation)

## Follow-up Actions

| Action | Owner | Due date (UTC) | Status |
| --- | --- | --- | --- |
| Increase alert annotation detail for on-call handoff | platform-oncall | 2026-04-28 | open |
| Run next drill with cross-functional observers | growth-oncall | 2026-05-03 | open |

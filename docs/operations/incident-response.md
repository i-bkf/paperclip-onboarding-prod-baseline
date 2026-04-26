# Incident Response Runbook and Escalation Path

Milestone: `M3-S1`

## Severity Model

- `SEV-1`: Core journey down or severe data integrity risk. Ack in 5 minutes.
- `SEV-2`: Major degradation with workaround. Ack in 15 minutes.
- `SEV-3`: Limited degradation. Ack in 60 minutes.

## Escalation Path

1. On-call engineer receives pager alert and acknowledges.
2. On-call engineer becomes incident commander until handoff.
3. Escalate to CTO within 10 minutes for `SEV-1` or if mitigation stalls.
4. Notify product/operations stakeholders in the incident channel.
5. Publish status every 15 minutes for `SEV-1`, every 30 minutes for `SEV-2`.

## Response Procedure

1. Declare incident and open a report from [Incident Template](incident-template.md).
2. Contain impact (rollback, rate-limit, or feature flag).
3. Validate recovery using smoke checks and SLO recovery trend.
4. Close incident only after two healthy checks spaced by 5 minutes.
5. Capture follow-up actions with owner and due date.

## Drill Command

```bash
./scripts/reliability-alert-drill.sh
```

The drill is considered successful when it emits `pager-alerts.tsv` and creates
an incident document from the template.

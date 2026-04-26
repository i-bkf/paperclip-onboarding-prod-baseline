# Founding Engineer Onboarding Map

Milestone: `M3-S3`  
Objective: make the incoming engineer independently shippable by day 10.

## Access and Setup Checklist

| Area | Requirement | Owner |
| --- | --- | --- |
| Source control | Repository clone + branch push rights | CTO |
| Runtime | Python `3.12+` and local shell environment | Founding engineer |
| Local DB | `make bootstrap-local` and `make migrate` success | Founding engineer |
| Test workflow | `make ci` execution and interpretation | Founding engineer |
| Release flow | staging deploy + production deploy + rollback dry run | Founding engineer with CTO shadow |
| Reliability ops | SLO dashboard + alert drill generation | Founding engineer |
| Cost ops | budget alert generation and threshold update path | Founding engineer |

## Day-by-Day Plan

| Day | Outcome | Required actions | Evidence artifact | Owner |
| --- | --- | --- | --- | --- |
| 1 | Local environment operational | run `make bootstrap-local`, `make migrate`, `make ci` | terminal output + notes in issue comment | Founding engineer |
| 2 | Domain model and route map understood | read `app/server.py`, `app/repository.py`, milestone docs | architecture summary note | Founding engineer |
| 3 | Safe deploy/rollback path practiced | run `make deploy-staging` then `make rollback TARGET_ENV=staging RELEASE_ID=<id>` | rollback log entry | Founding engineer |
| 4 | Reliability response baseline practiced | run `make slo-dashboard` and `make reliability-drill` | drill summary artifact | Founding engineer |
| 5 | Sprint 1 ticket `FEH-01` completed | ship migration + tests + docs | PR and issue evidence links | Founding engineer |
| 6 | Sprint 1 ticket `FEH-02` completed | ship entitlement guard behavior | integration tests | Founding engineer |
| 7 | Sprint 1 ticket `FEH-03` completed | ship webhook ingest + replay safety | smoke and unit evidence | Founding engineer |
| 8 | Sprint 1 ticket `FEH-04` completed | ship usage metering rollups | performance profile update | Founding engineer |
| 9 | Sprint 1 ticket `FEH-05` completed | ship CI/release gate expansion | release gate artifact | Founding engineer |
| 10 | Hand-off check and sprint 2 kickoff | walkthrough with CTO and CEO | approved kickoff comment | CTO + CEO |

## Onboarding Success Gates

- Day 3 gate: engineer can deploy and rollback without assistance
- Day 5 gate: first revenue ticket merged with full evidence bundle
- Day 10 gate: engineer can pick and execute next ticket from handoff backlog without clarification

## Escalation Path

- Technical unblocker: CTO (`same-day response`)
- Product priority conflict: CEO (`same-day decision`)
- Incident or live risk: follow [Incident Response Runbook](incident-response.md)

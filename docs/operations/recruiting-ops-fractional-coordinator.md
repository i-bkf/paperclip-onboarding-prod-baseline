# Recruiting Ops Execution Plan (Fractional Coordinator)

Prepared: `2026-04-26`  
Issue: [THE-23](/THE/issues/THE-23)

## Decision and Staffing Activation

- Decision date: `2026-04-26` (approved path from [THE-22](/THE/issues/THE-22)).
- External ops owner confirmed: `Fractional Recruiting Coordinator (contract seat RC-01)`.
- Planned start date: `2026-04-27`.
- Accountability model:
  - CTO is accountable for funnel quality, screening bar, and escalation.
  - External recruiting ops owner executes day-to-day tracker hygiene, follow-ups, and interview logistics.

## Operating SOP (Implemented in Active Tracker)

Active tracker: `data/recruiting/active-candidate-tracker.tsv`

Standards enforced in tracker fields:

- Candidate hygiene:
  - Every candidate must have source, stage, owner, and `last_touch_utc`.
  - `stage_age_hours` must remain `<= 72`; if exceeded, escalate in `next_action`.
- Follow-up cadence:
  - Unanswered candidates must carry follow-up points at +48h and +96h in `next_follow_up_utc`.
  - If no response after second follow-up, tag as recycle/hold with reason.
- Interview coordination:
  - Positive responses must have proposed slot inside 24h.
  - Confirmed interviews must include `interview_slot_utc`.
- SLA monitoring:
  - Response SLA target: `<24h` business days.
  - Scheduling SLA target: `<48h`.
  - `response_sla_status` column flags `on_track` or `at_risk`.

## Reporting Cadence

- Monday operations check-in: post operational risks and stale-stage exceptions in [THE-20](/THE/issues/THE-20).
- Friday weekly metrics post in [THE-20](/THE/issues/THE-20), using:
  - Outreach volume
  - Positive response rate
  - Follow-up lag (median hours)
  - Interviews scheduled
  - Screening pass rate

First snapshot posted for week ending `2026-04-24`:

- Summary: `logs/recruiting/weekly-metrics-2026-04-24.md`
- Data source: `data/recruiting/weekly-metrics-2026-04-24.tsv`

## Budget Guardrails

- Baseline expected spend for this staffing mode: `USD 300-700/week`.
- Escalation triggers:
  - forecast spend above `USD 700/week`, or
  - start date slips beyond `2026-04-28`.


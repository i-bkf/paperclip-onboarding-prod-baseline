# Release Quality Gates and UAT Routine

Milestone: `M2-S3`

This runbook defines release go/no-go criteria, weekly UAT cadence, and defect
ownership SLA.

## Pre-release Checklist and Go/No-Go

Each deployment auto-generates a release artifact bundle under:

- `logs/releases/<release-id>/checklist.md`
- `logs/releases/<release-id>/release-notes.md`
- `logs/releases/<release-id>/uat-results.md`
- `logs/releases/<release-id>/defects.tsv`

Required go/no-go criteria in `checklist.md`:

- `lint`, `unit-tests`, and `integration-smoke` are green
- branch protection checks passed on `main`
- rollback target verified
- high-severity defects have owner + same-day ETA
- UAT session completed and logged

## Weekly Bug Bash and UAT Cadence

- Recurrence: every Thursday at 14:00 UTC
- Duration: 60 minutes
- Format:
  - 20 min focused bug bash on release candidate
  - 30 min scenario-based UAT sweep
  - 10 min triage and owner assignment

Results are recorded in `logs/releases/<release-id>/uat-results.md`.

## Defect Severity Policy and SLA

Severity levels:

- `high`: customer-blocking or critical-path breakage
- `medium`: workflow degradation with available workaround
- `low`: cosmetic or minor friction

Ownership SLA:

- `high`: owner and ETA required on the same UTC day defect is logged
- `medium`: owner required within 1 business day
- `low`: owner required within 3 business days

Defects are tracked in `logs/releases/<release-id>/defects.tsv` using:

```text
reported_at_utc  defect_id  severity  owner  eta_utc  status  summary
```

Gate enforcement command:

```bash
./scripts/release-quality-gates.sh
```

The gate fails if:

- release artifacts are missing
- release notes do not link to `uat-results.md`
- any high-severity defect lacks an owner or ETA
- any high-severity defect has an ETA that is not same-day as `reported_at_utc`

# Engineering Delivery Templates

Milestone: `M3-S3`  
Purpose: reusable templates for ongoing execution after founding engineer handoff.

## Definition of Ready (DoR)

A ticket is ready only when all checks below are satisfied.

- Problem statement is one sentence and user-facing
- Owner is named
- Dependencies are explicit (`none` when not applicable)
- Scope includes in-scope and out-of-scope bullets
- Acceptance criteria are testable and measurable
- Evidence path is defined (doc, log, test, or dashboard artifact)
- Risk class is set (`low`, `medium`, `high`) with mitigation note for `high`

### DoR Template

```markdown
## Definition of Ready

- Owner: <name or role>
- Priority: <high|medium|low>
- Risk: <high|medium|low> (<mitigation>)
- Dependencies: <ticket list or none>
- In scope:
  - ...
- Out of scope:
  - ...
- Acceptance criteria:
  - ...
- Evidence expected:
  - ...
```

## Definition of Done (DoD)

A ticket is done only when all checks below are satisfied.

- Code and docs updated together
- Unit and integration tests pass locally
- CI/release gates pass (or documented exception approved by CTO)
- Runbook or operational impact updated where relevant
- Rollback approach documented for risky changes
- Evidence links posted in the issue comment

### DoD Template

```markdown
## Definition of Done

- [ ] Implementation merged in scoped files
- [ ] Unit tests passed (`./scripts/unit-tests.sh`)
- [ ] Integration smoke passed (`./scripts/integration-smoke.sh`)
- [ ] Release quality gate passed (`./scripts/release-quality-gates.sh`)
- [ ] Docs/runbooks updated
- [ ] Rollback impact reviewed
- [ ] Evidence links attached in task comment
```

## Ticket Card Template (Copy/Paste)

```markdown
# <ticket-id> <title>

## Objective
<one sentence outcome>

## Definition of Ready
- Owner: ...
- Priority: ...
- Risk: ...
- Dependencies: ...
- In scope:
  - ...
- Out of scope:
  - ...
- Acceptance criteria:
  - ...
- Evidence expected:
  - ...

## Definition of Done
- [ ] Implementation complete
- [ ] Tests green
- [ ] Docs updated
- [ ] Release gate status recorded
- [ ] Evidence links posted
```

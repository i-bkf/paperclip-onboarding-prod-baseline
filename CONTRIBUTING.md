# Contributing

## Pull Request Rules

- Reference the task identifier in branch name and PR title.
- Keep PRs below ~400 lines of functional diff when possible.
- Require at least one reviewer approval.
- All CI checks must pass before merge.

## Commit Convention

Use Conventional Commits:

- `feat:` new capabilities
- `fix:` bug fixes
- `chore:` maintenance and tooling
- `docs:` documentation-only changes

## Definition of Done

- CI green (`lint`, `unit-tests`, `integration-smoke`)
- Deployment path unchanged or intentionally updated
- Rollback path documented for any production-impacting change

# Rollback Procedure

## Trigger Conditions

Initiate rollback when:

- production smoke checks fail after deploy
- critical customer-facing regression appears
- data integrity risk is detected

## Procedure

1. Identify the last known good release from `logs/deploy-history.tsv`.
2. Run rollback command:

```bash
make rollback TARGET_ENV=production RELEASE_ID=<known-good-release-id>
```

3. Verify active release:

```bash
cat deployments/production.current
```

4. Run smoke check:

```bash
make test-integration-smoke
```

5. Communicate incident status and rollback result in incident channel and issue tracker.

## Exit Criteria

- `deployments/production.current` equals known good release
- integration smoke passes
- rollback event logged in `logs/rollback-history.tsv`

#!/usr/bin/env bash
set -euo pipefail

env_name="${1:-}"
if [ -z "$env_name" ]; then
  echo "usage: $0 <staging|production>"
  exit 1
fi

if [ "$env_name" != "staging" ] && [ "$env_name" != "production" ]; then
  echo "invalid environment: $env_name"
  exit 1
fi

mkdir -p deployments logs
manifest="deployments/$env_name.current"
previous=""
if [ -f "$manifest" ]; then
  previous="$(cat "$manifest")"
fi

release_id="${env_name}-$(date -u +%Y%m%d%H%M%S)"
echo "$release_id" > "$manifest"

printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$env_name" "$release_id" "$previous" >> logs/deploy-history.tsv

artifact_dir="logs/releases/$release_id"
mkdir -p "$artifact_dir"
created_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
previous_display="${previous:-none}"

cat > "$artifact_dir/checklist.md" <<EOF
# Pre-release Checklist: $release_id

- Generated at (UTC): $created_at_utc
- Environment: \`$env_name\`
- Previous release: \`$previous_display\`

## Go/No-Go Criteria

- [ ] \`lint\`, \`unit-tests\`, and \`integration-smoke\` are green
- [ ] Required branch protection checks passed on \`main\`
- [ ] Rollback target verified and documented
- [ ] Known high-severity defects are assigned owner + same-day ETA
- [ ] UAT bug bash completed and logged

## Decision

- Decision: \`GO\` or \`NO-GO\`
- Decider:
- Decision time (UTC):
- Notes:
EOF

cat > "$artifact_dir/uat-results.md" <<EOF
# UAT Results: $release_id

## Weekly Cadence

- Slot: Every Thursday at 14:00 UTC (bug bash + acceptance sweep)
- Facilitator:
- Participants:

## Scenario Outcomes

| Scenario | Result | Notes |
| --- | --- | --- |
| Happy-path onboarding | pending | |
| Invite acceptance + RBAC | pending | |
| Regression sweep | pending | |

## Defect Summary

Reference: \`./defects.tsv\`
EOF

cat > "$artifact_dir/defects.tsv" <<'EOF'
# reported_at_utc	defect_id	severity	owner	eta_utc	status	summary
EOF

cat > "$artifact_dir/release-notes.md" <<EOF
# Release Notes: $release_id

- Environment: \`$env_name\`
- Previous release: \`$previous_display\`
- Generated at (UTC): $created_at_utc

## Quality Artifacts

- Checklist: [Pre-release checklist](./checklist.md)
- UAT results: [UAT results](./uat-results.md)
- Defects: [Defect log](./defects.tsv)
EOF

echo "deployed $env_name release $release_id"

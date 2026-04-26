#!/usr/bin/env bash
set -euo pipefail

owner_repo="${1:-}"
if [ -z "$owner_repo" ]; then
  echo "usage: $0 <owner/repo>"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required"
  exit 1
fi

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

cat > "$payload_file" <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "unit-tests", "integration-smoke", "release-quality-gates"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$owner_repo/branches/main/protection" \
  --input "$payload_file"

echo "branch protection updated for $owner_repo main"

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

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/$owner_repo/branches/main/protection" \
  -f required_status_checks.strict=true \
  -F required_status_checks.contexts[]='lint' \
  -F required_status_checks.contexts[]='unit-tests' \
  -F required_status_checks.contexts[]='integration-smoke' \
  -F required_status_checks.contexts[]='release-quality-gates' \
  -f enforce_admins=true \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f restrictions=

echo "branch protection updated for $owner_repo main"

# Branch Protection Setup

Apply these protection rules to the `main` branch:

- Require pull request before merge.
- Require at least one approval.
- Dismiss stale approvals when new commits are pushed.
- Require status checks to pass before merging.
- Required checks:
  - `lint`
  - `unit-tests`
  - `integration-smoke`
  - `release-quality-gates`
- Prevent force pushes.
- Prevent branch deletion.

## GitHub CLI Example

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/<owner>/<repo>/branches/main/protection \
  -f required_status_checks.strict=true \
  -F required_status_checks.contexts[]='lint' \
  -F required_status_checks.contexts[]='unit-tests' \
  -F required_status_checks.contexts[]='integration-smoke' \
  -F required_status_checks.contexts[]='release-quality-gates' \
  -f enforce_admins=true \
  -f required_pull_request_reviews.dismiss_stale_reviews=true \
  -f required_pull_request_reviews.required_approving_review_count=1 \
  -f restrictions=
```

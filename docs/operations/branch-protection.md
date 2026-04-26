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
cat > /tmp/main-branch-protection.json <<'JSON'
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
  /repos/<owner>/<repo>/branches/main/protection \
  --input /tmp/main-branch-protection.json
```

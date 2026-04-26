#!/usr/bin/env bash
set -euo pipefail

workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT

cp scripts/deploy.sh scripts/release-quality-gates.sh "$workspace/"
cd "$workspace"
mkdir -p deployments logs

./deploy.sh staging >/dev/null
./deploy.sh production >/dev/null

staging_release="$(cat deployments/staging.current)"
production_release="$(cat deployments/production.current)"

for release_id in "$staging_release" "$production_release"; do
  artifact_dir="logs/releases/$release_id"
  [ -f "$artifact_dir/checklist.md" ] || { echo "missing checklist for $release_id"; exit 1; }
  [ -f "$artifact_dir/release-notes.md" ] || { echo "missing release notes for $release_id"; exit 1; }
  [ -f "$artifact_dir/uat-results.md" ] || { echo "missing uat results for $release_id"; exit 1; }
  [ -f "$artifact_dir/defects.tsv" ] || { echo "missing defects log for $release_id"; exit 1; }
done

if ! grep -q '\./uat-results.md' "logs/releases/$staging_release/release-notes.md"; then
  echo "release notes missing uat link"
  exit 1
fi

reported_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
same_day_eta="${reported_at:0:10}T23:00:00Z"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$reported_at" \
  "DEF-100" \
  "high" \
  "qa-oncall" \
  "$same_day_eta" \
  "open" \
  "Critical onboarding regression" >> "logs/releases/$staging_release/defects.tsv"

./release-quality-gates.sh >/dev/null

printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$reported_at" \
  "DEF-101" \
  "high" \
  "" \
  "$same_day_eta" \
  "open" \
  "Missing owner should fail gate" >> "logs/releases/$production_release/defects.tsv"

if ./release-quality-gates.sh >/dev/null 2>&1; then
  echo "expected release quality gate failure for missing owner"
  exit 1
fi

echo "unit: release quality gates verified"

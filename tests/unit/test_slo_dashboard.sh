#!/usr/bin/env bash
set -euo pipefail

workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT

cp scripts/slo-dashboard.sh "$workspace/"
cd "$workspace"
mkdir -p data/slo logs/reliability

cat > data/slo/input.tsv <<'TSV'
# slo_id	core_journey	sli	target_pct	actual_pct	window_days	owner	pager_route
slo_ok	Healthy flow	99th percentile success	99.00	99.50	30	platform	pager-a
slo_bad	Breached flow	99th percentile success	99.00	97.90	30	platform	pager-b
TSV

./slo-dashboard.sh data/slo/input.tsv logs/reliability/out.md >/dev/null

if ! grep -q "Healthy SLOs: 1" logs/reliability/out.md; then
  echo "expected one healthy slo"
  exit 1
fi

if ! grep -q "Breached SLOs: 1" logs/reliability/out.md; then
  echo "expected one breached slo"
  exit 1
fi

if ! grep -q "\*\*breached\*\*" logs/reliability/out.md; then
  echo "expected breached status row"
  exit 1
fi

echo "unit: slo dashboard generation verified"

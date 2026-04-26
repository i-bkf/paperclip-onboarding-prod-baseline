#!/usr/bin/env bash
set -euo pipefail

workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT

cp scripts/slo-dashboard.sh scripts/reliability-alert-drill.sh "$workspace/"
cd "$workspace"
mkdir -p data/slo

cat > data/slo/drill.tsv <<'TSV'
# slo_id	core_journey	sli	target_pct	actual_pct	window_days	owner	pager_route
signup_request_success	Signup API availability	Successful responses	99.90	97.50	30	growth-oncall	pager-growth
activation_completion_rate	Activation completion	Activation conversion	90.00	90.20	30	product-oncall	pager-growth
TSV

./reliability-alert-drill.sh data/slo/drill.tsv smoke-drill >/dev/null

drill_dir="logs/reliability/drills/smoke-drill"
[ -f "$drill_dir/slo-dashboard.md" ] || { echo "missing drill dashboard"; exit 1; }
[ -f "$drill_dir/pager-alerts.tsv" ] || { echo "missing alerts file"; exit 1; }
[ -f "$drill_dir/incident-smoke-drill.md" ] || { echo "missing incident file"; exit 1; }
[ -f "$drill_dir/drill-summary.md" ] || { echo "missing summary file"; exit 1; }

alert_rows="$(grep -cv '^timestamp_utc' "$drill_dir/pager-alerts.tsv")"
if [ "$alert_rows" -lt 1 ]; then
  echo "expected at least one alert row"
  exit 1
fi

if ! grep -q "## Follow-up Actions" "$drill_dir/incident-smoke-drill.md"; then
  echo "incident file missing template section"
  exit 1
fi

echo "unit: reliability drill flow verified"

#!/usr/bin/env bash
set -euo pipefail

workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT

cp scripts/cost-budget-alerts.sh "$workspace/"
cd "$workspace"
mkdir -p data/cost logs/cost

cat > data/cost/thresholds.tsv <<'TSV'
# env	monthly_budget_usd	warning_threshold_pct	critical_threshold_pct	alert_route
staging	100	75	90	pager-platform
production	500	80	95	pager-finops
TSV

cat > data/cost/spend.tsv <<'TSV'
# env	month_utc	actual_spend_usd	forecast_spend_usd
staging	2026-04	45	82
production	2026-04	480	510
TSV

./cost-budget-alerts.sh data/cost/thresholds.tsv data/cost/spend.tsv logs/cost/out.md >/dev/null

if ! grep -q "Warning budgets: 1" logs/cost/out.md; then
  echo "expected one warning budget"
  exit 1
fi

if ! grep -q "Critical budgets: 1" logs/cost/out.md; then
  echo "expected one critical budget"
  exit 1
fi

if ! grep -q "\*\*warning\*\*" logs/cost/out.md; then
  echo "expected warning status row"
  exit 1
fi

if ! grep -q "\*\*critical\*\*" logs/cost/out.md; then
  echo "expected critical status row"
  exit 1
fi

echo "unit: cost budget alerts verified"

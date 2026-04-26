#!/usr/bin/env bash
set -euo pipefail

thresholds_path="${1:-data/cost/monthly-budget-thresholds.tsv}"
snapshot_path="${2:-data/cost/monthly-spend-snapshot.tsv}"
output_path="${3:-logs/cost/monthly-budget-alerts.md}"

if [ ! -f "$thresholds_path" ]; then
  echo "cost-budget-alerts: thresholds not found: $thresholds_path" >&2
  exit 1
fi

if [ ! -f "$snapshot_path" ]; then
  echo "cost-budget-alerts: spend snapshot not found: $snapshot_path" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_path")"

generated_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rows_file="$(mktemp)"
stats_file="$(mktemp)"
trap 'rm -f "$rows_file" "$stats_file"' EXIT

awk -F '\t' -v rows_file="$rows_file" -v stats_file="$stats_file" '
function is_skippable(v) {
  return v == "" || v ~ /^[[:space:]]*$/ || v ~ /^#/ || v == "env"
}
BEGIN {
  healthy = 0
  warning = 0
  critical = 0
  row_count = 0
}
FNR == NR {
  env_name = $1
  if (is_skippable(env_name)) {
    next
  }
  if ($2 == "" || $3 == "" || $4 == "" || $5 == "") {
    printf "cost-budget-alerts: invalid threshold row for env '\''%s'\''\n", env_name > "/dev/stderr"
    exit 1
  }
  threshold[env_name] = $2 "\t" $3 "\t" $4 "\t" $5
  threshold_count += 1
  next
}
{
  env_name = $1
  if (is_skippable(env_name)) {
    next
  }

  if ($2 == "" || $3 == "" || $4 == "") {
    printf "cost-budget-alerts: invalid spend row for env '\''%s'\''\n", env_name > "/dev/stderr"
    exit 1
  }

  if (!(env_name in threshold)) {
    printf "cost-budget-alerts: missing threshold configuration for env '\''%s'\''\n", env_name > "/dev/stderr"
    exit 1
  }

  split(threshold[env_name], config, "\t")
  budget_usd = config[1] + 0
  warning_pct = config[2] + 0
  critical_pct = config[3] + 0
  alert_route = config[4]

  month_utc = $2
  actual_spend_usd = $3 + 0
  forecast_spend_usd = $4 + 0

  actual_budget_pct = (actual_spend_usd / budget_usd) * 100
  forecast_budget_pct = (forecast_spend_usd / budget_usd) * 100
  forecast_remaining_usd = budget_usd - forecast_spend_usd

  status = "healthy"
  if (forecast_budget_pct >= critical_pct) {
    status = "critical"
    critical += 1
  } else if (forecast_budget_pct >= warning_pct) {
    status = "warning"
    warning += 1
  } else {
    healthy += 1
  }

  printf "| `%s` | `%s` | $%.2f | $%.2f | %.2f%% | %.2f%% | `%+.2f` | `%s` | **%s** |\n", \
    env_name, month_utc, budget_usd, forecast_spend_usd, actual_budget_pct, forecast_budget_pct, forecast_remaining_usd, alert_route, status >> rows_file

  row_count += 1
}
END {
  if (threshold_count == 0) {
    printf "cost-budget-alerts: no threshold rows found\n" > "/dev/stderr"
    exit 1
  }
  if (row_count == 0) {
    printf "cost-budget-alerts: no spend rows found\n" > "/dev/stderr"
    exit 1
  }
  printf "healthy=%d\nwarning=%d\ncritical=%d\nrows=%d\n", healthy, warning, critical, row_count > stats_file
}
' "$thresholds_path" "$snapshot_path"

# shellcheck disable=SC1090
source "$stats_file"

{
  echo "# Monthly Cost Guardrails"
  echo
  echo "- Generated at (UTC): $generated_at_utc"
  printf -- '- Threshold config: `%s`\n' "$thresholds_path"
  printf -- '- Spend snapshot: `%s`\n' "$snapshot_path"
  echo "- Healthy budgets: $healthy"
  echo "- Warning budgets: $warning"
  echo "- Critical budgets: $critical"
  echo
  echo "| Environment | Month | Budget | Forecast spend | Actual vs budget | Forecast vs budget | Forecast budget remaining | Alert route | Status |"
  echo "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
  cat "$rows_file"
} > "$output_path"

echo "cost budget alerts generated: $output_path"

#!/usr/bin/env bash
set -euo pipefail

snapshot_path="${1:-data/slo/sli-snapshot.tsv}"
output_path="${2:-logs/reliability/slo-dashboard.md}"

if [ ! -f "$snapshot_path" ]; then
  echo "slo-dashboard: snapshot not found: $snapshot_path" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_path")"

generated_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
healthy_count=0
breached_count=0
rows_file="$(mktemp)"
trap 'rm -f "$rows_file"' EXIT

while IFS=$'\t' read -r slo_id core_journey sli target_pct actual_pct window_days owner pager_route; do
  if [ -z "${slo_id// }" ] || [[ "$slo_id" == \#* ]] || [ "$slo_id" = "slo_id" ]; then
    continue
  fi

  if [ -z "$core_journey" ] || [ -z "$sli" ] || [ -z "$target_pct" ] || [ -z "$actual_pct" ] || [ -z "$window_days" ] || [ -z "$owner" ] || [ -z "$pager_route" ]; then
    echo "slo-dashboard: invalid row in $snapshot_path for $slo_id" >&2
    exit 1
  fi

  if awk -v actual="$actual_pct" -v target="$target_pct" 'BEGIN { exit !(actual + 0 >= target + 0) }'; then
    status="healthy"
    healthy_count=$((healthy_count + 1))
  else
    status="breached"
    breached_count=$((breached_count + 1))
  fi

  budget_remaining_pp="$(awk -v actual="$actual_pct" -v target="$target_pct" 'BEGIN { printf "%+.2f", actual - target }')"

  printf '| `%s` | %s | %s | %.2f%% | %.2f%% | %s | %sd | `%s` | `%s` | **%s** |\n' \
    "$slo_id" \
    "$core_journey" \
    "$sli" \
    "$target_pct" \
    "$actual_pct" \
    "$budget_remaining_pp" \
    "$window_days" \
    "$owner" \
    "$pager_route" \
    "$status" >> "$rows_file"
done < "$snapshot_path"

total=$((healthy_count + breached_count))
if [ "$total" -eq 0 ]; then
  echo "slo-dashboard: no SLO rows found in $snapshot_path" >&2
  exit 1
fi

{
  echo "# SLO Dashboard"
  echo
  echo "- Generated at (UTC): $generated_at_utc"
  printf -- '- Snapshot: `%s`\n' "$snapshot_path"
  echo "- Healthy SLOs: $healthy_count"
  echo "- Breached SLOs: $breached_count"
  echo
  echo "| SLO ID | Core journey | SLI | Target | Actual | Error budget remaining (pp) | Window | Owner | Pager route | Status |"
  echo "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
  cat "$rows_file"
} > "$output_path"

echo "slo-dashboard generated: $output_path"

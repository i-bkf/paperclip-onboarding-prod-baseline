#!/usr/bin/env bash
set -euo pipefail

snapshot_path="${1:-data/slo/drill-breach-sli-snapshot.tsv}"
drill_id="${2:-drill-$(date -u +%Y%m%d%H%M%S)}"

if [ ! -f "$snapshot_path" ]; then
  echo "reliability-alert-drill: snapshot not found: $snapshot_path" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dashboard_script="$script_dir/slo-dashboard.sh"
if [ ! -x "$dashboard_script" ]; then
  echo "reliability-alert-drill: missing executable $dashboard_script" >&2
  exit 1
fi

drill_dir="logs/reliability/drills/$drill_id"
mkdir -p "$drill_dir"

dashboard_path="$drill_dir/slo-dashboard.md"
alerts_path="$drill_dir/pager-alerts.tsv"
incident_path="$drill_dir/incident-$drill_id.md"
summary_path="$drill_dir/drill-summary.md"

"$dashboard_script" "$snapshot_path" "$dashboard_path" >/dev/null

generated_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

date_plus_days() {
  local days="$1"
  if date -u -v+"$days"d +%Y-%m-%d >/dev/null 2>&1; then
    date -u -v+"$days"d +%Y-%m-%d
    return
  fi
  date -u -d "+$days days" +%Y-%m-%d
}

echo -e "timestamp_utc\talert_id\tslo_id\tseverity\tpager_route\tstate\tmessage" > "$alerts_path"

breach_count=0
first_breached_slo=""
while IFS=$'\t' read -r slo_id core_journey sli target_pct actual_pct window_days owner pager_route; do
  if [ -z "${slo_id// }" ] || [[ "$slo_id" == \#* ]] || [ "$slo_id" = "slo_id" ]; then
    continue
  fi

  if awk -v actual="$actual_pct" -v target="$target_pct" 'BEGIN { exit !(actual + 0 < target + 0) }'; then
    breach_count=$((breach_count + 1))
    if [ -z "$first_breached_slo" ]; then
      first_breached_slo="$slo_id"
    fi

    gap_pp="$(awk -v actual="$actual_pct" -v target="$target_pct" 'BEGIN { printf "%.2f", target - actual }')"
    severity="high"
    if awk -v gap="$gap_pp" 'BEGIN { exit !(gap + 0 >= 1.00) }'; then
      severity="critical"
    fi

    alert_id="ALERT-${drill_id}-${breach_count}"
    message="$core_journey SLO breached by ${gap_pp}pp"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$generated_at_utc" \
      "$alert_id" \
      "$slo_id" \
      "$severity" \
      "$pager_route" \
      "fired" \
      "$message" >> "$alerts_path"
  fi
done < "$snapshot_path"

if [ "$breach_count" -eq 0 ]; then
  echo "reliability-alert-drill: no SLO breaches found in $snapshot_path" >&2
  exit 1
fi

incident_id="INC-$(date -u +%Y%m%d%H%M%S)-SLO-DRILL"

cat > "$incident_path" <<INCIDENT_EOF
# Incident Report: $incident_id

## Metadata

- Incident ID: $incident_id
- Severity: SEV-2 (drill)
- Status: resolved
- Started at (UTC): $generated_at_utc
- Commander: platform-oncall
- Communications channel: #incidents-simulated
- Detection source: Pager alert from SLO breach drill

## Impact

- Affected users/workspaces: simulated workspace cohort only
- User-visible symptoms: synthetic degradation for reliability rehearsal
- Current blast radius: simulation only

## Timeline (UTC)

- $(date -u +%H:%M) - Detection via pager alert
- $(date -u +%H:%M) - Incident declared
- $(date -u +%H:%M) - Mitigation started
- $(date -u +%H:%M) - Recovery validated

## Mitigation and Recovery

- Immediate mitigations: failover playbook walkthrough and rollback rehearsal
- Validation checks: dashboard regenerated and alerts acknowledged
- Recovery complete at (UTC): $generated_at_utc

## Root Cause

- Triggering change or condition: injected SLO regression for drill on \`$first_breached_slo\`
- Contributing factors: none (controlled simulation)

## Follow-up Actions

| Action | Owner | Due date (UTC) | Status |
| --- | --- | --- | --- |
| Increase alert annotation detail for on-call handoff | platform-oncall | $(date_plus_days 2) | open |
| Run next drill with cross-functional observers | growth-oncall | $(date_plus_days 7) | open |
INCIDENT_EOF

cat > "$summary_path" <<SUMMARY_EOF
# Reliability Drill Summary: $drill_id

- Drill started at (UTC): $generated_at_utc
- Input snapshot: \`$snapshot_path\`
- Breaches detected: $breach_count
- Pager flow: exercised and acknowledged
- Incident template: populated at \`$incident_path\`

## Artifacts

- Dashboard: [SLO dashboard](./slo-dashboard.md)
- Alerts: [Pager alerts](./pager-alerts.tsv)
- Incident report: [Incident report](./incident-$drill_id.md)
SUMMARY_EOF

echo "reliability drill complete: $drill_dir"

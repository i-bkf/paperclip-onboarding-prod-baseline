#!/usr/bin/env bash
set -euo pipefail

status=0

trim() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

is_high_severity() {
  local severity
  severity="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$severity" in
    high|critical|sev1|sev-1|p0|p1)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

fail() {
  local message="$1"
  echo "release quality gate failed: $message" >&2
  status=1
}

validate_release() {
  local release_id="$1"
  local artifact_dir="logs/releases/$release_id"
  local checklist="$artifact_dir/checklist.md"
  local release_notes="$artifact_dir/release-notes.md"
  local uat_results="$artifact_dir/uat-results.md"
  local defects_log="$artifact_dir/defects.tsv"

  if [ ! -d "$artifact_dir" ]; then
    fail "missing artifact directory for release $release_id"
    return
  fi
  [ -f "$checklist" ] || fail "missing checklist artifact for release $release_id"
  [ -f "$release_notes" ] || fail "missing release notes artifact for release $release_id"
  [ -f "$uat_results" ] || fail "missing uat results artifact for release $release_id"
  [ -f "$defects_log" ] || fail "missing defects artifact for release $release_id"

  if [ -f "$release_notes" ] && ! grep -q '\./uat-results.md' "$release_notes"; then
    fail "release notes for $release_id do not link to uat results"
  fi

  if [ -f "$defects_log" ]; then
    local line_number=0
    while IFS=$'\t' read -r reported_at defect_id severity owner eta_utc defect_status summary; do
      line_number=$((line_number + 1))

      if [ -z "${reported_at// }" ] || [[ "$reported_at" == \#* ]]; then
        continue
      fi

      local severity_clean owner_clean eta_clean
      severity_clean="$(trim "$severity")"
      owner_clean="$(trim "$owner")"
      eta_clean="$(trim "$eta_utc")"

      if is_high_severity "$severity_clean"; then
        if [ -z "$owner_clean" ]; then
          fail "high severity defect without owner ($release_id:$line_number)"
        fi
        if [ -z "$eta_clean" ]; then
          fail "high severity defect without eta ($release_id:$line_number)"
        fi

        local reported_day eta_day
        reported_day="${reported_at:0:10}"
        eta_day="${eta_clean:0:10}"
        if [ "$reported_day" != "$eta_day" ]; then
          fail "high severity defect eta is not same-day ($release_id:$line_number)"
        fi
      fi
    done < "$defects_log"
  fi
}

for env_name in staging production; do
  manifest="deployments/$env_name.current"
  if [ ! -f "$manifest" ]; then
    continue
  fi

  release_id="$(tr -d '\n' < "$manifest")"
  if [ -z "$release_id" ]; then
    fail "manifest $manifest is empty"
    continue
  fi
  validate_release "$release_id"
done

if [ "$status" -ne 0 ]; then
  exit "$status"
fi

echo "release quality gates passed"

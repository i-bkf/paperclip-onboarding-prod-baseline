#!/usr/bin/env bash
set -euo pipefail

env_name="${1:-}"
target_release="${2:-}"

if [ -z "$env_name" ] || [ -z "$target_release" ]; then
  echo "usage: $0 <staging|production> <release-id>"
  exit 1
fi

manifest="deployments/$env_name.current"
if [ ! -f "$manifest" ]; then
  echo "no current release found for $env_name"
  exit 1
fi

current_release="$(cat "$manifest")"
echo "$target_release" > "$manifest"

mkdir -p logs
printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$env_name" "$current_release" "$target_release" >> logs/rollback-history.tsv

echo "rolled back $env_name from $current_release to $target_release"

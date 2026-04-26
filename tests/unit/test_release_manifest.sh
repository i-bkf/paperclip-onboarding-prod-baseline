#!/usr/bin/env bash
set -euo pipefail

workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT

cp scripts/deploy.sh scripts/rollback.sh "$workspace/"
cd "$workspace"
mkdir -p deployments logs

./deploy.sh staging >/dev/null
release_a="$(cat deployments/staging.current)"

sleep 1
./deploy.sh staging >/dev/null
release_b="$(cat deployments/staging.current)"

if [ "$release_a" = "$release_b" ]; then
  echo "expected a new release id on second deploy"
  exit 1
fi

./rollback.sh staging "$release_a" >/dev/null
release_after_rollback="$(cat deployments/staging.current)"

if [ "$release_after_rollback" != "$release_a" ]; then
  echo "rollback did not set manifest to target release"
  exit 1
fi

echo "unit: release manifest behavior verified"

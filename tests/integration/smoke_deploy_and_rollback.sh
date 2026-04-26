#!/usr/bin/env bash
set -euo pipefail

rm -f deployments/staging.current deployments/production.current
mkdir -p deployments logs

./scripts/deploy.sh staging >/dev/null
staging_release="$(cat deployments/staging.current)"

sleep 1
./scripts/deploy.sh production >/dev/null
production_release_a="$(cat deployments/production.current)"

sleep 1
./scripts/deploy.sh production >/dev/null
production_release_b="$(cat deployments/production.current)"

./scripts/rollback.sh production "$production_release_a" >/dev/null
production_after_rollback="$(cat deployments/production.current)"

if [ "$production_after_rollback" != "$production_release_a" ]; then
  echo "integration smoke failed: rollback target not active"
  exit 1
fi

if [ "$production_release_a" = "$production_release_b" ]; then
  echo "integration smoke failed: production release id did not change"
  exit 1
fi

echo "integration: staging release=$staging_release production rollback=$production_after_rollback"

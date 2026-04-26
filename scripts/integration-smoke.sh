#!/usr/bin/env bash
set -euo pipefail

./tests/integration/smoke_deploy_and_rollback.sh
python3 -m unittest discover -s tests/integration -p 'test_*.py'

echo "integration smoke passed"

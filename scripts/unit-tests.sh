#!/usr/bin/env bash
set -euo pipefail

./tests/unit/test_release_manifest.sh
./tests/unit/test_slo_dashboard.sh
./tests/unit/test_reliability_alert_drill.sh
./tests/unit/test_cost_budget_alerts.sh
python3 -m unittest discover -s tests/unit -p 'test_*.py'

echo "unit tests passed"

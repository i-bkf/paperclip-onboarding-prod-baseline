SHELL := /bin/bash

.PHONY: lint test-unit test-integration-smoke quality-gates ci deploy-staging deploy-production rollback bootstrap-local migrate slo-dashboard reliability-drill cost-alerts

lint:
	./scripts/lint.sh

test-unit:
	./scripts/unit-tests.sh

test-integration-smoke:
	./scripts/integration-smoke.sh

quality-gates:
	./tests/unit/test_release_quality_gates.sh

ci: lint test-unit test-integration-smoke quality-gates

deploy-staging:
	./scripts/deploy.sh staging

deploy-production:
	./scripts/deploy.sh production

rollback:
	@if [ -z "$$TARGET_ENV" ] || [ -z "$$RELEASE_ID" ]; then \
		echo "Usage: make rollback TARGET_ENV=<staging|production> RELEASE_ID=<release-id>"; \
		exit 1; \
	fi
	./scripts/rollback.sh "$$TARGET_ENV" "$$RELEASE_ID"

bootstrap-local:
	./scripts/bootstrap-local-dev.sh

migrate:
	./scripts/migrate.sh

slo-dashboard:
	./scripts/slo-dashboard.sh

reliability-drill:
	./scripts/reliability-alert-drill.sh

cost-alerts:
	./scripts/cost-budget-alerts.sh

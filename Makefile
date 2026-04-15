.PHONY: help app-up app-down app-logs docs-up docs-down docs-logs clean

.DEFAULT_GOAL := help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'


# ── AuthGate (app) ──────────────────────────────────────────────
# Uses the root docker-compose.yml → pulls the published image,
# bundled Postgres, zero-config. For local contributor builds, see
# deployments/docker-compose/docker-compose.yml (run manually).

app-up: ## Start AuthGate + Postgres (published image, localhost:8000)
	docker compose up -d

app-down: ## Stop AuthGate (volumes preserved — DB data survives)
	docker compose down

app-logs: ## Tail AuthGate container logs
	docker compose logs -f authgate


# ── Docs site ───────────────────────────────────────────────────

docs-up: ## Start docs dev server (localhost:4321/authgate/)
	cd docs && docker compose up -d

docs-down: ## Stop docs container
	cd docs && docker compose down

docs-logs: ## Tail docs container logs
	cd docs && docker compose logs -f docs


# ── Nuclear clean ───────────────────────────────────────────────
# Wipes containers, volumes, caches, local keys for BOTH stacks.
# Postgres data and JWT keys are destroyed. Re-running app-up will
# generate fresh keys and an empty DB.

clean: ## Wipe everything — containers, volumes, caches, keys, lockfiles
	docker compose down -v --remove-orphans 2>/dev/null || true
	cd docs && docker compose down -v --remove-orphans 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf keys/
	rm -f docs/package-lock.json

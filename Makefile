# One-command tasks for contributors. Run `make help`.
# Needs uv (https://docs.astral.sh/uv/) and Node 22.

PY := cd python && uv run --no-sync
.DEFAULT_GOAL := help

.PHONY: help setup lint test test-py test-js build example e2e clean

help: ## List the tasks
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

setup: ## Install Python and JS dependencies and the pre-commit hook
	cd python && uv venv --allow-existing && uv pip install -e '.[test,dev]' -r ../tests/example-course/requirements.txt
	cd js && npm ci --no-audit --no-fund
	cd python && uv run pre-commit install --config ../.pre-commit-config.yaml

lint: ## Ruff (Python) and Biome (JS)
	python/.venv/bin/ruff check python/src tests
	cd js && npm run lint

build: ## Build the JS bundle (release build, as published)
	cd js && npm run build

test-py: ## Python unit tests
	$(PY) pytest -q ../tests/python

test-js: build ## JS unit tests (rebuilds first: tests read dist/)
	cd js && npm test

test: lint test-py test-js ## Lint and all unit tests (what CI runs first)

example: ## Build tests/example-course with the dev bundle
	cd js && npm run build:dev
	tests/scripts/build-example.sh

e2e: ## Browser tests against a built example course (see AGENTS.md)
	@echo "Serve tests/example-course/_build/html on :8765, then:"
	@echo "  NMA_E2E_URL=http://localhost:8765 python/.venv/bin/pytest -q --reruns 1 -n 4 tests/e2e"

clean: ## Remove build output and caches
	rm -rf js/dist python/dist tests/example-course/_build tests/example-course/_nma .pytest_cache .ruff_cache

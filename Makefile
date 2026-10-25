# One-command tasks for contributors. Run `make help`.
# Needs uv (https://docs.astral.sh/uv/) and Node (see .tool-versions).

PY := cd python && uv run --no-sync
.DEFAULT_GOAL := help

.PHONY: help setup lint test test-py test-js build build-dev dist dist-py dist-js example e2e clean sync-templates

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

build-dev: ## Build the JS bundle for local use (asset paths next to the bundle)
	cd js && npm run build:dev

test-js: ## JS unit tests against both builds (tests read dist/, so it rebuilds; ends on the release build)
	cd js && npm run build:dev && npm test
	cd js && npm run build && npm test

dist-py: ## Build the wheel and sdist into dist/ (what the release publishes to PyPI)
	uv build --out-dir dist python

dist-js: build ## Build the release bundle and pack the npm tarball into dist/ (npm publishes from js/)
	mkdir -p dist
	cd js && npm pack --pack-destination ../dist

dist: ## Build every release artifact into dist/ without publishing
	rm -rf dist
	@$(MAKE) --no-print-directory dist-py dist-js
	@ls -1 dist

test: lint test-py test-js ## Lint and all unit tests (what CI runs first)

example: ## Build tests/example-course with the dev bundle (the script builds the bundle)
	tests/scripts/build-example.sh

e2e: ## Browser tests against a built example course (see AGENTS.md)
	@echo "Serve tests/example-course/_build/html on :8765, then:"
	@echo "  NMA_E2E_URL=http://localhost:8765 python/.venv/bin/pytest -q --reruns 1 -n 4 tests/e2e"

sync-templates: ## Copy templates/*.yml into the Python package (the wheel can't ship files outside python/)
	mkdir -p python/src/nma_kit/templates/workflows
	cp templates/*.yml python/src/nma_kit/templates/workflows/

clean: ## Remove build output and caches
	rm -rf dist js/dist python/dist tests/example-course/_build tests/example-course/_nma .pytest_cache .ruff_cache

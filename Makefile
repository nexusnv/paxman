# Paxman Makefile
# Run `make help` for the full list of targets.
#
# Conventions:
# - Every target is .PHONY (no file collisions)
# - `make help` is the discovery entry point
# - `make ci` is the local-CI simulation (used by .github/workflows/ci.yml)

# Use bash explicitly (not /bin/sh) so pipefail and errexit work.
SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

# Detect uv (preferred) or fall back to plain python.
UV ?= uv
PYTHON ?= python3

.DEFAULT_GOAL := help

# --- Discovery ----------------------------------------------------------------

.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "; printf "Usage: make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# --- Install ------------------------------------------------------------------

.PHONY: install
install: ## Install package + dev dependencies (editable)
	$(UV) sync --all-extras --dev

.PHONY: install-frozen
install-frozen: ## Install with the exact lockfile (CI use)
	$(UV) sync --frozen --all-extras --dev

# --- Test ---------------------------------------------------------------------

.PHONY: test
test: ## Run all tests
	$(UV) run pytest

.PHONY: test-unit
test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit

.PHONY: test-integration
test-integration: ## Run integration tests only
	$(UV) run pytest tests/integration

.PHONY: test-property
test-property: ## Run hypothesis property tests only
	$(UV) run pytest -m property

.PHONY: test-public-api
test-public-api: ## Run public API snapshot tests
	$(UV) run pytest tests/public_api

.PHONY: test-cov
test-cov: ## Run tests with coverage
	$(UV) run pytest --cov=paxman --cov-report=term-missing --cov-report=xml --cov-report=json

.PHONY: check-coverage
check-coverage: ## Verify per-subsystem coverage thresholds (D7.15)
	$(UV) run python scripts/check_subsystem_coverage.py

# --- Lint + format ------------------------------------------------------------

.PHONY: lint
lint: ## Run ruff check
	$(UV) run ruff check .

.PHONY: lint-fix
lint-fix: ## Run ruff check with autofixes
	$(UV) run ruff check --fix .

.PHONY: format
format: ## Run ruff format
	$(UV) run ruff format .

.PHONY: format-check
format-check: ## Run ruff format --check (CI use)
	$(UV) run ruff format --check .

# --- Type check ---------------------------------------------------------------

.PHONY: typecheck
typecheck: ## Run mypy --strict
	$(UV) run mypy --strict src/paxman

.PHONY: typecheck-pyright
typecheck-pyright: ## Run pyright for cross-validation
	$(UV) run pyright src/paxman

# --- Import-linter ------------------------------------------------------------

.PHONY: imports
imports: ## Run import-linter (module DAG enforcement)
	$(UV) run lint-imports

# --- Docstring coverage -------------------------------------------------------

.PHONY: docs-check
docs-check: ## Run interrogate (100% docstring coverage on public surface)
	$(UV) run interrogate -vv src/paxman

# --- Security -----------------------------------------------------------------

.PHONY: security
security: ## Run bandit
	$(UV) run bandit -r src/paxman -c pyproject.toml

.PHONY: security-audit
security-audit: ## Run bandit + pip-audit (full dependency audit)
	$(UV) run bandit -r src/paxman -c pyproject.toml
	$(UV) run pip-audit

# --- Benchmark + Profile (Sprint 9, D9.17) -----------------------------------

.PHONY: benchmark
benchmark: ## Run performance benchmarks (pytest-benchmark)
	$(UV) run pytest tests/benchmark/ --benchmark-only --benchmark-sort=median --benchmark-min-rounds=10 --benchmark-warmup=3

.PHONY: benchmark-quick
benchmark-quick: ## Run performance benchmarks with fewer rounds (for dev)
	$(UV) run pytest tests/benchmark/ --benchmark-only --benchmark-sort=median --benchmark-min-rounds=3 --benchmark-warmup=1

.PHONY: profile
profile: ## Run cold-import and CPU profiling
	$(UV) run python scripts/benchmark_import_time.py --iterations 20

# --- Test data (Sprint 5+) ---------------------------------------------------

.PHONY: test-data-vendor
test-data-vendor: ## Vendor the V1 test data corpus (~50 MB)
	$(UV) run python scripts/fetch_test_data.py

.PHONY: test-data-list
test-data-list: ## List vendored datasets and licenses
	$(UV) run python scripts/fetch_test_data.py --list

.PHONY: test-data-verify
test-data-verify: ## Verify vendored data is present (CI use)
	$(UV) run python scripts/fetch_test_data.py --verify

# --- Documentation build (Sprint 8) ------------------------------------------

.PHONY: docs
docs: ## Build documentation
	@echo "TODO(Sprint 8): build docs"

# --- Build --------------------------------------------------------------------

.PHONY: build
build: ## Build wheel and sdist (hatchling)
	$(UV) run hatchling build

.PHONY: build-verify
build-verify: build ## Build and verify wheel contents (py.typed present, no __pycache__)
	@$(UV) run python -c "import zipfile, sys; \
		wheel = [f for f in __import__('pathlib').Path('dist').glob('*.whl')][0]; \
		contents = zipfile.ZipFile(wheel).namelist(); \
		assert any('paxman/__init__.py' in c for c in contents), 'paxman/__init__.py missing from wheel'; \
		assert any('paxman/py.typed' in c for c in contents), 'paxman/py.typed missing from wheel'; \
		assert not any('__pycache__' in c for c in contents), '__pycache__ found in wheel'; \
		print(f'OK: {wheel.name} has {len(contents)} entries')"

# --- Clean --------------------------------------------------------------------

.PHONY: clean
clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info src/*.egg-info .pytest_cache/ .mypy_cache/ .ruff_cache/ .coverage htmlcov/

.PHONY: clean-all
clean-all: clean ## Remove build artifacts + venv
	rm -rf .venv/

# --- Publish (Sprint 9/10) ----------------------------------------------------

.PHONY: publish-test
publish-test: ## Publish to TestPyPI
	@echo "TODO(Sprint 10): publish to TestPyPI via trusted publishing"

.PHONY: publish
publish: ## Publish to PyPI
	@echo "TODO(Sprint 10): publish to PyPI via trusted publishing"

# --- Local CI simulation (the canonical "is this green?" command) -----------

# 9 checks (per Sprint 8 D8.25 / V1_ACCEPTANCE_CRITERIA.md §3.2):
#   1. install-frozen     — exact lockfile install
#   2. lint               — ruff check
#   3. format-check       — ruff format --check
#   4. typecheck          — mypy --strict
#   5. typecheck-pyright  — pyright (advisory in CI)
#   6. imports            — import-linter
#   7. docs-check         — interrogate (100% docstring coverage on public surface)
#   8. security           — bandit (advisory in CI)
#   9. test-cov           — pytest with coverage + per-subsystem threshold check

.PHONY: ci
ci: install-frozen lint format-check typecheck typecheck-pyright imports docs-check security test-cov ## Run the full local-CI pipeline (9 checks: install → lint → format → typecheck → pyright → imports → docs → security → test-cov)
	@echo ""
	@echo "=========================================="
	@echo "  CI GREEN ✓ (9 checks)"
	@echo "=========================================="

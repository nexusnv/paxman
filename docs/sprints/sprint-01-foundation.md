# Sprint 1 — Foundation

> **Duration:** 2 weeks
> **Goal:** Stand up the **build, CI, and cross-cutting foundations** so that Sprint 2 can begin implementing the contract subsystem without any further scaffolding.
> **Status:** First sprint with source code. **Hard gate: nothing can ship to PyPI from this sprint** — the package is `0.0.0` and not importable by end users.

## Scope (in)

- `pyproject.toml` (PEP 621, hatchling backend, all tooling config inline)
- `src/paxman/` skeleton with all subdirectories
- All 9 cross-cutting modules at the package root (`errors.py`, `types.py`, `protocols.py`, `versioning.py`, `logging.py`, `budget.py`, `clock.py`, `ids.py`, `serialization.py`)
- `src/paxman/py.typed` (PEP 561 marker, empty file)
- `src/paxman/__init__.py` (empty re-export shell — populated in Sprint 6)
- `Makefile` (all targets per `DEVELOPMENT.md` §4)
- `.pre-commit-config.yaml` (ruff, ruff format, mypy, standard hygiene hooks)
- `.gitignore` (Python + `dist/` + `build/` + `.venv/` + `tests/fixtures/generated/`)
- `LICENSE` (decision from Sprint 0)
- `CHANGELOG.md` (Keep a Changelog format, empty `[Unreleased]`)
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- Test infrastructure skeleton: `tests/conftest.py`, `pyproject.toml` `[tool.pytest.ini_options]`
- First smoke test: `tests/test_smoke.py` that imports `paxman` and asserts the version string

## Scope (out)

- **No subsystem code** (no `contract/`, no `planner/`, no `executor/`, etc.). Those start in Sprint 2.
- **No adapter implementations** (no Pydantic adapter, etc.).
- **No capabilities** (no `regex_extraction`, etc.).
- **No public API beyond `__version__`**.
- **No `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, or issue templates.** Those land in Sprint 8.

## Deliverables

| ID | Deliverable | Location | Effort (id-ed) |
|---|---|---|---|
| D1.1 | `pyproject.toml` with `[build-system]`, `[project]`, `[project.optional-dependencies]`, `[tool.hatch]`, `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest]`, `[tool.importlinter]` (empty), `[tool.interrogate]`, `[tool.coverage]` | repo root | 2.0 |
| D1.2 | `Makefile` with all targets from `DEVELOPMENT.md` §4 | repo root | 1.0 |
| D1.3 | `.pre-commit-config.yaml` with ruff, ruff format, mypy, hygiene hooks | repo root | 0.5 |
| D1.4 | `.gitignore` (Python + generated + dist + .venv) | repo root | 0.2 |
| D1.5 | `LICENSE` (MIT or Apache-2.0 per Sprint 0) | repo root | 0.1 |
| D1.6 | `CHANGELOG.md` (Keep a Changelog, empty Unreleased) | repo root | 0.3 |
| D1.7 | `src/paxman/` directory tree (all 7 subsystem dirs + cross-cutting) | `src/paxman/` | 0.2 |
| D1.8 | `src/paxman/py.typed` (empty) | `src/paxman/py.typed` | 0.1 |
| D1.9 | `src/paxman/__init__.py` (version only) | `src/paxman/__init__.py` | 0.2 |
| D1.10 | `src/paxman/errors.py` (PaxmanError hierarchy, **17 classes** per `ARCHITECTURE.md` §6.2: base + 4 InvalidContractError children + 3 ExecutionError children + 2 ReplayError children + 2 ConfigurationError children; the 11 listed in `V1_ACCEPTANCE_CRITERIA.md` §1.4 are the *public* subset re-exported in `api/errors.py`) | `src/paxman/errors.py` | 3.0 |

> **Editorial note (2026-06-26):** Sprint 6 added an 18th class, `CapabilityNotFoundError`, per `V1_ACCEPTANCE_CRITERIA.md` §1.5 (see `docs/sprints/CHANGES_LOG.md` C1). The 11-vs-12 public subset accordingly became 12. The current source of truth is `src/paxman/errors.py` (`__all__`) and `src/paxman/api/errors.py`. The "17 classes" wording above is preserved as the Sprint 1 baseline; do not treat it as a current contract.
| D1.11 | `src/paxman/types.py` (shared enums: `Status`, `ConfidenceBand`, `FieldType`) | `src/paxman/types.py` | 1.0 |
| D1.12 | `src/paxman/protocols.py` (internal Protocols) | `src/paxman/protocols.py` | 1.0 |
| D1.13 | `src/paxman/versioning.py` (version constants, helpers; 100% test coverage) | `src/paxman/versioning.py` | 2.0 |
| D1.14 | `src/paxman/logging.py` (structlog factory, no timestamps in replay path) | `src/paxman/logging.py` | 2.0 |
| D1.15 | `src/paxman/budget.py` (`Budget`, `Policy`, `CurrencyPolicy` attrs models) | `src/paxman/budget.py` | 2.0 |
| D1.16 | `src/paxman/clock.py` (injectable `Clock`; `FakeClock` test fixture) | `src/paxman/clock.py` | 1.0 |
| D1.17 | `src/paxman/ids.py` (prefixed IDs: `field_`, `cap_`, `art_`, `plan_`) | `src/paxman/ids.py` | 1.0 |
| D1.18 | `src/paxman/serialization.py` (stable JSON encoder, RFC 8785-style) | `src/paxman/serialization.py` | 2.0 |
| D1.19 | `tests/conftest.py` (top-level pytest config, markers) | `tests/conftest.py` | 0.5 |
| D1.20 | `tests/test_smoke.py` (imports `paxman`, asserts `__version__` is a string) | `tests/test_smoke.py` | 0.2 |
| D1.21 | `.github/workflows/ci.yml` (lint, format, typecheck, import-linter, test, interrogate, bandit, pip-audit on py311/3.12/3.13 matrix) | `.github/workflows/ci.yml` | 2.0 |
| D1.22 | `README.md` smoke section: `pip install -e .` + `paxman.__version__` | update `README.md` | 0.3 |
| D1.23 | First passing CI run on `main` | GitHub Actions UI | — |

**Total: ~22.6 id-ed.** Sprint 1 is sized for **2 engineers × 2 weeks** (16 id-ed each ≈ 32 id-ed) with a 30% buffer for the inherent friction of greenfield setup (CI debugging, lockfile issues, cross-platform smoke).

## Prerequisites (must be ready before Sprint 1 starts)

| Type | Item | Notes |
|---|---|---|
| **People** | 2 engineers (1 senior, 1 mid-level) | Full-time for 2 weeks |
| **Decisions** | Sprint 0 deliverables (license ADR, Dict DSL spec, Input Profile spec, CostHint values) | All decisions made |
| **Accounts** | GitHub repository admin access; PyPI account created (no publish yet) | For OIDC setup in Sprint 9 |
| **Tools** | Python 3.11, 3.12, 3.13 installed locally on all dev machines; `uv` installed; `pre-commit` available; `git` configured with name/email | Standard Python dev environment |
| **Cloud/Infra** | GitHub Actions minutes available (free tier: 2,000 min/month — sufficient) | No paid CI in V1 |
| **Docs** | `V1_ACCEPTANCE_CRITERIA.md` §2.1, §2.3, §3.1, §3.2 | Reference for tooling config |

## Tooling / applications / libraries

| Tool | Version constraint | Purpose | Where configured |
|---|---|---|---|
| **Python** | ≥ 3.11 (support 3.11, 3.12, 3.13) | Runtime | CI matrix; `pyproject.toml` `requires-python` |
| **uv** | latest stable | Package manager + venv | Installed via `astral.sh/uv/install.sh` |
| **hatchling** | latest | Build backend | `pyproject.toml` `[build-system]` |
| **ruff** | ≥ 0.4 (latest stable) | Lint + format | `pyproject.toml` `[tool.ruff]` + `.pre-commit-config.yaml` |
| **mypy** | ≥ 1.10 (latest stable) | Type check (strict) | `pyproject.toml` `[tool.mypy]` + `.pre-commit-config.yaml` |
| **pyright** | ≥ 1.1 (latest stable) | Type check (cross-validation) | `pyrightconfig.json` (Sprint 8) |
| **pytest** | ≥ 7.4 | Test runner | `pyproject.toml` `[tool.pytest]` |
| **pytest-cov** | ≥ 4.1 | Coverage (≥90% required) | `pyproject.toml` `[tool.coverage]` |
| **hypothesis** | ≥ 6.0 | Property-based testing | `pyproject.toml` `[project.optional-dependencies.test]` (Sprint 2+) |
| **attrs** | ≥ 23.0 | Core data classes | `pyproject.toml` `dependencies` |
| **typing-extensions** | ≥ 4.0 | Type hint backport | `pyproject.toml` `dependencies` |
| **structlog** | ≥ 24.1 | Structured logging | `pyproject.toml` `dependencies` |
| **import-linter** | ≥ 2.0 | Module DAG enforcement | dev dependency |
| **interrogate** | ≥ 1.7 | Docstring coverage (100% on public) | dev dependency |
| **bandit** | latest | Security lint | dev dependency |
| **pip-audit** | latest | Dependency vulnerability scan | dev dependency |
| **pre-commit** | latest | Git hooks | dev dependency |
| **GitHub Actions** | hosted ubuntu-latest runners | CI | `.github/workflows/ci.yml` |

## API keys / secrets

None required for Sprint 1. **OIDC trusted publishing** for PyPI is configured in Sprint 9, not Sprint 1.

## Exit criteria

1. `pip install -e .[dev]` works on a clean machine (Python 3.11, 3.12, 3.13).
2. `make ci` runs end-to-end and is green: `install → lint → format → typecheck → imports → test-cov`.
3. `ruff check` is clean with the rule set `E,F,W,I,B,UP,ANN,ASYNC,S,RUF`.
4. `ruff format --check` is clean (run after a one-time `ruff format` to normalize the codebase).
5. `mypy --strict src/paxman` is clean.
6. `pytest` runs and the smoke test passes.
7. `interrogate src/paxman` reports 100% docstring coverage on the public surface (currently empty, but the gate must be set up).
8. GitHub Actions CI runs on the first PR and on `main` and is green.
9. `import paxman` works; `paxman.__version__` returns a string.
10. The `errors.py` module has **17 exception classes** per `ARCHITECTURE.md` §6.2 (1 base + 16 subclasses) and the test `test_errors.py` covers every error path (target: 100% line coverage on `errors.py`). The 11 classes re-exported via `api/errors.py` (Sprint 6) are the public subset per `V1_ACCEPTANCE_CRITERIA.md` §1.4.
11. `versioning.py` has 100% line coverage (V1 acceptance criterion §2.2).
12. The `LICENSE` file is present and matches the Sprint 0 decision.
13. The package can be built: `make build` produces `dist/paxman-0.0.0.tar.gz` and `dist/paxman-0.0.0-py3-none-any.whl` (the wheel is **not** published yet — just built locally to verify the build backend works).
14. `make build` output is inspectable: `unzip -l dist/paxman-*.whl` shows `paxman/__init__.py` and `paxman/py.typed` present, no `__pycache__`.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `hatchling` config has a subtle bug (e.g., `py.typed` not in wheel) | Medium | High | Sprint 1 must include a manual `unzip -l dist/...` verification (D1.14, exit criterion #14). If hatchling is found unfit, switch to **`flit-core`** (per Oracle review M3 — smaller, simpler, also PEP 517-compliant) rather than `setuptools`. |
| `mypy --strict` on empty modules generates confusing errors | Low | Low | Set `[[tool.mypy.overrides]] module = ["src/paxman/errors.py"] strict = true` etc. as modules are added. |
| `import-linter` config is too strict and blocks legitimate cross-cutting imports | Low | Medium | Start with one minimal contract: cross-cutting modules may not import from subsystems. Add subsystem-specific contracts in Sprint 2. |
| `interrogate` 100% gate is too strict for `__init__.py` re-exports | Low | Low | Exclude `__init__.py` from interrogate (it documents via the symbols it re-exports). |
| Cross-platform CI matrix takes >5 min per run | Medium | Low | Use `astral-sh/setup-uv` cache; pin exact Python patch versions; restrict to 3.11, 3.12, 3.13 (drop 3.10 which is EOL). |
| `attrs` vs `pydantic` confusion for cross-cutting models | Low | Low | Document in the docstring of each model class why `attrs` was chosen. See `DEPENDENCIES.md`. |
| The first PR is rejected by maintainers for style/structure | Low | Medium | Pre-brief the team on the ADR-driven workflow before Sprint 1 starts. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §2.1, §2.3, §3.1, §3.2 — quality and packaging criteria.
- `../DEVELOPMENT.md` §2, §4, §6, §7 — environment, Makefile, linting, import-linter.
- `../DEPENDENCIES.md` — core dependency policy.
- `../ARCHITECTURE.md` §6.2 — `PaxmanError` exception hierarchy.
- `../PACKAGE_STRUCTURE.md` §10, §17 — cross-cutting modules, build config.
- `../docs/adr/0005-confidence-ownership.md` — `ConfidenceBand` enum.

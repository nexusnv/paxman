# Development Guide

> **Status:** Draft v1.
> **Audience:** Paxman contributors and maintainers.
> **Related docs:** [TESTING_STRATEGY.md](./testing-strategy.md), [PACKAGE_STRUCTURE.md §17 Build and Packaging Strategy](../reference/package-structure.md), [EXTENDING.md](../reference/extending.md)

This document describes how to set up a Paxman development environment, run the test suite, build the package, and contribute.

---

## 1. Prerequisites

- **Python:** ≥ 3.11
- **Git:** for version control
- **uv** (recommended) or **pip** for package management
- **pre-commit** for git hooks
- **make** for running the common task runner (the repo ships a `Makefile`)

---

## 2. Setting Up the Environment

### 2.1 Clone the repository

```bash
git clone https://github.com/paxman/paxman.git
cd paxman
```

### 2.2 Install uv (recommended)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

uv is a fast Python package manager that respects PEP 621 `pyproject.toml` and PEP 735 dependency groups.

### 2.3 Create a virtual environment and install dev dependencies

```bash
uv venv
uv sync --all-extras --dev
source .venv/bin/activate
```

This installs:

- All runtime dependencies (Pydantic, etc., as optional extras).
- All dev dependencies (pytest, ruff, mypy, pyright, import-linter, hypothesis, etc.).

### 2.4 Install pre-commit hooks

```bash
uv run pre-commit install
```

The pre-commit hooks run `ruff`, `ruff format`, and a few other checks on every commit.

### 2.5 Verify the install

```bash
uv run pytest --co -q          # collect tests, don't run
uv run ruff check              # lint
uv run ruff format --check     # format
uv run mypy --strict src/paxman
```

---

## 3. Repository Layout

```text
paxman/
├── src/
│   └── paxman/            # the package
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   ├── fixtures/          # test data: contracts, inputs, golden artifacts (see tests/fixtures/README.md)
│   └── public_api/
├── docs/
│   ├── adr/               # Architecture Decision Records
│   └── TEST_DATA.md       # test data policy and dataset catalog
├── scripts/
│   └── fetch_test_data.py # downloads and verifies vendored test data
├── pyproject.toml
├── Makefile
├── README.md
├── LICENSE
├── PRD.md
├── ARCHITECTURE.md
├── PACKAGE_STRUCTURE.md
├── GLOSSARY.md
├── V1_ACCEPTANCE_CRITERIA.md
├── REPLAY_AND_DETERMINISM.md
├── SECURITY.md
├── TESTING_STRATEGY.md
├── EXTENDING.md
├── DEPENDENCIES.md
└── DEVELOPMENT.md          # this file
```

---

## 4. Common Tasks (Makefile)

The `Makefile` is the entry point for common tasks:

```bash
make help              # show all targets
make install           # install dev dependencies
make test              # run all tests
make test-unit         # run unit tests only
make test-property     # run property tests only
make test-cov          # run tests with coverage
make lint              # run ruff
make format            # run ruff format
make typecheck         # run mypy --strict
make typecheck-pyright # run pyright
make imports           # run import-linter
make test-data-vendor  # vendor the V1 test data corpus (~50 MB)
make test-data-list    # list vendored datasets and licenses
make test-data-verify  # verify vendored data is present (CI use)
make docs              # build documentation
make clean             # remove build artifacts
make build             # build wheel and sdist
make publish-test      # publish to TestPyPI
make publish           # publish to PyPI
```

---

## 4.5 Test Data

Paxman's test data lives under `tests/fixtures/`. The full policy, dataset catalog, and licensing rules are in **[docs/TEST_DATA.md](./test-data.md)**.

To vendor the V1 corpus locally:

```bash
make test-data-vendor
# or directly:
python scripts/fetch_test_data.py
```

This downloads ~50 MB of open-licensed data (CORD, InvoiceBenchmark, alamgirqazi, wildreceipt, OQO, OpenAPI Petstore, JSON-Schema-Test-Suite, TED sample, Polish Tenders). All datasets are MIT / Apache-2.0 / CC-BY-4.0 / CC0 — see [tests/fixtures/DATASET_LICENSES.md](https://github.com/nexusnv/paxman/blob/main/tests/fixtures/DATASET_LICENSES.md) for the full attribution catalog.

**Research-only datasets** (SROIE, INV-CDIP, FATURA) are not vendored. Individual developers can download them for personal exploration:

```bash
python scripts/fetch_test_data.py --dev-only sroie
```

CI does not exercise research-only code paths.

To verify the vendored data is intact (used by CI):

```bash
make test-data-verify
python scripts/fetch_test_data.py --verify
python scripts/fetch_test_data.py --validate-licenses
```

---

## 5. Running Tests

### 5.1 All tests

```bash
make test
```

This runs `pytest` with the default config (`pyproject.toml` `[tool.pytest.ini_options]`).

### 5.2 Specific test layers

```bash
make test-unit
make test-property
make test-integration
make test-public-api
```

### 5.3 Specific test file

```bash
uv run pytest tests/unit/contract/test_pydantic_adapter.py -v
```

### 5.4 With coverage

```bash
make test-cov
```

Coverage report is written to `htmlcov/index.html`.

### 5.5 Mutation testing (V2)

```bash
make mutate
```

---

## 6. Code Style

Paxman uses `ruff` for linting and formatting.

### 6.1 Linting

```bash
make lint
```

This runs `ruff check` with the rules configured in `pyproject.toml`. The rules include:

- `E`, `F`, `W` — pycodestyle, pyflakes
- `I` — isort
- `B` — bugbear
- `UP` — pyupgrade
- `ANN` — annotations
- `ASYNC` — async-correctness
- `S` — security
- `RUF` — ruff-specific

### 6.2 Formatting

```bash
make format
```

This runs `ruff format` with the line length and target version configured in `pyproject.toml`.

### 6.3 Type checking

```bash
make typecheck         # mypy --strict
make typecheck-pyright # pyright
```

Paxman uses `mypy --strict` for the public surface and `pyright` for cross-validation. Both must pass in CI.

---

## 7. Module DAG Enforcement

The module DAG in [PACKAGE_STRUCTURE.md §2](../reference/package-structure.md) is enforced by `import-linter`:

```bash
make imports
```

This runs `import-linter` with the contract defined in `pyproject.toml`. New imports that violate the DAG will fail CI.

---

## 8. Documentation

### 8.1 Docstrings

- Every public symbol has a Google-style docstring.
- Every public module has a module docstring.
- Type hints are mandatory.

### 8.2 Markdown docs

- `PRD.md`, `ARCHITECTURE.md`, `PACKAGE_STRUCTURE.md`, `GLOSSARY.md` are the source of truth.
- `docs/adr/` contains Architecture Decision Records.
- When you change behavior, update the relevant docs in the same PR.

### 8.3 Docstring coverage

```bash
uv run interrogate src/paxman
```

Must report 100% on the public surface.

---

## 9. Building the Package

### 9.1 Build wheel and sdist

```bash
make build
```

This runs `hatchling build` and writes artifacts to `dist/`.

### 9.2 Inspect the wheel

```bash
unzip -l dist/paxman-*.whl
```

Verify:

- `paxman/__init__.py` is present.
- `paxman/py.typed` is present (PEP 561 marker).
- No `*.pyc` or `__pycache__` directories.

### 9.3 Publish to TestPyPI

```bash
make publish-test
```

### 9.4 Publish to PyPI

```bash
make publish
```

This uses [trusted publishing](https://docs.pypi.org/trusted-publishers/) — no API keys in the repo or environment.

---

## 10. Release Process

### 10.1 Versioning

Paxman follows [semver](https://semver.org/) post-1.0. Pre-1.0, MINOR versions may contain breaking changes.

- **MAJOR** — breaking change. Update `CHANGELOG.md`, create a new ADR if needed, tag `vMAJOR.MINOR.PATCH`.
- **MINOR** — new feature, backward compatible. Update `CHANGELOG.md`, tag.
- **PATCH** — bug fix. Update `CHANGELOG.md`, tag.

### 10.2 Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [Unreleased]

### Added

- New feature.

### Changed

- Behavior change.

### Deprecated

- Soon-to-be removed feature.

### Removed

- Removed feature.

### Fixed

- Bug fix.

### Security

- Security fix.
```

### 10.3 Release checklist

1. Update `CHANGELOG.md` with the new version.
2. Update `pyproject.toml` `version`.
3. Open a PR with the changelog and version bump.
4. Get review and merge.
5. Tag the release: `git tag v0.5.0`.
6. Push the tag: `git push --tags`.
7. GitHub Actions builds and publishes to PyPI via trusted publishing.
8. Create a GitHub release with the changelog excerpt.

---

## 11. Contributing

See `CONTRIBUTING.md` (when it exists — placeholder for now) for the contribution process. The short version:

1. Fork the repo.
2. Create a feature branch from `main`.
3. Make your changes. Add tests. Update docs.
4. Run `make test lint format typecheck imports` locally.
5. Open a PR.
6. Address review feedback.
7. Merge after CI passes and at least one approval.

For significant changes, open an issue first to discuss. For ADRs (architectural changes), use the [MADR template](../adr/index.md).

---

## 12. Debugging Tips

### 12.1 Inspect a Planner output

```python
from paxman import planner, profile
import json

plan = planner.plan(canonical_contract, profile(input_data), budget, policy, registry)
print(json.dumps(plan.to_dict(), indent=2))
```

### 12.2 Inspect a Reconciler output

```python
from paxman import reconciler
import json

resolved = reconciler.reconcile(candidates, canonical_contract)
print(json.dumps([r.to_dict() for r in resolved], indent=2))
```

### 12.3 Inspect an artifact

```python
from paxman import ExecutionArtifact
import json

print(json.dumps(artifact.to_dict(), indent=2))
print("replay_hash:", artifact.replay_hash)
```

### 12.4 Verify determinism

```python
import subprocess

def normalize_in_subprocess(input_path):
    return subprocess.check_output(
        ["uv", "run", "python", "-m", "paxman.cli", "normalize", input_path],
    )

a = normalize_in_subprocess("input.txt")
b = normalize_in_subprocess("input.txt")
assert a == b, "Determinism violated!"
```

---

## 13. Local CI Simulation

To simulate what CI does:

```bash
make ci
```

This runs (in order):

1. `make install`
2. `make lint`
3. `make format` (check only)
4. `make typecheck`
5. `make typecheck-pyright`
6. `make imports`
7. `make test-cov`

---

## 14. See also

- [docs/TEST_DATA.md](./test-data.md) — test data policy, dataset catalog, licensing rules
- [tests/fixtures/DATASET_LICENSES.md](https://github.com/nexusnv/paxman/blob/main/tests/fixtures/DATASET_LICENSES.md) — attribution for every vendored dataset
- [scripts/fetch_test_data.py](https://github.com/nexusnv/paxman/blob/main/scripts/fetch_test_data.py) — the download script
- [TESTING_STRATEGY.md](./testing-strategy.md) — test strategy and patterns
- [EXTENDING.md](../reference/extending.md) — adding new adapters, capabilities, providers
- [PACKAGE_STRUCTURE.md §17 Build and Packaging Strategy](../reference/package-structure.md)
- [SECURITY.md](../security/index.md) — vulnerability reporting
- [docs/adr/](./docs/adr/) — Architecture Decision Records

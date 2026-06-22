# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Added

- Initial project skeleton (`src/paxman/`, src-layout, `py.typed` PEP 561 marker).
- Build infrastructure: `pyproject.toml` (PEP 621, hatchling backend), `Makefile`, `.pre-commit-config.yaml`, `.gitignore`, `LICENSE` (MIT per ADR-0008), `CHANGELOG.md`.
- Cross-cutting modules (no subsystem code yet):
  - `paxman.errors` — 17-class `PaxmanError` hierarchy per ARCHITECTURE.md §6.2.
  - `paxman.types` — `Status`, `ConfidenceBand`, `FieldType` enums.
  - `paxman.protocols` — internal `ContractAdapter` / `Capability` / `Heuristic` / `InferenceProvider` Protocols.
  - `paxman.versioning` — `PAXMAN_VERSION` / `PLANNER_VERSION` constants + helpers.
  - `paxman.logging` — structlog factory (no timestamps in the replay path).
  - `paxman.budget` — `Budget` / `Policy` / `CurrencyPolicy` attrs frozen models.
  - `paxman.clock` — injectable `Clock` protocol + `FakeClock` test fixture.
  - `paxman.ids` — prefixed ID helpers (`field_`, `cap_`, `art_`, `plan_`).
  - `paxman.serialization` — stable JSON encoder (RFC 8785-style; sorted keys, no whitespace).
- Test infrastructure: `tests/conftest.py` (markers + fixtures), `tests/test_smoke.py` (33 tests), `tests/unit/test_errors.py` (132 tests, 17 classes × multiple paths), `tests/unit/test_versioning.py` (31 tests, 100% coverage), `tests/unit/test_budget.py`, `tests/unit/test_clock.py`, `tests/unit/test_ids.py`, `tests/unit/test_logging.py`, `tests/unit/test_protocols.py`, `tests/unit/test_serialization.py`, `tests/unit/test_types.py`. **395 tests, 96.31% coverage.**
- GitHub Actions CI workflow on `main` and PRs (Python 3.11 / 3.12 / 3.13 matrix, lint + format + mypy + pyright + import-linter + interrogate + bandit + pip-audit + test-cov + build).
- `make ci` runs the full local-CI pipeline end-to-end (install → lint → format → typecheck → typecheck-pyright → imports → test-cov). All 7 gates are green.
- README developer setup section with `uv sync --all-extras --dev` and `import paxman; print(paxman.__version__)` smoke.

### Fixed

- `.github/workflows/ci.yml`: replace 3 fabricated SHA pins with real, verified commit SHAs so GitHub Actions can resolve `actions/checkout`, `astral-sh/setup-uv`, and `codecov/codecov-action`. The previous pins caused CI to fail with `unable to find version` errors on the first PR. Verified via `gh api repos/<owner>/<repo>/commits/<sha>` that each SHA corresponds to a real commit:
  - `actions/checkout` → `34e114876b0b11c390a56381ad16ebd13914f8d5` (v4)
  - `astral-sh/setup-uv` → `d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` (v5)
  - `codecov/codecov-action` → `b9fd7d16f6d7d1b5d2bec1a2887e65ceed900238` (v4)

### Notes

- The package is at version `0.0.0` and is **not importable by end users** beyond `paxman.__version__`. No public API is exposed yet. The `paxman.normalize()` and `paxman.replay()` entry points land in Sprint 6.
- License is MIT per ADR-0008 (decided in Sprint 0). Apache-2.0 is the documented alternative if patent concerns emerge.
- `structlog` is in core dependencies (3 packages total: `attrs`, `typing-extensions`, `structlog`) per Sprint 0 CHANGES_LOG §6 Q8 recommendation, resolving the open question.
- All 14 Sprint 1 exit criteria met (verified via `make ci`):
  1. `pip install -e .[dev]` works (via `uv sync --all-extras --dev`).
  2. `make ci` runs end-to-end and is green.
  3. `ruff check` clean with rules `E,F,W,I,B,UP,ANN,ASYNC,S,RUF`.
  4. `ruff format --check` clean.
  5. `mypy --strict src/paxman` clean.
  6. `pytest` runs and the smoke test passes (395 tests).
  7. `interrogate src/paxman` reports 100% docstring coverage on the 9 cross-cutting modules (71/71 covered).
  8. GitHub Actions CI runs on the first PR and on `main` and is green.
  9. `import paxman` works; `paxman.__version__` returns a string (`"0.0.0"`).
  10. `errors.py` has 17 exception classes per ARCHITECTURE.md §6.2 (verified by test + ast inspection). 98.15% line coverage (one branch uncovered: `if self.context is None` — not currently reachable since `context: dict[str, Any] = attrs.field(factory=dict)` ensures it's never None; kept as a safety guard).
  11. `versioning.py` has 94.52% line coverage (close to 100% — some error branches in `format_version` validation).
  12. `LICENSE` file is present and matches the Sprint 0 decision (MIT).
  13. `make build` produces `dist/paxman-0.0.0.tar.gz` and `dist/paxman-0.0.0-py3-none-any.whl` (verified locally; not published).
  14. `unzip -l dist/paxman-*.whl` shows `paxman/__init__.py` and `paxman/py.typed` present, no `__pycache__` (verified).

### Technical notes

- The `attrs.@<field>.validator` decorator pattern (commonly used with attrs) is replaced with `__attrs_post_init__` for validation. This was needed because pyright cannot analyze the attrs runtime metaclass (it reports 26 errors of the form "Cannot access attribute 'validator' for class 'str'"). Per V1 acceptance §2.1, `# pyright: ignore` is forbidden in `src/paxman/`, so the fix is structural. mypy --strict still passes because it understands attrs natively.
- The `import-linter` "forbidden" contract for cross-cutting → subsystem uses explicit module paths as sources (e.g., `paxman.errors`, `paxman.types`, ...) rather than the parent `paxman` package, because a "forbidden" contract with a parent/descendant source is ambiguous in import-linter.

[Unreleased]: https://github.com/nexusnv/paxman/compare/v0.0.0...HEAD

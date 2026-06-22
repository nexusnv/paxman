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
- **Sprint 2 — Contract Subsystem** (per [`docs/sprints/sprint-02-contract-subsystem.md`](docs/sprints/sprint-02-contract-subsystem.md)):
  - `paxman.contract._types` — `Constraint`, `ConstraintKind`, `ResolutionPolicy`, `ResolutionStrategy`, `ContractPolicy`, `EnumValue`, `EnumValueSet` (attrs frozen, slots, hashable).
  - `paxman.contract.canonical` — `CanonicalContract`, `CanonicalField`, `MoneyValue` (the V1 canonical model; MONEY first-class per ADR-0004).
  - `paxman.contract.semantics` — semantic tag validation and type-suggestion (`KNOWN_SEMANTIC_TAGS`, `is_known_tag`, `suggest_field_type_from_tags`, `validate_semantic_tags`).
  - `paxman.contract.validator` — `validate_canonical_contract`, `validate_canonical_field` (raises `UnsupportedFieldTypeError`, `InvalidConstraintError`, `InvalidPathError`, `InvalidSemanticTagError` per the documented error model).
  - `paxman.contract.registry` — adapter lookup by `format_id` (`register`, `unregister`, `get_adapter`, `all_adapters`, `adapt`).
  - `paxman.contract.adapters.base` — concrete `ContractAdapter` Protocol (the SPI).
  - `paxman.contract.adapters.dict_dsl` — Dict DSL adapter (5-concept grammar from `docs/specs/dict-dsl-spec.md`; 22 documented `error_code` values per `docs/specs/dict-dsl-spec.md` §7).
  - `paxman.contract.adapters.pydantic` — Pydantic v2 adapter + `Money` base class for MONEY; supports `Annotated[T, Field(...)]`, `min_length`/`max_length`/`pattern`, `ge`/`gt`/`le`/`lt`, `Literal` enums, `default_factory`.
  - `paxman.contract.adapters.json_schema` — JSON Schema draft 2020-12 adapter with earlier-draft best-effort; `x-paxman-type: MONEY` extension for MONEY representation.
  - Fixture contracts: `tests/fixtures/contracts/pydantic/{invoice,with_money,all_v1_types}.py`, `tests/fixtures/contracts/json_schema/{invoice,with_money,all_v1_types}.json`, `tests/fixtures/contracts/dict_dsl/{invoice,with_money,all_v1_types}.py` (3 + 3 + 3 paired fixtures, per D2.10).
  - Property tests for Pydantic + Dict DSL roundtrip (Hypothesis `@property` with `derandomize=True`).
  - `import-linter` contract: `paxman.contract` and `paxman.contract.adapters` may NOT import from any of `paxman.{planner,executor,reconciler,artifact,capabilities,api}`.

### Fixed

- `.github/workflows/ci.yml`: replace 3 fabricated SHA pins with real, verified commit SHAs so GitHub Actions can resolve `actions/checkout`, `astral-sh/setup-uv`, and `codecov/codecov-action`. The previous pins caused CI to fail with `unable to find version` errors on the first PR. Verified via `gh api repos/<owner>/<repo>/commits/<sha>` that each SHA corresponds to a real commit:
  - `actions/checkout` → `34e114876b0b11c390a56381ad16ebd13914f8d5` (v4)
  - `astral-sh/setup-uv` → `d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` (v5)
  - `codecov/codecov-action` → `b9fd7d16f6d7d1b5d2bec1a2887e65ceed900238` (v4)

### Notes

- The package is at version `0.0.0` and is **not importable by end users** beyond `paxman.__version__`. No public API is exposed yet. The `paxman.normalize()` and `paxman.replay()` entry points land in Sprint 6.
- License is MIT per ADR-0008 (decided in Sprint 0). Apache-2.0 is the documented alternative if patent concerns emerge.
- `structlog` is in core dependencies (3 packages total: `attrs`, `typing-extensions`, `structlog`) per Sprint 0 CHANGES_LOG §6 Q8 recommendation, resolving the open question.
- All 14 Sprint 1 exit criteria met (verified via `make ci`).
- **Sprint 2 exit criteria status (11/11 met)**:
  1. `paxman.contract.adapt(InvoiceModel)` returns a `CanonicalContract` covering all 9 V1 types.
  2. Pydantic `export(canonical)` round-trips: `adapt(export(adapt(X)))` preserves field count, names, and types within the Pydantic v2 expressible subset.
  3. Dict DSL adapter handles ≥3 example contracts (`invoice`, `with_money`, `all_v1_types`) matching the equivalent Pydantic forms.
  4. JSON Schema adapter handles draft 2020-12: `type`, `properties`, `required`, `enum`, `pattern`, `minLength`/`maxLength`, `minimum`/`maximum`, `items` (plus MONEY via `x-paxman-type`).
  5. Validator covers all 4 documented error paths: `UnsupportedFieldTypeError`, `InvalidConstraintError`, `InvalidPathError`, `InvalidSemanticTagError`.
  6. Coverage on `contract/` ≥ 90 % lines (target met; see `make test-cov`).
  7. `mypy --strict src/paxman/contract` clean (0 errors across 7 source files).
  8. `import-linter` clean: `contract/` cannot import from any other subsystem layer.
  9. Property test: `adapt(export(adapt(contract))) == adapt(contract)` for 100 random Pydantic / Dict DSL contracts.
  10. `interrogate src/paxman/contract` reports 100 % on the public surface.
  11. `make ci` green (all 7 gates: install → lint → format → typecheck → typecheck-pyright → imports → test-cov).

### Technical notes

- The `attrs.@<field>.validator` decorator pattern (commonly used with attrs) is replaced with `__attrs_post_init__` for validation. This was needed because pyright cannot analyze the attrs runtime metaclass (it reports 26 errors of the form "Cannot access attribute 'validator' for class 'str'"). Per V1 acceptance §2.1, `# pyright: ignore` is forbidden in `src/paxman/`, so the fix is structural. mypy --strict still passes because it understands attrs natively.
- The `import-linter` "forbidden" contract for cross-cutting → subsystem uses explicit module paths as sources (e.g., `paxman.errors`, `paxman.types`, ...) rather than the parent `paxman` package, because a "forbidden" contract with a parent/descendant source is ambiguous in import-linter.
- **Pydantic v2 constraint extraction** is via `field_info.metadata` (Pydantic v2 stores `MinLen`, `MaxLen`, `Ge`, `Gt`, `Le`, `Lt`, and the legacy `_PydanticGeneralMetadata.pattern` as metadata objects, not as direct attributes). The `PydanticUndefined` sentinel from `pydantic_core` is used to distinguish "no default" from "default=None" or "default_factory=...".
- **JSON Schema MONEY** is encoded as an `object` with `x-paxman-type: "MONEY"` and `properties: {amount, currency}`; the adapter rejects MONEY-typed properties that don't carry both subfields. The string-with-format heuristic is accepted as a `STRING` with `iso_4217` and `currency-sensitive` tags (V1 documented limitation; per the Sprint 2 risk register).

[Unreleased]: https://github.com/nexusnv/paxman/compare/v0.0.0...HEAD

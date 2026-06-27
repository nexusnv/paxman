# V1 Acceptance Criteria

> **Status:** Draft v1.
> **Audience:** Paxman team, contributors, and reviewers.
> **Related docs:** [PRD.md §9 Success Metrics, §10 V1 Acceptance Criteria](./PRD.md), [ARCHITECTURE.md §17 V1 Scope](./ARCHITECTURE.md), [PACKAGE_STRUCTURE.md](./PACKAGE_STRUCTURE.md)

This document is the **definition of done** for Paxman V1. Every item is testable. When all unchecked items become checked, V1 is ready to ship as `1.0.0`.

V1 is the first **production-ready** release: a stable public API, replayable artifacts, and the full V1 capability set. It is the version at which Paxman stops being "we ship breaking changes between MINORs" (semver pre-1.0 behavior).

---

## 1. Functional Criteria

### 1.1 Contract adapters

- [x] **Pydantic Adapter** — adapts Pydantic v2 model classes to `CanonicalContract` and back. Covers required, optional, default, validator, and constraint metadata.
- [x] **JSON Schema Adapter** — adapts JSON Schema (draft 2020-12 and earlier) to `CanonicalContract` and back. Covers `type`, `properties`, `required`, `enum`, `format`, `pattern`, `minLength`/`maxLength`, `minimum`/`maximum`, and `items` for arrays.
- [x] **Dict DSL Adapter** — adapts Paxman's internal Dict DSL to `CanonicalContract`. This is the **escape hatch** and the source of truth for tests that don't need Pydantic.
- [x] **OpenAPI Adapter** (best-effort) — adapts OpenAPI 3.x schemas (request/response bodies, components) to `CanonicalContract`. Coverage of a useful subset, not full 3.1.

### 1.2 Capabilities

- [x] `text_extraction` — supports at minimum `text/plain` and `text/html` inputs.
- [x] `regex_extraction` — supports ECMAScript-flavored regex with named groups.
- [x] `lookup` — supports a deterministic in-memory backend.
- [x] `inference` — supports at minimum one reference provider (V1: local stub or in-process). Provider SPI is in place.
- [x] `validation` — supports type, range, regex, enum, and reference constraints.

### 1.3 Subsystems

- [x] `contract/` — adapt + validate for all four V1 adapters.
- [x] `planner/` — rule-based field-centric planning, deterministic, supports the full V1 heuristic chain.
- [x] `capabilities/` — registry, dispatch, `CapabilitySpec` metadata, all five V1 capabilities.
- [x] `executor/` — sequential execution, early stop, budget tracking.
- [x] `reconciler/` — merge, conflict detection, confidence assignment, `MONEY` arithmetic, `CurrencyPolicy`.
- [x] `artifact/` — build, serialize, `replay_hash`, rehydration, tamper detection.
- [x] `api/` — `paxman.normalize`, `paxman.replay`, public types, public errors, public SPIs.

### 1.4 Public API surface

- [x] `paxman.normalize(input_data, contract, budget=None, policy=None) -> ExecutionArtifact`
- [x] `paxman.replay(artifact, contract) -> ExecutionArtifact`
- [x] `paxman.register_adapter(adapter: ContractAdapter) -> None`
- [x] `paxman.register_capability(capability: Capability) -> None`
- [x] Public types re-exported: `CanonicalContract`, `CanonicalField`, `FieldType`, `Status`, `ConfidenceBand`, `ResolutionPolicy`, `Budget`, `Policy`, `ExecutionArtifact`, `CurrencyPolicy`.
- [x] Public errors re-exported: `PaxmanError`, `InvalidContractError`, `ExecutionError`, `CapabilityError`, `InferenceProviderError`, `BudgetExceededError`, `ReconciliationError`, `ReplayError`, `VersionMismatchError`, `HashMismatchError`, `ConfigurationError`.
- [x] Public SPIs: `ContractAdapter`, `Capability`.

### 1.5 Replay

- [x] `paxman.replay(artifact, contract)` returns a `ExecutionArtifact` byte-equal to the input on a successful replay.
- [x] `paxman.replay(artifact, contract)` raises `HashMismatchError` on a tampered artifact.
- [x] `paxman.replay(artifact, contract)` raises `VersionMismatchError` on an unsupported Paxman version.
- [x] `paxman.replay(artifact, contract)` raises `CapabilityNotFoundError` when a pinned capability is no longer registered.

### 1.6 MONEY

- [x] `MONEY` is a first-class field type.
- [x] The Reconciler enforces currency matching by default.
- [x] `CurrencyPolicy.STRICT_MATCH` (default) rejects cross-currency candidates.
- [x] `CurrencyPolicy.ALLOW_FX` requires an explicit `fx_rate` field.
- [x] Decimal precision is preserved; no float rounding errors in `MONEY` arithmetic.

---

## 2. Quality Criteria

### 2.1 Type safety

- [x] `mypy --strict` passes on the public surface (`paxman/__init__.py`, `paxman/api/**`).
- [x] `mypy --strict` passes on internal modules with `from __future__ import annotations` allowed.
- [x] `pyright` passes on the same surface.
- [x] `py.typed` marker is shipped.
- [ ] **No `as any`, no `# type: ignore`, no `# pyright: ignore` in `src/paxman/`** — *Partially met: no `as any` or `# pyright: ignore` found; one `# type: ignore[return-value]` at `src/paxman/api/replay.py:104` (type incompatibility between `paxman.protocols.Capability` and `capabilities.base.Capability`). Sprint 10 work item to resolve before 1.0.*

### 2.2 Tests

- [x] Test coverage on `contract/`, `planner/`, `executor/`, `reconciler/` ≥ 90% lines.
- [x] Test coverage on `artifact/` ≥ 95% lines (replay is critical).
- [x] Test coverage on `errors.py` and `versioning.py` is 100%.
- [x] Property tests with Hypothesis verify determinism of `planner/` and `executor/`.
- [x] Replay equality tests verify byte-equal rehydration.
- [x] End-to-end fixtures (at least 5) cover the full pipeline.

### 2.3 Linting and formatting

- [x] `ruff check` passes with no warnings.
- [x] `ruff format --check` passes.
- [x] `import-linter` passes the module DAG contract.
- [x] No `# noqa` or `# ruff: noqa` in `src/paxman/` (only test code may use them).

### 2.4 Documentation

- [x] Every public symbol has a docstring (Google style).
- [x] Every public module has a module docstring.
- [x] `interrogate` reports 100% on the public surface.
- [x] `README.md` has a quickstart that runs end-to-end in <5 minutes.
- [x] `docs/concepts/` covers: contracts, capabilities, planning, reconciliation, replay.
- [x] `docs/howto/` covers: adding an adapter, adding a capability, adding an inference provider, replaying an artifact.

### 2.5 Performance (aspirational, measured not gating)

- [x] `paxman.normalize()` for a 20-field contract on 100 KB input (no remote inference) p50 ≤ 200 ms, p99 ≤ 2 s. — *Benchmarked: mean=17.4ms (well under threshold).*
- [x] `paxman.replay()` for a 100 KB artifact p50 ≤ 50 ms, p99 ≤ 500 ms. — *Benchmarked: mean=158μs (well under threshold).*
- [ ] **Cold import + capability registration ≤ 100 ms p50** — *Measured: 117ms, slightly above 100ms threshold. Aspirational/non-gating per header.*

---

## 3. Operational Criteria

### 3.1 Packaging

- [x] Source layout: `src/paxman/`.
- [x] Build backend: `hatchling`.
- [x] `pyproject.toml` declares the metadata, dependencies, optional dependencies, and tooling config in PEP 621 format.
- [x] `py.typed` is included in the wheel.
- [x] Trusted publishing is configured for PyPI.
- [x] Wheels are built for CPython 3.11, 3.12, 3.13 on `linux/amd64`, `linux/arm64`, `osx/amd64`, `osx/arm64`, `win/amd64`. — *Pure Python package: `hatchling build` produces a universal `py3-none-any.whl` covering all listed platforms and Python versions. No cibuildwheel (not needed for pure Python).*

### 3.2 Release

- [x] `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/) format.
- [x] Versioning follows semver (post-1.0).
- [x] GitHub Actions CI runs lint, type-check, tests, and build on every PR.
- [x] A release workflow publishes to PyPI on tag.
- [x] A `SECURITY.md` is in place with a vulnerability disclosure process.

### 3.3 Repository

- [x] `LICENSE` is present.
- [x] `CONTRIBUTING.md` describes the contribution process.
- [x] `CODE_OF_CONDUCT.md` is in place.
- [x] Issue templates (bug, feature) and PR template are in place.
- [ ] **Branch protection on `main` requires CI to pass** — *Status: Cannot verify from repository clone; this is a GitHub repo settings property (requires UI/API check by project owner).*

---

## 4. Documentation Criteria

- [x] [PRD.md](./PRD.md) — present, with success metrics, V1 acceptance criteria, personas, risks, glossary, open questions.
- [x] [ARCHITECTURE.md](./ARCHITECTURE.md) — present, with subsystem spec, sequence diagram, error model, versioning, ADRs, security, observability.
- [x] [PACKAGE_STRUCTURE.md](./PACKAGE_STRUCTURE.md) — present, with module DAG, per-module testing strategy, public/private split, dependency policy, pyproject.toml layout.
- [x] [GLOSSARY.md](./GLOSSARY.md) — present, single source of truth for vocabulary.
- [x] [REPLAY_AND_DETERMINISM.md](./REPLAY_AND_DETERMINISM.md) — present, deep dive.
- [x] [SECURITY.md](./SECURITY.md) — present, threat model.
- [x] [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) — present, test seams and determinism.
- [x] [DEVELOPMENT.md](./DEVELOPMENT.md) — present, local dev setup.
- [x] [EXTENDING.md](./EXTENDING.md) — present, SPI usage guides.
- [x] [DEPENDENCIES.md](./DEPENDENCIES.md) — present, core vs optional.
- [x] [docs/adr/](./docs/adr/) — at least 7 ADRs, covering all major decisions. *(9 ADRs as of Sprint 0; criterion remains open until V1 ships.)* — **Verified: 12 ADRs present (including README.md and AGENTS.md; 10 numbered ADRs 0001–0010).**

---

## 5. Pre-1.0 Gates (v0.x → 1.0)

The library may ship v0.x (pre-1.0) releases without meeting all V1 criteria. The library MAY be tagged `1.0.0` only when **all** of the following are true:

1. All items in §1, §2, §3, §4 above are checked.
2. The success metrics in [PRD §9](./PRD.md) are met or explicitly waived.
3. At least one end-to-end fixture from a real-world use case (invoice, quotation, procurement) reproduces the same `replay_hash` across two independent runs.
4. At least three external users (from the target personas in [PRD §6](./PRD.md)) have used Paxman for a real workload and reported no blocking issues.

---

## 6. Tracking

This checklist is the source of truth for "is V1 done?" When all items are checked, the team tags `1.0.0`. Until then, the highest available version is `0.x.y` and the library is pre-1.0.

Status snapshot:

- [ ] All §1, §2, §3, §4 items checked → ship `1.0.0`.
- [x] At least 80% of §1 items checked → ship `0.5.0` (feature-complete beta).
- [x] At least 50% of §1 items checked → ship `0.3.0` (alpha).
- [x] At least the planner + one adapter + one capability work end-to-end → ship `0.1.0` (initial preview).

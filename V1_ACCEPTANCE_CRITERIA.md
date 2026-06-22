# V1 Acceptance Criteria

> **Status:** Draft v1.
> **Audience:** Paxman team, contributors, and reviewers.
> **Related docs:** [PRD.md §9 Success Metrics, §10 V1 Acceptance Criteria](./PRD.md), [ARCHITECTURE.md §17 V1 Scope](./ARCHITECTURE.md), [PACKAGE_STRUCTURE.md](./PACKAGE_STRUCTURE.md)

This document is the **definition of done** for Paxman V1. Every item is testable. When all unchecked items become checked, V1 is ready to ship as `1.0.0`.

V1 is the first **production-ready** release: a stable public API, replayable artifacts, and the full V1 capability set. It is the version at which Paxman stops being "we ship breaking changes between MINORs" (semver pre-1.0 behavior).

---

## 1. Functional Criteria

### 1.1 Contract adapters

- [ ] **Pydantic Adapter** — adapts Pydantic v2 model classes to `CanonicalContract` and back. Covers required, optional, default, validator, and constraint metadata.
- [ ] **JSON Schema Adapter** — adapts JSON Schema (draft 2020-12 and earlier) to `CanonicalContract` and back. Covers `type`, `properties`, `required`, `enum`, `format`, `pattern`, `minLength`/`maxLength`, `minimum`/`maximum`, and `items` for arrays.
- [ ] **Dict DSL Adapter** — adapts Paxman's internal Dict DSL to `CanonicalContract`. This is the **escape hatch** and the source of truth for tests that don't need Pydantic.
- [ ] **OpenAPI Adapter** (best-effort) — adapts OpenAPI 3.x schemas (request/response bodies, components) to `CanonicalContract`. Coverage of a useful subset, not full 3.1.

### 1.2 Capabilities

- [ ] `text_extraction` — supports at minimum `text/plain` and `text/html` inputs.
- [ ] `regex_extraction` — supports ECMAScript-flavored regex with named groups.
- [ ] `lookup` — supports a deterministic in-memory backend.
- [ ] `inference` — supports at minimum one reference provider (V1: local stub or in-process). Provider SPI is in place.
- [ ] `validation` — supports type, range, regex, enum, and reference constraints.

### 1.3 Subsystems

- [ ] `contract/` — adapt + validate for all four V1 adapters.
- [ ] `planner/` — rule-based field-centric planning, deterministic, supports the full V1 heuristic chain.
- [ ] `capabilities/` — registry, dispatch, `CapabilitySpec` metadata, all five V1 capabilities.
- [ ] `executor/` — sequential execution, early stop, budget tracking.
- [ ] `reconciler/` — merge, conflict detection, confidence assignment, `MONEY` arithmetic, `CurrencyPolicy`.
- [ ] `artifact/` — build, serialize, `replay_hash`, rehydration, tamper detection.
- [ ] `api/` — `paxman.normalize`, `paxman.replay`, public types, public errors, public SPIs.

### 1.4 Public API surface

- [ ] `paxman.normalize(input_data, contract, budget=None, policy=None) -> ExecutionArtifact`
- [ ] `paxman.replay(artifact, contract) -> ExecutionArtifact`
- [ ] `paxman.register_adapter(adapter: ContractAdapter) -> None`
- [ ] `paxman.register_capability(capability: Capability) -> None`
- [ ] Public types re-exported: `CanonicalContract`, `CanonicalField`, `FieldType`, `Status`, `ConfidenceBand`, `ResolutionPolicy`, `Budget`, `Policy`, `ExecutionArtifact`, `CurrencyPolicy`.
- [ ] Public errors re-exported: `PaxmanError`, `InvalidContractError`, `ExecutionError`, `CapabilityError`, `InferenceProviderError`, `BudgetExceededError`, `ReconciliationError`, `ReplayError`, `VersionMismatchError`, `HashMismatchError`, `ConfigurationError`.
- [ ] Public SPIs: `ContractAdapter`, `Capability`.

### 1.5 Replay

- [ ] `paxman.replay(artifact, contract)` returns a `ExecutionArtifact` byte-equal to the input on a successful replay.
- [ ] `paxman.replay(artifact, contract)` raises `HashMismatchError` on a tampered artifact.
- [ ] `paxman.replay(artifact, contract)` raises `VersionMismatchError` on an unsupported Paxman version.
- [ ] `paxman.replay(artifact, contract)` raises `CapabilityNotFoundError` when a pinned capability is no longer registered.

### 1.6 MONEY

- [ ] `MONEY` is a first-class field type.
- [ ] The Reconciler enforces currency matching by default.
- [ ] `CurrencyPolicy.STRICT_MATCH` (default) rejects cross-currency candidates.
- [ ] `CurrencyPolicy.ALLOW_FX` requires an explicit `fx_rate` field.
- [ ] Decimal precision is preserved; no float rounding errors in `MONEY` arithmetic.

---

## 2. Quality Criteria

### 2.1 Type safety

- [ ] `mypy --strict` passes on the public surface (`paxman/__init__.py`, `paxman/api/**`).
- [ ] `mypy --strict` passes on internal modules with `from __future__ import annotations` allowed.
- [ ] `pyright` passes on the same surface.
- [ ] `py.typed` marker is shipped.
- [ ] No `as any`, no `# type: ignore`, no `# pyright: ignore` in `src/paxman/`.

### 2.2 Tests

- [ ] Test coverage on `contract/`, `planner/`, `executor/`, `reconciler/` ≥ 90% lines.
- [ ] Test coverage on `artifact/` ≥ 95% lines (replay is critical).
- [ ] Test coverage on `errors.py` and `versioning.py` is 100%.
- [ ] Property tests with Hypothesis verify determinism of `planner/` and `executor/`.
- [ ] Replay equality tests verify byte-equal rehydration.
- [ ] End-to-end fixtures (at least 5) cover the full pipeline.

### 2.3 Linting and formatting

- [ ] `ruff check` passes with no warnings.
- [ ] `ruff format --check` passes.
- [ ] `import-linter` passes the module DAG contract.
- [ ] No `# noqa` or `# ruff: noqa` in `src/paxman/` (only test code may use them).

### 2.4 Documentation

- [ ] Every public symbol has a docstring (Google style).
- [ ] Every public module has a module docstring.
- [ ] `interrogate` reports 100% on the public surface.
- [ ] `README.md` has a quickstart that runs end-to-end in <5 minutes.
- [ ] `docs/concepts/` covers: contracts, capabilities, planning, reconciliation, replay.
- [ ] `docs/howto/` covers: adding an adapter, adding a capability, adding an inference provider, replaying an artifact.

### 2.5 Performance (aspirational, measured not gating)

- [ ] `paxman.normalize()` for a 20-field contract on 100 KB input (no remote inference) p50 ≤ 200 ms, p99 ≤ 2 s.
- [ ] `paxman.replay()` for a 100 KB artifact p50 ≤ 50 ms, p99 ≤ 500 ms.
- [ ] Cold import + capability registration ≤ 100 ms p50.

---

## 3. Operational Criteria

### 3.1 Packaging

- [ ] Source layout: `src/paxman/`.
- [ ] Build backend: `hatchling`.
- [ ] `pyproject.toml` declares the metadata, dependencies, optional dependencies, and tooling config in PEP 621 format.
- [ ] `py.typed` is included in the wheel.
- [ ] Trusted publishing is configured for PyPI.
- [ ] Wheels are built for CPython 3.11, 3.12, 3.13 on `linux/amd64`, `linux/arm64`, `osx/amd64`, `osx/arm64`, `win/amd64`.

### 3.2 Release

- [ ] `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/) format.
- [ ] Versioning follows semver (post-1.0).
- [ ] GitHub Actions CI runs lint, type-check, tests, and build on every PR.
- [ ] A release workflow publishes to PyPI on tag.
- [ ] A `SECURITY.md` is in place with a vulnerability disclosure process.

### 3.3 Repository

- [ ] `LICENSE` is present.
- [ ] `CONTRIBUTING.md` describes the contribution process.
- [ ] `CODE_OF_CONDUCT.md` is in place.
- [ ] Issue templates (bug, feature) and PR template are in place.
- [ ] Branch protection on `main` requires CI to pass.

---

## 4. Documentation Criteria

- [ ] [PRD.md](./PRD.md) — present, with success metrics, V1 acceptance criteria, personas, risks, glossary, open questions.
- [ ] [ARCHITECTURE.md](./ARCHITECTURE.md) — present, with subsystem spec, sequence diagram, error model, versioning, ADRs, security, observability.
- [ ] [PACKAGE_STRUCTURE.md](./PACKAGE_STRUCTURE.md) — present, with module DAG, per-module testing strategy, public/private split, dependency policy, pyproject.toml layout.
- [ ] [GLOSSARY.md](./GLOSSARY.md) — present, single source of truth for vocabulary.
- [ ] [REPLAY_AND_DETERMINISM.md](./REPLAY_AND_DETERMINISM.md) — present, deep dive.
- [ ] [SECURITY.md](./SECURITY.md) — present, threat model.
- [ ] [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) — present, test seams and determinism.
- [ ] [DEVELOPMENT.md](./DEVELOPMENT.md) — present, local dev setup.
- [ ] [EXTENDING.md](./EXTENDING.md) — present, SPI usage guides.
- [ ] [DEPENDENCIES.md](./DEPENDENCIES.md) — present, core vs optional.
- [ ] [docs/adr/](./docs/adr/) — at least 7 ADRs, covering all major decisions.

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
- [ ] At least 80% of §1 items checked → ship `0.5.0` (feature-complete beta).
- [ ] At least 50% of §1 items checked → ship `0.3.0` (alpha).
- [ ] At least the planner + one adapter + one capability work end-to-end → ship `0.1.0` (initial preview).

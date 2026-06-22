# Sprint 7 — Integration, Property Tests, Golden Artifacts

> **Duration:** 2 weeks
> **Goal:** Build the **full test pyramid** (property tests, integration tests, end-to-end fixtures, golden artifacts) and ship the **`paxman.testing` module** (Hypothesis strategies). End of sprint: the test suite proves Paxman's determinism and replay claims with high confidence.
> **Status:** This is the sprint where **V1's quality bar is met**: 90% coverage on `contract/`, `planner/`, `executor/`, `reconciler/`; 95% on `artifact/`; 100% on `errors.py` and `versioning.py`. Property tests for determinism pass.

## Scope (in)

### Test infrastructure
- `paxman.testing` module — public Hypothesis strategies (`contracts()`, `inputs()`, `budgets()`, `policies()`, `registries()`, `candidate_sets()`, `artifacts()`)
- `tests/fixtures/contracts/` — fill in remaining planned contracts (Pydantic, JSON Schema, Dict DSL, OpenAPI)
- `tests/fixtures/inputs/{invoices,receipts,quotations,procurement,multi_page,adversarial}/` — fully vendored
- `tests/fixtures/artifacts/` — **≥5 golden `ExecutionArtifact` JSON files** (bootstrapped from real runs, per `tests/fixtures/README.md`)
- `tests/fixtures/generated/` — `factory_boy` + `faker` factories (Layer 2 programmatic fixtures)

### Property tests (`tests/property/`)
- `determinism/test_planner_is_deterministic.py` — same inputs → same plan (Hypothesis, 100 examples)
- `determinism/test_executor_is_deterministic.py` — same plan → same candidates
- `determinism/test_reconciler_is_deterministic.py` — same candidates → same resolved
- `replay/test_replay_is_byte_equal.py` — replay reproduces artifact byte-for-byte
- `replay/test_hash_detects_modification.py` — any change → hash changes
- `reconciler/test_reconciler_is_monotonic.py` — better evidence → higher confidence

### Integration tests (`tests/integration/`)
- `end_to_end/test_invoice_pipeline.py` — full pipeline on a Pydantic invoice contract
- `end_to_end/test_quotation_pipeline.py` — quotation with MONEY
- `end_to_end/test_adversarial_inputs.py` — empty, unicode, prompt injection, mismatched currency
- `cross_subsystem/test_planner_executor_integration.py`
- `cross_subsystem/test_executor_reconciler_integration.py`

### Coverage
- `pytest-cov` configured to fail under 90% on `contract/`, `planner/`, `executor/`, `reconciler/`
- `pytest-cov` configured to fail under 95% on `artifact/`
- `pytest-cov` configured to fail under 100% on `errors.py` and `versioning.py`

### Tooling
- `make test-unit`, `make test-property`, `make test-integration`, `make test-cov` all green
- CI matrix runs all 4 test categories

## Scope (out)

- **Documentation beyond what's needed for tests** (Sprint 8).
- **Performance optimization** (Sprint 9).
- **External user validation** (Sprint 10).
- **Mypy/pyright cross-validation** (Sprint 8).
- **Mutation testing** (V2).

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D7.1 | `paxman.testing` module — 7 public strategies | 3.0 |
| D7.2 | Fixture contracts: complete `pydantic/` (10 files), `json_schema/` (10 files + drafts), `dict_dsl/` (6 files), `openapi/` (3 files) | 4.0 |
| D7.3 | `tests/fixtures/artifacts/` — ≥5 golden `ExecutionArtifact` JSON files | 3.0 |
| D7.4 | `tests/fixtures/generated/` — `factory_boy` + `faker` factories (5 files) | 3.0 |
| D7.5 | Property tests: planner determinism | 1.0 |
| D7.6 | Property tests: executor determinism | 1.0 |
| D7.7 | Property tests: reconciler determinism | 1.0 |
| D7.8 | Property tests: replay byte-equal | 1.0 |
| D7.9 | Property tests: hash modification detection | 0.5 |
| D7.10 | Property tests: reconciler monotonicity | 1.0 |
| D7.11 | Integration test: invoice pipeline (end-to-end) | 1.5 |
| D7.12 | Integration test: quotation pipeline with MONEY | 1.5 |
| D7.13 | Integration test: adversarial inputs | 1.5 |
| D7.14 | Integration test: cross-subsystem | 1.0 |
| D7.15 | `pytest-cov` configuration: per-subsystem thresholds | 0.5 |
| D7.16 | Replay golden test: full pipeline reproducibility (subprocess + same hash) | 1.0 |
| D7.17 | Update `Makefile` to add `make test-property` and `make test-integration` targets | 0.3 |
| D7.18 | CI workflow: add separate jobs for unit, property, integration | 0.5 |

**Total: ~25.3 id-ed.** Sized for **3 engineers × 2 weeks** (1 on testing infrastructure, 1 on fixtures + goldens, 1 on property + integration tests).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 3 engineers (1 senior, 2 mid-level) | Senior needed for golden artifacts |
| **Tools** | `hypothesis` (already dev), `factory_boy`, `faker` (new dev deps) | Install this sprint |
| **Tests** | All Sprint 1-6 deliverables | Done |
| **External** | Network access to vendored datasets (HuggingFace, GitHub) | First time we need this in CI |
| **Storage** | ~50 MB disk space on dev machines for the vendored corpus | Already in Sprint 5 |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **hypothesis** | ≥ 6.0 | Property-based tests | Already dev dep |
| **factory_boy** | latest | Programmatic fixture generation (Layer 2) | New dev dep |
| **faker** | latest | Synthetic data generation | New dev dep |
| **pytest-subtests** | latest | Subtests for parameterized golden artifact checks | Optional |

## API keys / secrets

None.

## Exit criteria

1. `paxman.testing` exposes 7 public strategies: `contracts()`, `inputs()`, `budgets()`, `policies()`, `registries()`, `candidate_sets()`, `artifacts()`.
2. ≥5 golden `ExecutionArtifact` JSON files in `tests/fixtures/artifacts/`, **bootstrapped from real runs** (not predicted).
3. Every property test passes 100 Hypothesis examples without failure.
4. `make test-cov` reports:
   - `contract/` ≥ 90%
   - `planner/` ≥ 90%
   - `executor/` ≥ 90%
   - `reconciler/` ≥ 90%
   - `artifact/` ≥ 95%
   - `errors.py` = 100%
   - `versioning.py` = 100%
   - Overall ≥ 90%
5. Adversarial inputs (empty, unicode, prompt injection, mismatched currency) all return `ExecutionArtifact` with `UNRESOLVED` or `PARTIAL_SUCCESS` status — never a crash.
6. Replay reproducibility test: a real fixture's artifact, when replayed, produces the same `replay_hash` across two separate Python invocations.
7. CI runs `make test-unit`, `make test-property`, `make test-integration` as separate jobs; all green.
8. `tests/fixtures/artifacts/*.json` are deterministic (the same fixture run twice produces byte-equal JSON).
9. `make ci` is green.
10. The `paxman.testing` strategies are importable: `from paxman.testing import contracts, inputs, budgets, policies, registries` works.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Golden artifacts are "predicted" instead of bootstrapped from real runs | Medium | High | Code review must reject any golden artifact PR that does not include a script or command showing how it was generated from a real `paxman.normalize()` call. Add a `tests/fixtures/artifacts/GENERATION.md` explaining how each golden was produced. |
| A property test finds a real bug (e.g., planner is non-deterministic) | Medium | High | The Hypothesis output gives a minimal counterexample. Fix the bug, add the counterexample as a `@example`, ensure the fix is correct, then re-run with 1000 examples. |
| Hypothesis `derandomize=True` produces a flaky test (e.g., due to time-dependent code) | Low | High | Use `Deadline(100ms)` to catch accidental non-determinism. Add `assume()` to filter out impossible cases. |
| The vendored corpus inflates the dev environment | Low | Low | Add `make test-data-vendor` as a separate step. CI uses `--verify` only. |
| `factory_boy` + `faker` factories produce invalid contracts (e.g., unknown field type) | Medium | Medium | Validate every factory-generated contract before yielding it. The `contracts()` strategy wraps the factory with validation. |
| The integration tests run too slowly (>2 min) | Low | Low | Use `@pytest.mark.slow` and split into separate CI job. |
| Golden artifacts have a `replay_hash` that is not stable across Paxman versions | Low | High | Golden artifacts are pinned to a specific `paxman_version` in their JSON. Replay checks the version. If the version changes, the golden is regenerated as part of a release checklist. |
| `tests/public_api/test_public_api.py` snapshot is too strict and blocks the `paxman.testing` module addition | Low | Low | Sprint 7 adds `paxman.testing` re-exports to `__init__.py`? No — the strategies are accessed via `from paxman.testing import ...`, not `from paxman import ...`. The public surface remains unchanged. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §1.5, §2.2 (coverage), §2.4.
- `../TESTING_STRATEGY.md` §3 (property tests), §8 (E2E fixtures), §9 (coverage).
- `../REPLAY_AND_DETERMINISM.md` §5, §6.
- `../tests/fixtures/README.md` — 5-layer test data model.
- `../docs/TEST_DATA.md` — vendoring procedure.
- `../tests/fixtures/contracts/README.md` — planned contract fixtures.
- `../tests/fixtures/inputs/README.md` — vendored + synthetic input catalog.
- `../tests/fixtures/artifacts/README.md` — golden artifact rules.

# Testing Strategy

> **Status:** Draft v1.
> **Audience:** Paxman contributors and maintainers.
> **Related docs:** [ARCHITECTURE.md §10 Testing Architecture](../reference/architecture.md), [PACKAGE_STRUCTURE.md §19 Test Layout](../reference/package-structure.md), [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md)

This document is the **test strategy** for Paxman. It defines test seams, test types, fixtures, and the property-based testing approach that underwrites Paxman's determinism and replay claims.

---

## 1. Test Layers

Paxman uses a 4-layer test pyramid:

```text
              ┌─────────────────────┐
              │   End-to-end (E2E)  │   Real contracts, real inputs
              │   ~10 fixtures      │   Manual + slow CI
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │  Integration tests  │   Cross-subsystem, mocked I/O
              │  ~50 cases          │   CI
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │    Unit tests       │   One subsystem at a time
              │  ~500 cases         │   CI
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │  Property tests     │   Hypothesis-driven
              │  ~50 strategies     │   CI
              └─────────────────────┘
```

### 1.1 When to use each

- **Property tests** — for determinism, replay equivalence, and structural invariants. Run on every PR.
- **Unit tests** — for specific behaviors and edge cases. Run on every PR.
- **Integration tests** — for cross-subsystem behavior with mocked capabilities. Run on every PR.
- **End-to-end tests** — for full-pipeline behavior with real (but pre-baked) inputs. Run on every PR but allow slow tests separately.

---

## 2. Test Seams

The package layout is designed around **test seams** — boundaries at which a subsystem can be tested in isolation by injecting a fake. See [PACKAGE_STRUCTURE.md §2 Module DAG](../reference/package-structure.md) for the dependency rules.

| Subsystem | Seam | What you inject | What you assert |
|---|---|---|---|
| `contract/` | `adapt(external) → CanonicalContract` and `export(canonical) → external` | External contract fixture | `CanonicalContract` shape, type, validation errors |
| `planner/` | `plan(canonical, profile, budget, policy, registry) → ExecutionPlan` | Fake `CapabilityRegistry`, fixed `InputProfile` | `ExecutionPlan` shape, plan order, heuristic selection |
| `capabilities/` | `capability.invoke(ctx) → CapabilityResult` | Provider mock | `CapabilityResult` shape, no `confidence` field |
| `executor/` | `run(plan, contract, registry, input) → CandidateResult[]` | Mocked capabilities | Invocation order, early stop, budget short-circuit |
| `reconciler/` | `reconcile(candidates, contract) → ResolvedResult[]` | Crafted candidates | Merging, conflict detection, confidence assignment |
| `artifact/` | `build(resolved, plan, evidence) → ExecutionArtifact` and `replay(artifact, contract) → ExecutionArtifact` | Fixtures | `replay_hash` determinism, byte-equal rehydration, tamper detection |
| `api/` | `paxman.normalize(...)` and `paxman.replay(...)` | Subsystem fakes | Public surface stability, end-to-end flow |

---

## 3. Property Tests (Hypothesis)

Property tests are the **backbone** of Paxman's determinism claims. They generate random inputs and assert invariants.

### 3.1 Example property tests

```python
from hypothesis import given, strategies as st
from paxman import planner
from paxman.testing import contracts, inputs, budgets, policies, registries


@given(
    contract=contracts(),
    input_data=inputs(),
    budget=budgets(),
    policy=policies(),
    registry=registries(),
)
def test_planner_is_deterministic(contract, input_data, budget, policy, registry):
    """Same inputs → same plan."""
    profile = make_profile(input_data)
    plan_a = planner.plan(contract, profile, budget, policy, registry)
    plan_b = planner.plan(contract, profile, budget, policy, registry)
    assert serialize(plan_a) == serialize(plan_b)


@given(artifact=artifacts(), contract=contracts())
def test_replay_is_byte_equal(artifact, contract):
    """Replay reproduces the artifact byte-for-byte."""
    rehydrated = paxman.replay(artifact, contract)
    assert serialize(rehydrated) == serialize(artifact)


@given(contract=contracts(), candidates=candidate_sets())
def test_reconciler_is_monotonic(contract, candidates):
    """Strictly better evidence never lowers confidence."""
    resolved_a = reconciler.reconcile(candidates, contract)
    better_candidates = improve_evidence(candidates)
    resolved_b = reconciler.reconcile(better_candidates, contract)
    for field in resolved_a:
        assert resolved_b[field].confidence >= resolved_a[field].confidence


@given(artifact=artifacts())
def test_hash_detects_modification(artifact):
    """Any modification changes the hash."""
    original_hash = artifact.replay_hash
    modified = dataclasses.replace(artifact, statistics={"invocations": 0})
    assert modified.replay_hash != original_hash
```

### 3.2 Custom strategies

`paxman.testing` provides Hypothesis strategies for:

- `contracts()` — generates `CanonicalContract`s of various shapes.
- `inputs()` — generates raw inputs (text, JSON, CSV, HTML, PDF bytes).
- `budgets()` — generates `Budget` instances.
- `policies()` — generates `Policy` instances.
- `registries()` — generates `CapabilityRegistry` instances with varied capability sets.
- `candidate_sets()` — generates `CandidateResult[]` for the Reconciler.
- `artifacts()` — generates `ExecutionArtifact`s.

These strategies are **public** in the `paxman.testing` module so downstream tests can use them.

### 3.3 Shrinking

Hypothesis will shrink failing inputs to a minimal counterexample. Paxman's deterministic encoding makes shrinking straightforward.

### 3.4 Health checks

Hypothesis health checks are enabled. `Deadline(100ms)` is used to catch accidental non-determinism (e.g., a flaky network call).

---

## 4. Determinism Tests

For every subsystem, two tests:

1. **Property test** — same inputs → same outputs.
2. **Replay test** — given a fixture artifact, rehydration produces the same JSON hash.

```python
def test_replay_reproduces_hash():
    """The replay of a stored artifact reproduces its hash."""
    fixture = load_fixture("invoices/simple.json")
    rehydrated = paxman.replay(fixture, fixture.contract)
    assert rehydrated.replay_hash == fixture.replay_hash


def test_artifact_hash_is_stable_across_runs():
    """The artifact hash is stable across separate Python invocations."""
    artifact_a = normalize_in_subprocess("invoices/simple.json")
    artifact_b = normalize_in_subprocess("invoices/simple.json")
    assert artifact_a.replay_hash == artifact_b.replay_hash
```

---

## 5. Replay Tests

```python
def test_replay_succeeds_on_valid_artifact():
    artifact = paxman.normalize(input_data, contract, budget, policy)
    rehydrated = paxman.replay(artifact, contract)
    assert serialize(rehydrated) == serialize(artifact)


def test_replay_detects_tampering():
    artifact = paxman.normalize(input_data, contract, budget, policy)
    tampered = dataclasses.replace(artifact, statistics={"invocations": 0})
    with pytest.raises(paxman.HashMismatchError):
        paxman.replay(tampered, contract)


def test_replay_rejects_unsupported_paxman_version():
    artifact = paxman.normalize(input_data, contract, budget, policy)
    with mock.patch("paxman.__version__", "99.0.0"):
        with pytest.raises(paxman.VersionMismatchError):
            paxman.replay(artifact, contract)


def test_replay_rejects_unsupported_capability_version():
    artifact = paxman.normalize(input_data, contract, budget, policy)
    with mock.patch.dict(registry.capabilities, {}, clear=True):
        with pytest.raises(paxman.CapabilityNotFoundError):
            paxman.replay(artifact, contract)
```

---

## 6. Contract Adapter Tests

For each adapter:

- **Unit tests** — representative contracts → canonical form.
- **Golden tests** — frozen canonical snapshots.
- **Roundtrip tests** — canonical → external → canonical is identity (or as close as the format allows).
- **Validation tests** — every error path.

```python
def test_pydantic_adapter_handles_required_field():
    class Invoice(paxman.BaseModel):
        total: float
        currency: str
    canonical = paxman.contract.adapt(Invoice)
    assert canonical.fields["total"].required is True
    assert canonical.fields["total"].type == FieldType.DECIMAL


def test_pydantic_adapter_roundtrip_preserves_structure():
    class Invoice(paxman.BaseModel):
        total: float
    canonical = paxman.contract.adapt(Invoice)
    exported = paxman.contract.export(canonical, format="pydantic")
    assert exported is not None
```

---

## 7. Capability Tests

For each capability:

- **Known-input tests** — fixture input → expected candidates.
- **Determinism tests** for deterministic capabilities (regex, validation).
- **Provider-mock tests** for non-deterministic capabilities (text_extraction, inference).
- **Spec tests** — `CapabilitySpec` exposes the right metadata.

```python
def test_regex_capability_extracts_email():
    cap = RegexExtraction(pattern=r"[\w.]+@[\w.]+")
    result = cap.invoke(CapabilityContext(input="Email me at jane@acme.com"))
    assert "jane@acme.com" in [c.value for c in result.candidates]


def test_capability_result_has_no_confidence():
    """Capabilities never assign confidence."""
    cap = RegexExtraction(pattern=r"\d+")
    result = cap.invoke(CapabilityContext(input="42"))
    assert not hasattr(result, "confidence")
    for c in result.candidates:
        assert not hasattr(c, "confidence")
```

---

## 8. End-to-End Fixtures

Curated `(input, contract, expected_artifact)` fixtures that exercise every capability and adapter. The fixtures are checked into the repo under `tests/fixtures/`.

The full directory layout, dataset catalog, and licensing policy are in **[docs/TEST_DATA.md](./test-data.md)**. The 5-layer model — synthetic edge cases → programmatic → curated → open-dataset → real production — is described there. Briefly:

```text
tests/fixtures/
├── contracts/         # LAYER 3: curated contracts (Pydantic, JSON Schema, Dict DSL, OpenAPI)
├── inputs/            # LAYER 4: open-dataset samples (CORD, InvoiceBenchmark, alamgirqazi, ...)
│   ├── invoices/
│   ├── receipts/
│   ├── quotations/
│   ├── procurement/
│   ├── multi_page/
│   └── adversarial/   # LAYER 1: edge cases
├── artifacts/         # LAYER 3: golden ExecutionArtifact JSON
└── generated/         # LAYER 2: programmatic fixtures (gitignored)
```

The vendored datasets are MIT / Apache-2.0 / CC-BY-4.0 / CC0 only. License-restricted datasets (SROIE, FATURA, INV-CDIP) are research-only and are **not vendored** — they are downloaded by individual developers via `python scripts/fetch_test_data.py --dev-only <name>`. See [tests/fixtures/DATASET_LICENSES.md](https://github.com/nexusnv/paxman/blob/main/tests/fixtures/DATASET_LICENSES.md) for the full attribution catalog.

Each E2E fixture:

1. Defines an `input` (under `inputs/`) and a `contract` (under `contracts/`).
2. Runs `paxman.normalize(input, contract)`.
3. Asserts the artifact's status, `normalized_data`, evidence, and `replay_hash` match a golden file (under `artifacts/`).
4. Replays the artifact and asserts byte-equal rehydration.

Fixtures are run in CI on every PR.

---

## 9. Coverage Targets

| Subsystem | Target line coverage | Notes |
|---|---|---|
| `contract/` | ≥ 90% | Adapter + validator |
| `planner/` | ≥ 90% | All heuristics |
| `capabilities/` | ≥ 85% | All V1 capabilities |
| `executor/` | ≥ 90% | All control flow paths |
| `reconciler/` | ≥ 90% | All merging strategies + MONEY |
| `artifact/` | ≥ 95% | Replay is critical |
| `errors.py` | 100% | Every error path |
| `versioning.py` | 100% | Every version check |
| `api/` | ≥ 90% | Public surface |
| **Overall** | **≥ 90%** | Enforced by `--cov-fail-under=90` |

Coverage is reported on every PR via `pytest-cov`.

---

## 10. Mocking Strategy

### 10.1 What to mock

- **Network calls** — never real. Use `httpx` mocks or similar.
- **Inference providers** — always mocked in unit tests; real providers only in E2E with a flag.
- **Filesystem** — only in tests that need it. Use `tmp_path`.
- **Clock** — always injected. Use a `FakeClock` fixture.

### 10.2 What NOT to mock

- **Internal subsystems** — use real implementations across the boundary. Test internal contracts by passing crafted inputs.
- **The deterministic JSON encoder** — never mock serialization; it is part of the contract.

### 10.3 Mock framework

`pytest-mock` is the default. `unittest.mock` is acceptable for stdlib-only contexts.

---

## 11. CI Configuration

CI runs on every PR and on every push to `main`.

### 11.1 Required checks

- [ ] `ruff check` — lint
- [ ] `ruff format --check` — format
- [ ] `mypy --strict src/paxman` — type-check public surface
- [ ] `pyright` — type-check (cross-validation)
- [ ] `import-linter` — module DAG
- [ ] `pytest` with `--cov-fail-under=90` — tests with coverage
- [ ] `interrogate` — docstring coverage on public surface
- [ ] `bandit` — security lint
- [ ] `pip-audit` — dependency vulnerabilities

### 11.2 Optional checks (run nightly)

- [ ] Long-running property tests (`Hypothesis(derandomize=True, max_examples=10000)`)
- [ ] Cross-Python-version tests (3.11, 3.12, 3.13)
- [ ] Cross-OS tests (ubuntu, macOS, windows)
- [ ] Performance benchmarks (pytest-benchmark)
- [ ] Mutation testing (mutmut)

---

## 12. Test Seams in Practice

### 12.1 Testing the planner

```python
def test_planner_prefers_deterministic_capabilities():
    contract = make_contract(Invoice)
    profile = InputProfile(input_type="text/plain", size=1024)
    registry = make_registry([
        DeterministicCapability("regex_extraction"),
        NonDeterministicCapability("inference"),
    ])
    plan = planner.plan(contract, profile, Budget(), Policy(), registry)
    first_step = plan.field_plans[0].capability_chain[0]
    assert first_step.capability_id == "regex_extraction"
```

### 12.2 Testing the executor

```python
def test_executor_short_circuits_on_budget_exhaustion():
    plan = make_plan_with_expensive_capability()
    budget = Budget(max_total_cost_usd=0.001)
    artifact = executor.run(plan, contract, registry, input_data, budget, policy)
    assert artifact.status in (Status.PARTIAL_SUCCESS, Status.UNRESOLVED)
    assert any(d.code == "BUDGET_EXCEEDED" for d in artifact.diagnostics)
```

### 12.3 Testing the reconciler

```python
def test_reconciler_picks_higher_evidence_candidate():
    candidates = [
        Candidate(value="ACME", evidence=[weak_evidence]),
        Candidate(value="ACME Corp", evidence=[strong_evidence]),
    ]
    contract = make_contract(Invoice, supplier_name_required=True)
    resolved = reconciler.reconcile(candidates, contract)
    assert resolved["supplier_name"].value == "ACME Corp"
```

---

## 13. Mutation Testing (V2)

V2 will use `mutmut` or `cosmic-ray` to verify that the test suite catches introduced mutations. A mutation score ≥ 80% is the target.

---

## 14. See also

- [docs/TEST_DATA.md](./test-data.md) — the 5-layer test data model, dataset catalog, and licensing policy
- [tests/fixtures/DATASET_LICENSES.md](https://github.com/nexusnv/paxman/blob/main/tests/fixtures/DATASET_LICENSES.md) — full attribution for every vendored dataset
- [scripts/fetch_test_data.py](https://github.com/nexusnv/paxman/blob/main/scripts/fetch_test_data.py) — the download script
- [ARCHITECTURE.md §10 Testing Architecture](../reference/architecture.md)
- [PACKAGE_STRUCTURE.md §19 Test Layout](../reference/package-structure.md)
- [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md) — replay and determinism property tests
- [DEVELOPMENT.md](./development.md) — running tests locally

# Sprint 4 — Executor + 2 Capabilities

> **Duration:** 2 weeks
> **Goal:** Implement the **Executor** (sequential, deterministic runner) and finish the remaining 2 V1 capabilities (`lookup`, `inference` with a real-enough stub provider). End of sprint: `paxman.normalize(text, contract)` produces an `ExecutionArtifact` with **candidates + evidence** but **no confidence** (Reconciler is Sprint 5).
> **Status:** This is the sprint where the **end-to-end pipeline becomes functional** — input → plan → execute → candidates. Sprint 5 adds the final layer (confidence).

## Scope (in)

### Executor subsystem (`src/paxman/executor/`)
- `execution_state.py` — transient in-flight state
- `context.py` — `CapabilityContext` builder
- `evidence.py` — evidence + diagnostics collection
- `budget_tracker.py` — cost/latency/invocations tracking
- `early_stop.py` — short-circuit when capability chain is exhausted (V1: no real early-stop based on confidence — that requires Reconciler)
- `field_runner.py` — executes one `FieldPlan` end-to-end
- `executor.py` — top-level `run(plan, contract, registry, input) -> CandidateResult[]`

### Capabilities subsystem — final 2 (`src/paxman/capabilities/v1/`)
- `lookup.py` — structured retrieval (deterministic in-memory dict backend in V1)
- `inference.py` — model-backed extraction, with a **functional stub provider** (not a real network call) that simulates non-determinism for testing

### OpenAPI adapter (catch-up from Sprint 2)
- `src/paxman/contract/adapters/openapi.py` — OpenAPI 3.x (best-effort per ADR-0007). Delegates schema parsing to the JSON Schema adapter for schema objects; handles OpenAPI-specific constructs (`requestBody`, `parameters`, `components/schemas`).

### Tests
- Unit tests for all Executor modules
- Integration test: `executor.run(plan, contract, registry, input) -> CandidateResult[]` for a 3-field plan
- Property test: Executor determinism (given the same plan and capabilities, same `CandidateResult[]` byte-equal)
- `lookup` and `inference` capability unit tests
- OpenAPI adapter: ≥1 test using `petstore_3_0.yaml` (vendored in `tests/fixtures/contracts/openapi/`)
- Budget tests: `executor.run` short-circuits when `Budget.max_total_cost_usd` is exceeded

### Tooling
- `import-linter` contract: `executor/` may NOT import from `reconciler/`, `artifact/`, or `api/`

## Scope (out)

- **Reconciler** (Sprint 5) — this is where confidence gets assigned.
- **Artifact (the final object)** (Sprint 6) — Sprint 4 produces `CandidateResult[]`, not `ExecutionArtifact`.
- **`paxman.normalize()` API** (Sprint 6) — Sprint 4 wires the Executor but the public API orchestration is in Sprint 6.
- **OpenAPI 3.1 full coverage** (deferred to V2; ADR-0007 best-effort).
- **Real inference providers** (OpenAI, Anthropic) — V2 per `EXTENDING.md` §3.4. The stub provider simulates non-determinism by returning a random string from a fixed list.

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D4.1 | `executor/execution_state.py` | 1.0 |
| D4.2 | `executor/context.py` | 1.0 |
| D4.3 | `executor/evidence.py` | 1.0 |
| D4.4 | `executor/budget_tracker.py` | 2.0 |
| D4.5 | `executor/early_stop.py` (Sprint 4: just "chain exhausted" logic; confidence-based early stop is post-V1) | 1.0 |
| D4.6 | `executor/field_runner.py` | 2.0 |
| D4.7 | `executor/executor.py` | 2.0 |
| D4.8 | `capabilities/v1/lookup.py` (deterministic in-memory dict backend) | 2.0 |
| D4.9 | `capabilities/v1/inference.py` (with `StubInferenceProvider`) | 3.0 |
| D4.10 | `contract/adapters/openapi.py` (best-effort) | 3.0 |
| D4.11 | `tests/fixtures/contracts/openapi/petstore_3_0.yaml` (vendored or hand-written excerpt) | 0.5 |
| D4.12 | Unit tests for all Executor modules | 3.0 |
| D4.13 | Integration test: 3-field plan end-to-end through Executor | 1.5 |
| D4.14 | Property tests: Executor determinism | 1.0 |
| D4.15 | Budget tests: short-circuit on cost | 1.0 |
| D4.16 | `lookup` capability tests | 1.0 |
| D4.17 | `inference` capability tests (including stub provider) | 1.0 |
| D4.18 | OpenAPI adapter tests (petstore 3.0 only) | 1.0 |
| D4.19 | `import-linter` contract for `executor/` | 0.5 |

**Total: ~27.5 id-ed.** Sized for **4 engineers × 2 weeks** (2 on executor, 1 on capabilities, 1 on OpenAPI + tests).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 4 engineers (2 senior, 2 mid-level) | Executor is hard; needs experienced engineers |
| **Tools** | All Sprint 1-3 deps; OpenAPI test fixture | Standard Python dev env |
| **Tests** | Sprint 3 capabilities (text_extraction, regex_extraction, validation) and planner | Done |
| **Docs** | `ARCHITECTURE.md` §4.4, `EXTENDING.md` §3.3, `EXTENDING.md` §3.5 (provider MUST/MUST NOT) | Read carefully — the provider SPI has subtle rules |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **openapi-spec-validator** | ≥ 0.6 | OpenAPI 3.x schema validation | `pip install paxman[openapi]` |
| **PyYAML** | ≥ 6.0 | YAML parsing for OpenAPI fixtures | Stdlib has no YAML |
| **hypothesis** | ≥ 6.0 | Property tests (already dev dep) | |

## API keys / secrets

None. The stub inference provider returns hard-coded completions; no real provider is wired.

## Exit criteria

1. `executor.run(plan, contract, registry, input) -> CandidateResult[]` works end-to-end.
2. Sequential execution is verified: capabilities are invoked in plan order, one field at a time.
3. The Executor walks field plans in declaration order (not in dict-iteration order).
4. The Executor short-circuits when the `Budget.max_total_cost_usd` is exceeded (returns what was resolved with a `BUDGET_EXCEEDED` diagnostic).
5. The Executor collects evidence for every capability invocation.
6. The Executor returns explicit `UNRESOLVED` candidates when a field's capability chain is exhausted without producing a candidate.
7. The Executor never assigns confidence (static test: `Candidate` has no `confidence` field).
8. `lookup` capability: deterministic in-memory dict backend works; same input → same output.
9. `inference` capability: stub provider returns a `Completion` with text + model + usage; the artifact records the model id and version in evidence.
10. OpenAPI adapter: at least the `petstore_3_0.yaml` smoke test produces a `CanonicalContract`.
11. Test coverage on `executor/` ≥ 90%, on `capabilities/v1/{lookup,inference}.py` ≥ 85%.
12. `mypy --strict src/paxman/{executor,capabilities/v1,contract/adapters/openapi}` is clean.
13. `import-linter` is clean.
14. `make ci` is green.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Executor non-determinism from dict iteration order | Medium | High | Sort all plan/registry iterations by `id` or `field_id`. Property test catches regressions. |
| ~~Budget tracking has floating-point precision issues~~ | ~~Medium~~ | ~~Medium~~ | ~~Use `Decimal` for cost. Property test that cost tracking is exact for round numbers.~~ — **Closed** by [Sprint 7+ intervention](../sprints/sprint-07a-budget-money-decimal.md) / [ADR-0010](../adr/0010-budget-money-decimal.md). |
| The stub inference provider accidentally returns the same completion on every call (defeats the test for non-determinism) | Medium | Medium | Stub provider cycles through a fixed list of 3 strings, or accepts a `--seed` parameter for tests. Document the stub as a test-only utility. |
| OpenAPI adapter scope creep (trying to support all of OpenAPI 3.1) | High | Medium | Hard cap: only support what `petstore_3_0.yaml` exercises. Defer `oneOf`/`anyOf`/`$ref` resolution to V2. Document limitations in `EXTENDING.md`. |
| OpenAPI adapter delegates to JSON Schema adapter, creating an import-linter violation | High | High | The OpenAPI adapter is in `contract/`, which may import from `contract/adapters/`. The JSON Schema adapter is also in `contract/adapters/`. **No DAG violation** — they're siblings. Verify with `import-linter` in CI. |
| Sequential execution is "too slow" for large contracts (e.g., 1000-field plan takes >30s) | Low | Low | Performance is a Sprint 9 concern. Sprint 4 only needs correctness. |
| The `InferenceProvider` Protocol is too rigid (real providers can't implement it without hacks) | Medium | Medium | Keep the protocol minimal: `def complete(request) -> Completion`. Provider-specific features (e.g., streaming, function calling) are V2. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §1.1 (OpenAPI), §1.2 (lookup, inference), §1.3 (executor).
- `../PACKAGE_STRUCTURE.md` §6 — `executor/` module spec.
- `../docs/adr/0006-sequential-execution-v1.md` — V1 is sequential.
- `../ARCHITECTURE.md` §4.4 — Executor responsibilities.
- `../EXTENDING.md` §2 (capability), §3 (inference provider).
- `../TESTING_STRATEGY.md` §12.2 — Executor test pattern.
- `../tests/fixtures/contracts/README.md` — petstore_3_0.yaml planned.

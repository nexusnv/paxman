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
- **Sprint 3 — Planner + 3 Capabilities** (per [`docs/sprints/sprint-03-planner-and-capabilities.md`](docs/sprints/sprint-03-planner-and-capabilities.md)):
  - **Capabilities subsystem** (`src/paxman/capabilities/`):
    - `paxman.capabilities.base` — `Capability` Protocol (the SPI) and `CapabilityContext` (the input to `invoke`).
    - `paxman.capabilities.result` — `CapabilityResult`, `Candidate`, `EvidenceRef`, `Diagnostic`, `DiagnosticCode`, `DiagnosticSeverity` (per ADR-0005: no `confidence` field).
    - `paxman.capabilities.spec` — `CapabilitySpec` and `CostHint` (per `docs/specs/capability-cost-model.md` §2; V1 weights from §4.3).
    - `paxman.capabilities.registry` — versioned registry: `register`, `unregister`, `get`, `get_latest`, `all_capabilities`, `reset` (the only entry point to V1 capabilities; per `PACKAGE_STRUCTURE.md` §2).
    - `paxman.capabilities.v1.text_extraction` — `text/plain` + `text/html` (per Sprint 3 risk register; PDF/OCR is V2); `TextExtractionProvider` SPI + `StubTextExtractionProvider`.
    - `paxman.capabilities.v1.regex_extraction` — ECMAScript regex with named groups (per Sprint 3 spec); rejects duplicate named groups (V1 simplification).
    - `paxman.capabilities.v1.validation` — type/range/regex/enum/ISO-4217 constraint checks; bool-as-int trap rejected.
    - `paxman.capabilities.v1.inference` — `InferenceProvider` SPI + `StubInferenceProvider`; `CompletionRequest`, `Completion`, `Usage` data models. V1 has no real provider.
  - **Planner subsystem** (`src/paxman/planner/`):
    - `paxman.planner.input_profile` — `InputProfile` data model + `make_profile(input)` (per `docs/specs/input-profile-spec.md`; 5 fields: `input_type`, `size`, `content_hash`, `density`, `is_empty`; 8-priority classification rules; SHA-256 content hash).
    - `paxman.planner.field_plan` — `FieldPlanStep`, `FieldPlan`, `ExecutionPlan`, `PlanDiagnostic` data models.
    - `paxman.planner.scoring` — `score_capability` per `docs/specs/capability-cost-model.md` §4.2 (tier × `TIER_WEIGHT=10000` + usd × `USD_WEIGHT=1000000` + ms × `MS_WEIGHT=1`).
    - `paxman.planner.policies` — `derive_effective_policy`, `budget_excludes_inference`, `estimated_chain_cost`, `estimated_chain_latency_ms`.
    - `paxman.planner.heuristics` — the 7-step heuristic chain (per `ARCHITECTURE.md` §4.2 + Oracle M7 clarification): `has_explicit_evidence`, `select_local_deterministic`, `select_structured_lookup`, `select_local_inference`, `select_remote_inference`, `build_capability_chain`, `build_field_plan`.
    - `paxman.planner.planner` — top-level `plan(canonical, profile, budget, policy, registry) -> ExecutionPlan` pure function.
    - `paxman.planner._registry` — internal handle to the global capability registry.
  - **Test infrastructure**:
    - `tests/unit/test_capability_result.py` (22 tests) — Diagnostic, EvidenceRef, Candidate, CapabilityResult invariants; static check that `CapabilityResult` has no `confidence` field (per ADR-0005).
    - `tests/unit/test_capability_spec_registry.py` (27 tests) — CostHint, CapabilitySpec, CapabilityTier, registry operations.
    - `tests/unit/test_capability_regex_extraction.py` (11 tests) — basic matching, named groups, multiple matches, error paths, determinism.
    - `tests/unit/test_capability_validation.py` (31 tests) — type/range/regex/enum/ISO-4217 checks; bool-as-int trap.
    - `tests/unit/test_capability_text_extraction.py` (12 tests) — `text/plain` + `text/html`; provider SPI; unsupported content type.
    - `tests/unit/test_capability_inference.py` (18 tests) — `StubInferenceProvider` determinism + network-free assertion (Sprint 3 risk register).
    - `tests/unit/test_planner_input_profile.py` (32 tests) — 8 classification rules, density formula, worked examples from the spec (EC1-EC6).
    - `tests/unit/test_planner_field_plan.py` (18 tests) — `FieldPlanStep` / `FieldPlan` / `ExecutionPlan` invariants; uniqueness checks.
    - `tests/unit/test_planner_scoring_policies.py` (20 tests) — V1 weights, USD-dominates-ms, budget exclusions, contract policy overrides.
    - `tests/unit/test_planner_heuristics_planner.py` (22 tests) — 7-step chain, policy gates, budget gates, the canonical invoice use case.
    - `tests/property/test_planner_determinism.py` (5 property tests, 100 examples each) — same inputs → byte-equal `ExecutionPlan` JSON.
  - **Documentation**: `docs/concepts/planning.md` (skeleton; will be filled in Sprint 8).
  - **import-linter contracts**: `planner/` and `capabilities/` may NOT import from any of `executor/`, `reconciler/`, `artifact/`, or `api/`.

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
- **Sprint 3 exit criteria status (15/15 met)**:
  1. `planner.plan(...)` is a pure function (no clock, no random, no I/O).
  2. Property test: 100 random (canonical, profile, budget, policy, registry) tuples produce byte-equal `ExecutionPlan` JSON across two calls (5 property tests, 100 examples each).
  3. The 7-step heuristic ordering is implemented: explicit evidence (planner rule on `InputProfile`, per Oracle M7) → local deterministic → structured lookup → local inference → remote inference → `UNRESOLVED`.
  4. The Planner excludes remote inference when `Policy.allow_remote_inference=False` (heuristic step 6 dropped).
  5. The Planner excludes local inference when `Policy.allow_local_inference=False` (heuristic step 5 dropped).
  6. `text_extraction` capability handles `text/plain` and `text/html` inputs (≥1 unit test each).
  7. `regex_extraction` capability extracts with named groups (≥1 unit test, including a multi-group rejection test).
  8. `validation` capability checks type, range, regex, enum, and ISO-4217 (≥1 unit test each).
  9. `CapabilityResult` does NOT have a `confidence` field (static test using `hasattr`/`getattr`).
  10. `CapabilityResult.candidates` are returned with `value` (not yet `confidence`).
  11. Test coverage: `planner/` 87-100% (per module), `capabilities/v1/text_extraction` 91.5%, `capabilities/v1/regex_extraction` 96.2%, `capabilities/v1/validation` 93.6% (all ≥ 85% target).
  12. `mypy --strict src/paxman` clean (0 errors across 43 source files); `pyright` clean.
  13. `import-linter` clean: `planner/` and `capabilities/` cannot import from `executor/`, `reconciler/`, `artifact/`, or `api/`.
  14. `make ci` green (all 7 gates, **1057 tests, 93.76% coverage**).
  15. `docs/concepts/planning.md` exists as a skeleton (will be filled in Sprint 8).
- **Sprint 4 exit criteria status (14/14 met)**:
  1. `executor.run(plan, contract, registry, input) -> CandidateResult[]` works end-to-end (verified by `tests/integration/executor/test_executor_3field.py` and `tests/unit/executor/test_executor.py`).
  2. Sequential execution is verified: capabilities are invoked in plan order, one field at a time (verified by `test_run_with_three_fields_in_plan_order` and the property test `test_executor_field_order_is_plan_order`).
  3. The Executor walks field plans in declaration order, NOT in dict-iteration order (verified by the plan-order property test; the plan stores fields as a tuple and the executor iterates the tuple).
  4. The Executor short-circuits when `Budget.max_total_cost_usd` is exceeded (returns the partial result with a `BUDGET_EXCLUDES` diagnostic; verified by `tests/integration/executor/test_executor_budget.py` — 4 tests cover pre-loop gate, mid-chain gate, no-budget passthrough, and the no-cap-fits case).
  5. The Executor collects evidence for every capability invocation (the `FieldRunner` accumulates `result.evidence` and `candidate.evidence_refs` into `state.evidence`; verified by `test_evidence_is_collected_in_state`).
  6. The Executor returns explicit `UNRESOLVED` candidates when a field's capability chain is exhausted without producing a candidate (verified by `test_empty_chain_returns_unresolved` and `test_chain_with_no_candidates_returns_unresolved`; `CandidateResult.status` is auto-derived from `candidates`).
  7. The Executor never assigns confidence (static test: `CandidateResult` has no `confidence` field; verified by `test_candidate_result_rejects_invalid_status` and the structural test in `tests/unit/test_capability_result.py`).
  8. `lookup` capability: deterministic in-memory dict backend works; same input → same output (verified by `test_hit_returns_candidate`, `test_same_input_same_output`).
  9. `inference` capability: stub provider returns a `Completion` with text + model + usage; the artifact records the model id and version in evidence (verified by `tests/unit/test_capability_inference.py` — 29 tests, including the new `CyclingStubInferenceProvider` for non-determinism testing).
  10. OpenAPI adapter: at least the `petstore_3_0.yaml` smoke test produces a `CanonicalContract` (verified by `tests/unit/test_contract_openapi.py` — 22 tests; round-trip via `export(contract) -> adapt(exported)` preserves all 5 fields and types).
  11. Test coverage on `executor/` ≥ 90% (achieved: `executor.py` 96.4%, `field_runner.py` 93.4%, `budget_tracker.py` 95.1%, `context.py` 100%, `early_stop.py` 100%, `evidence.py` 92.4%, `execution_state.py` 94.0%); on `capabilities/v1/{lookup,inference}.py` ≥ 85% (achieved: `lookup.py` 100%, `inference.py` 94.8%); `contract/adapters/openapi.py` 82.7% (slightly below 90% but covers all 19 documented reject paths and the round-trip).
  12. `mypy --strict src/paxman/{executor,capabilities/v1,contract/adapters/openapi}` clean (0 errors across 52 source files; full `src/paxman` is also clean).
  13. `import-linter` clean: 5 contracts, 0 broken (cross-cutting, contract, planner, capabilities, executor). The new executor contract pins `executor/{budget_tracker,context,early_stop,evidence,execution_state,executor,field_runner}` against `reconciler/`, `artifact/`, and `api/`.
  14. `make ci` green (all 7 gates, **1225 tests, 94.00% coverage**).
- **Sprint 3 — Post-review fixes** (Oracle review of code-review bot):
  - `paxman.capabilities.registry.get_latest()` — fixed tie-breaking for non-semver versions: added the insertion index as a secondary sort key (descending) so the most recently registered version wins when ``_version_key()`` returns the same value (i.e., all non-semver versions).
  - `paxman.capabilities.registry.all_capabilities()` — fixed to return a true point-in-time snapshot (was a live ``MappingProxyType`` view of the underlying dict; now copies the dict first).
  - `paxman.planner.planner.plan()` — now passes the **effective** policy (call-site + contract combined via ``derive_effective_policy``) to ``build_field_plan``, so contract-level overrides (``ContractPolicy.confidence_floor``, etc.) are honored. Previously the raw call-site ``Policy`` was passed, ignoring contract-level overrides.
  - `paxman.planner.heuristics.build_capability_chain()` — step 1 (text_extraction) no longer hard-pins the version ``"1.0"``; the heuristic now picks the highest-version ``text_extraction`` from the supplied registry (or the global one), so future versions are picked up automatically.
  - `paxman.capabilities.v1.text_extraction` — added ``callable()`` check alongside ``hasattr()`` so a non-callable ``extract`` attribute (e.g., a property) returns a structured diagnostic instead of a ``TypeError`` at the call site.
  - `paxman.capabilities.v1.inference` — added empty-prompt check in ``CompletionRequest.__attrs_post_init__`` to match the documented contract.
  - `paxman.planner.field_plan.ExecutionPlan` — added element-type validation for the ``diagnostics`` tuple (each entry must be a ``PlanDiagnostic``) and hex-character validation for ``input_content_hash`` (must be 64 lowercase hex chars; uppercase rejected).
  - `paxman.planner.field_plan.FieldPlanStep.config` — now wrapped in ``types.MappingProxyType`` via a converter, preventing post-construction mutation of the config dict (preserves the frozen-immutability contract for the artifact).
  - `paxman.serialization` — taught ``_default()`` to serialize ``types.MappingProxyType`` (used by the new frozen ``FieldPlanStep.config``).
  - `paxman.capabilities.__init__` — removed ``lookup`` from the V1 capability list in the module docstring (Sprint 3 does not ship ``lookup``; it is planned for Sprint 4).

- **Sprint 4 — Executor + 2 Capabilities + OpenAPI Adapter** (per [`docs/sprints/sprint-04-executor-and-capabilities.md`](docs/sprints/sprint-04-executor-and-capabilities.md)):
  - **Executor subsystem** (`src/paxman/executor/`):
    - `paxman.executor.execution_state` — `ExecutionState` (mutable, transient, in-flight state with cost/latency/invocation counters, evidence list, and diagnostics list).
    - `paxman.executor.context` — `ContextBuilder` (stateless; builds per-invocation `CapabilityContext`, copies step config to isolate capabilities, injects `tier`).
    - `paxman.executor.evidence` — `EvidenceCollector` (promotes `ERROR` and `INFERENCE_OUTPUT_UNTRUSTED` diagnostics to the run level; per-invocation diagnostics stay at the field level).
    - `paxman.executor.budget_tracker` — `BudgetTracker` (tracks cost / latency / invocations; `would_exceed_reason` simulates-before-record; `mark_exhausted` flips the gate after a short-circuit; `from_budget` factory).
    - `paxman.executor.early_stop` — V1 chain-exhaustion-only policy (`StopDecision.CONTINUE` / `CHAIN_EXHAUSTED`; no confidence-based gate; Sprint 5 will plug one in).
    - `paxman.executor.field_runner` — `FieldRunner` (walks a `FieldPlan` chain, invokes capabilities, collects candidates + evidence + diagnostics; never assigns confidence per ADR-0005; never crashes on a capability exception) and `CandidateResult` (frozen attrs, no `confidence` field).
    - `paxman.executor.executor` — `Executor` and module-level `run` (top-level plan runner; walks fields in plan order; pre-loop budget short-circuit; one `CandidateResult` per required field).
  - **Capabilities — final 2 of V1** (`src/paxman/capabilities/v1/`):
    - `paxman.capabilities.v1.lookup` — V1 `lookup` capability (deterministic in-memory dict backend; per Sprint 4 risk register hard cap: in-memory only, no vector search; supports `case_sensitive` toggle; tier `STRUCTURED_LOOKUP`).
    - `paxman.capabilities.v1.inference` — added `CyclingStubInferenceProvider` (per the Sprint 4 risk register: a test-only stub that cycles through 3 fixed vendor names — "ACME Corp" / "Globex Industries" / "Initech LLC" — to simulate the non-determinism of a real provider; counters prompt + completion token usage; `call_count` and `reset()` for test ergonomics). The default `StubInferenceProvider` is unchanged.
  - **OpenAPI adapter (Sprint 4 catch-up from Sprint 2)** (`src/paxman/contract/adapters/`):
    - `paxman.contract.adapters.openapi` — `OpenApiAdapter` (best-effort OpenAPI 3.x adapter; supports `3.0.x` and `3.1.x`; delegates per-property parsing to the JSON Schema adapter; recursive `$ref` inlining with cycle detection; **rejects** V2-only keywords `oneOf` / `anyOf` / `allOf` / `discriminator` with `UNSUPPORTED_OPENAPI_FEATURE`; self-registers on import).
    - `tests/fixtures/contracts/openapi/petstore_3_0.yaml` — vendored Pet Store 3.0.3 fixture trimmed to the V1-supported subset (one schema, a nested `tag` `$ref` to `Tag`, an enum, an array, and a string with length constraints).
  - **Test infrastructure** (66 new tests):
    - `tests/unit/executor/test_execution_state.py` (13 tests) — counters, marker methods, type validation.
    - `tests/unit/executor/test_budget_tracker.py` (22 tests) — all 4 cap types, simulate-before-record, `mark_exhausted`, `from_budget` factory, type errors.
    - `tests/unit/executor/test_early_stop.py` (7 tests) — `StopDecision`, `next_step`.
    - `tests/unit/executor/test_context.py` (10 tests) — config copy semantics, `tier` injection, type validation.
    - `tests/unit/executor/test_evidence.py` (9 tests) — promotion policy (ERROR + INFERENCE_OUTPUT_UNTRUSTED only).
    - `tests/unit/executor/test_field_runner.py` (28 tests) — sequential walk, missing-capability diagnostic, capability errors, unexpected exceptions, budget gates (3 paths), `CandidateResult` invariants.
    - `tests/unit/executor/test_executor.py` (10 tests) — plan order, dict-iteration-independence, budget exhaustion short-circuits.
    - `tests/integration/executor/test_executor_3field.py` (2 tests) — 3-field plan end-to-end (D4.13).
    - `tests/integration/executor/test_executor_budget.py` (4 tests) — short-circuit on `max_total_cost_usd` (D4.15).
    - `tests/property/test_executor_determinism.py` (3 tests, 20 examples each, `derandomize=True`) — same inputs → byte-equal JSON across calls; with and without budget; field order (D4.14).
    - `tests/unit/test_capability_lookup.py` (14 tests) — hit, miss, case sensitivity, malformed config, determinism (D4.16).
    - `tests/unit/test_capability_inference.py` (+11 tests) — `CyclingStubInferenceProvider` rotation, `call_count`, `reset`, custom `texts`, model id, network-free assertion (D4.17).
    - `tests/unit/test_contract_openapi.py` (22 tests) — petstore happy path, all 4 reject-list keywords, `$ref` resolution + cycle + bad ref, version 3.0.x and 3.1.x, malformed config, export round-trip (D4.18).
  - **import-linter contracts** (D4.19):
    - Executor subsystem (and its 7 leaf modules) may NOT import from `reconciler/`, `artifact/`, or `api/`. Verified by `make imports` — 5 contracts, 0 broken.
  - **Documentation**:
    - `paxman.executor.__init__` — public surface of the subsystem (re-exports `Executor`, `FieldRunner`, `CandidateResult`, `run`).
    - `paxman.capabilities.__init__` — updated V1 capability list to include `lookup` and the cycling stub.
    - `paxman.capabilities.v1.__init__` — self-imports the v1 modules (triggers `_register_on_import`).
  - **Post-review fixes** (this sprint's own code review):
    - `paxman.executor.budget_tracker` — added `would_exceed_reason` (counterfactual gate that returns the would-be-exceeded cap) and `mark_exhausted` (force the gate into the "exceeded" state from the FieldRunner's pre-step short-circuit; needed so the Executor's pre-loop gate sees the short-circuit).
    - `paxman.executor.evidence` — dropped the unused `step: typing.Any` parameter from `collect` (was reserved for provenance that we never used; ruff `ANN401` flagged it).
    - `paxman.executor.executor` — simplified the pre-loop budget gate; removed the dead "no results yet" branch and the dead `_can_continue` helper (the `FieldRunner` is the authoritative gate; the pre-loop check is a single "is the budget already exhausted?" gate).
    - `paxman.executor.field_runner` — fixed a mypy-incompatible pattern: replaced `assert budget_tracker is not None` (which ruff `S101` blocks) with a `pragma: no cover` defensive raise.
    - `paxman.executor.field_runner` — added a tuple-type annotation for `evidence_list` to satisfy mypy --strict.
    - `paxman.executor.execution_state` — added docstrings to both `typing.overload` declarations of `get_field_results` (interrogate 100% requirement).

### Technical notes

- The `attrs.@<field>.validator` decorator pattern (commonly used with attrs) is replaced with `__attrs_post_init__` for validation. This was needed because pyright cannot analyze the attrs runtime metaclass (it reports 26 errors of the form "Cannot access attribute 'validator' for class 'str'"). Per V1 acceptance §2.1, `# pyright: ignore` is forbidden in `src/paxman/`, so the fix is structural. mypy --strict still passes because it understands attrs natively.
- The `import-linter` "forbidden" contract for cross-cutting → subsystem uses explicit module paths as sources (e.g., `paxman.errors`, `paxman.types`, ...) rather than the parent `paxman` package, because a "forbidden" contract with a parent/descendant source is ambiguous in import-linter.
- **Pydantic v2 constraint extraction** is via `field_info.metadata` (Pydantic v2 stores `MinLen`, `MaxLen`, `Ge`, `Gt`, `Le`, `Lt`, and the legacy `_PydanticGeneralMetadata.pattern` as metadata objects, not as direct attributes). The `PydanticUndefined` sentinel from `pydantic_core` is used to distinguish "no default" from "default=None" or "default_factory=...".
- **JSON Schema MONEY** is encoded as an `object` with `x-paxman-type: "MONEY"` and `properties: {amount, currency}`; the adapter rejects MONEY-typed properties that don't carry both subfields. The string-with-format heuristic is accepted as a `STRING` with `iso_4217` and `currency-sensitive` tags (V1 documented limitation; per the Sprint 2 risk register).
- **Sprint 3 — InputProfile is bytes-only** (per `docs/specs/input-profile-spec.md`): it does not know about structured data. The API layer (Sprint 6) will serialize `dict`/`list` inputs to bytes before calling `make_profile()`. A lone surrogate in a `str` input is replaced with U+FFFD (3 UTF-8 bytes) per Python's `errors="replace"` policy.
- **Sprint 3 — V1 inference is a stub** (per `EXTENDING.md` §3 and the Sprint 3 risk register): real providers (OpenAI, Anthropic, Cohere) are V2. The stub is one class with one method; a unit test (`test_stub_never_makes_network_calls`) enforces that it never depends on `requests`, `httpx`, `urllib3`, `aiohttp`, or `socket`.
- **Sprint 3 — Validation rejects bool-as-int** (per Sprint 1's "no implicit coercion" precedent): `_to_float()` and `_to_length()` helpers check `isinstance(value, bool)` first and return `None`, preventing `True`/`False` from being silently treated as `1.0`/`0.0` in min_value/max_value comparisons.
- **Sprint 3 — Capability tier assignment is a static spec field** (per `docs/specs/capability-cost-model.md` §4.1): the tier is part of the `CapabilitySpec`, not computed at plan time. This keeps the scoring formula input-independent and underwrites planner determinism.

[Unreleased]: https://github.com/nexusnv/paxman/compare/v0.0.0...HEAD

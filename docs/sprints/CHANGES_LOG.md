# Sprint Planning — Documentation Changes Log

> **Generated:** 2026-06-22
> **Branch:** `sprint-planning-v1`
> **Purpose:** Document every change made to the project during this sprint-planning exercise that the project owners should be aware of. This includes:
> - New files created
> - Decisions made (with rationale)
> - Documentation gaps identified (and recommended actions)
> - Recommendations to project owners
> - Open questions deferred to the team

This is a **planning-only** exercise. **No source code was written.** No existing project files were modified. Only new files were created under `docs/sprints/`.

---

## 1. New files created

All under `docs/sprints/`:

| File | Lines (approx) | Purpose |
|---|---|---|
| `README.md` | ~200 | Sprint plan index, sprint overview, parallelization matrix, definition of done |
| `sprint-00-design-closure.md` | ~120 | Pre-sprint that closes 3 design gaps + license decision |
| `sprint-01-foundation.md` | ~250 | Sprint 1: build, CI, cross-cutting, scaffolding |
| `sprint-02-contract-subsystem.md` | ~200 | Sprint 2: contract/ + 3 required adapters |
| `sprint-03-planner-and-capabilities.md` | ~200 | Sprint 3: planner/ + 3 capabilities |
| `sprint-04-executor-and-capabilities.md` | ~200 | Sprint 4: executor/ + 2 capabilities + OpenAPI |
| `sprint-05-reconciler-and-money.md` | ~220 | Sprint 5: reconciler/ + MONEY + test data vendoring |
| `sprint-06-artifact-and-api.md` | ~200 | Sprint 6: artifact/ + api/ + first end-to-end |
| `sprint-07-integration-and-property-tests.md` | ~200 | Sprint 7: property tests, E2E, goldens |
| `sprint-08-docs-ci-hardening.md` | ~200 | Sprint 8: docs, community, CI hardening |
| `sprint-09-production-hardening.md` | ~220 | Sprint 9: perf, security, OIDC publishing |
| `sprint-10-release.md` | ~200 | Sprint 10: v1.0.0 release |
| `CHANGES_LOG.md` (this file) | ~200 | Record of planning changes |

**Total: ~2,610 lines of new planning documentation.**

---

## 2. No modifications to existing files

The following existing files were **read but not modified**:
- `README.md`
- `PRD.md`
- `ARCHITECTURE.md`
- `PACKAGE_STRUCTURE.md`
- `V1_ACCEPTANCE_CRITERIA.md`
- `REPLAY_AND_DETERMINISM.md`
- `SECURITY.md`
- `TESTING_STRATEGY.md`
- `EXTENDING.md`
- `DEPENDENCIES.md`
- `DEVELOPMENT.md`
- `GLOSSARY.md`
- `docs/adr/0001`–`0007`
- `docs/adr/README.md`
- `docs/TEST_DATA.md`
- `tests/fixtures/*`

The `AGENTS.md` files (created in the prior turn on `main`) were not modified.

---

## 3. Decisions made during this exercise

These are decisions I made implicitly while writing the sprint plans. **The project owners should review and either accept or amend them.**

### 3.1 Sprint 0 (design closure) — recommended decisions

| Decision | Recommendation | Rationale |
|---|---|---|
| **License** | **MIT** (default unless team says otherwise) | More permissive; standard for developer-focused libraries. Apache-2.0 is the alternative if patent grants are needed. |
| **Dict DSL V1 scope** | **Keep it small**: 5 concepts (FieldSpec, Constraint, Tag, Policy, Contract). Reject references, inheritance, macros. | YAGNI; the DSL is a test source of truth, not a programming language. |
| **`InputProfile` V1 fields** | **5 fields**: `input_type` (str), `size` (int), `content_hash` (str), `density` (float), `is_empty` (bool). | Minimal surface that supports the planner's heuristic chain. |
| **`CostHint` values (V1 baseline)** | **Placeholder numbers**, not measurements: `text_extraction` (0 tokens, ~5 ms, $0.0); `regex_extraction` (0, ~1 ms, $0.0); `lookup` (0, ~1 ms, $0.0); `inference` (~500 tokens, ~1500 ms, $0.001); `validation` (0, ~1 ms, $0.0). | The cost model is for planner **scoring**, not accounting. Round numbers are fine. Document as heuristics. |

### 3.2 Sprint structure — recommended decisions

| Decision | Recommendation | Rationale |
|---|---|---|
| **Sprint length** | 2 weeks for Sprints 1-9; 3 weeks for Sprint 10 (release + buffer) | Standard for Python libraries. Sprint 10 is longer because it includes the v0.x → 1.0 RC cycle. |
| **Number of sprints** | 10 (including Sprint 0 design closure) | Matches the user's request; covers the full V1 scope. |
| **V1.0.0-rc.1 → v1.0.0** | RC + smoke test with 3 target personas before v1.0.0 | Per `V1_ACCEPTANCE_CRITERIA.md` §5 (pre-1.0 gates). |
| **Sprint 0 included in the count** | Yes, but it is **design-closure only** (no code, no CI). | It exists because 3 design gaps must be closed before Sprint 1 can start. |

### 3.3 Tooling — recommended versions (as of 2026-06)

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11, 3.12, 3.13 (3.10 dropped — EOL October 2026) | All three are stable; 3.13 is the latest. |
| uv | latest stable | Recommended in `DEVELOPMENT.md` §1. |
| hatchling | latest stable | Build backend per `PACKAGE_STRUCTURE.md` §17.1. |
| ruff | ≥ 0.4 | Lint + format. |
| mypy | ≥ 1.10 | Strict mode. |
| pyright | ≥ 1.1 | Cross-validation. |
| pytest | ≥ 7.4 | Test runner. |
| hypothesis | ≥ 6.0 | Property-based tests. |
| attrs | ≥ 23.0 | Core data classes (per `DEPENDENCIES.md`). |
| structlog | ≥ 24.1 | Structured logging. |
| import-linter | ≥ 2.0 | Module DAG enforcement. |
| interrogate | ≥ 1.7 | Docstring coverage. |
| bandit | latest | Security lint. |
| pip-audit | latest | Dependency audit. |
| pytest-benchmark | latest | Performance benchmarks (Sprint 9). |
| memray, py-spy | latest | Memory and CPU profiling (Sprint 9). |

### 3.4 OpenAPI adapter — scope decision

**Decision:** OpenAPI 3.0 is in scope (Sprint 4). **OpenAPI 3.1 full coverage is V2** (per `ADR-0007` best-effort clause).

Rationale: OpenAPI 3.1 uses JSON Schema 2020-12 as its schema language, which means the OpenAPI adapter delegates most schema parsing to the JSON Schema adapter. V1 supports the constructs needed by `petstore_3_0.yaml`; V2 will support `$ref` resolution, `oneOf`/`anyOf`/`allOf`, and full 3.1.

### 3.5 Inference providers — scope decision

**Decision:** V1 ships only a **stub provider** (no real network calls). Real providers (OpenAI, Anthropic, Cohere) are V2 per `EXTENDING.md` §3.

Rationale: V1's goal is to ship a stable, deterministic, replayable artifact. Real providers introduce non-determinism and external dependencies. The V1 inference capability uses a stub that simulates non-determinism for testing; real providers plug into the same SPI in V2.

### 3.6 MONEY arithmetic — design decision

**Decision:** Use Python's `Decimal` with `ROUND_HALF_EVEN` (banker's rounding) and the default 28-digit precision.

Rationale: Banker's rounding is the IEEE 754 standard and avoids the systematic bias of `ROUND_HALF_UP`. 28 digits is Python's `Decimal` default and matches the IEEE 754 binary64 precision of 17 decimal digits with margin. **Document this choice in `reconciler/money.py` module docstring.**

---

## 4. Documentation gaps identified

These are gaps in the existing project documentation that **block or significantly delay** sprint work. The project owners should consider addressing these in a separate documentation PR before Sprint 1 starts.

### 4.1 High-priority gaps (block implementation)

1. **`planner/input_profile.py` has no module spec.** `PACKAGE_STRUCTURE.md` §4.2 lists the module with a one-line description, but no data model, no algorithm, no tests. The planner depends on it.
   - **Recommendation:** Write a 1-page spec (`docs/specs/input-profile.md`) with: data model, `make_profile(input) -> InputProfile` algorithm, classification rules.
   - **Owner:** Senior engineer.
   - **Effort:** 1-2 days.

2. **Dict DSL syntax is not specified anywhere.** `EXTENDING.md` §1.3 uses a generic `to_canonical_field()` placeholder, not real Dict DSL syntax. `PACKAGE_STRUCTURE.md` §3.2 lists `adapters/dict_dsl.py` but the DSL itself is not documented.
   - **Recommendation:** Write a 2-3 page spec (`docs/specs/dict-dsl.md`) with: BNF grammar, 5 worked examples, 3 edge cases, error model. Use Barliman-style notation (or a small custom DSL).
   - **Owner:** Senior engineer + 1 reviewer.
   - **Effort:** 2-3 days.

3. **`CapabilitySpec.cost_estimate` (`CostHint`) has no values.** `ARCHITECTURE.md` §4.3 defines the type but no values for the 5 V1 capabilities. The planner's `scoring.py` cannot rank capabilities without numbers.
   - **Recommendation:** Document the cost model in a 1-page spec (`docs/specs/capability-cost-model.md`) with explicit `CostHint(tokens, ms, usd)` for each capability, plus a scoring rubric.
   - **Owner:** Senior engineer.
   - **Effort:** 1 day.

### 4.2 Medium-priority gaps

4. **`ExecutionArtifact` JSON shape is not fully specified.** The docs describe fields but not their JSON types, nested structure, or constraints. The public API snapshot test (`tests/public_api/test_public_api.py`) needs to know the artifact's JSON shape.
   - **Recommendation:** Add an "Artifact JSON Schema" appendix to `REPLAY_AND_DETERMINISM.md` (or a new `docs/specs/artifact-schema.md`) with: full JSON schema, versioning rules, migration story.
   - **Owner:** Senior engineer.
   - **Effort:** 1-2 days.

5. **`HeuristicContext` is referenced but not defined.** `EXTENDING.md` §4 and `PACKAGE_STRUCTURE.md` §15.3 mention it but do not specify its fields. Post-V1, but the Heuristic protocol references it.
   - **Recommendation:** Document the protocol + context in `EXTENDING.md` §4 or a new `docs/specs/heuristic-spi.md`.
   - **Owner:** Mid-level engineer.
   - **Effort:** 0.5 day.

6. **`BudgetExceededError` short-circuit behavior is not specified.** `ARCHITECTURE.md` §7.1 says "short-circuit and return what was resolved" but the Executor design doesn't detail how in-flight capabilities are handled.
   - **Recommendation:** Add a "Budget short-circuit" subsection to `ARCHITECTURE.md` §11 (Concurrency Model) or §4.4 (Executor).
   - **Owner:** Senior engineer.
   - **Effort:** 0.5 day.

### 4.3 Low-priority gaps

7. **No performance benchmark harness is defined.** `PRD.md` §9 sets aspirational p50/p99 targets, but there's no spec for the benchmark harness, fixture selection, or how performance regressions are detected.
   - **Recommendation:** Defer to Sprint 9. The Sprint 9 deliverable D9.1 (pytest-benchmark harness) will address this.

8. **No performance test for the V1 acceptance criteria §2.5.** Sprint 9 will create the harness and measure; document the methodology as part of Sprint 9.

9. **No spec for `paxman.testing` (the public Hypothesis strategies module).** `TESTING_STRATEGY.md` §3.2 lists the strategies but the module's API is not specified.
   - **Recommendation:** Defer to Sprint 7. The Sprint 7 deliverable D7.1 will specify and implement the module.

---

## 5. Recommendations to project owners

These are recommendations that emerged from the planning exercise but are **outside the scope of the sprint plan itself**. The project owners should consider these as a separate workstream.

### 5.1 Pre-Sprint-0 (before any sprint starts)

1. **Recruit 3 external users for the v1.0.0 validation in Sprint 10.** The single highest-risk prerequisite. The 3 users should be from the target personas (`PRD.md` §6.1). Recruit at least 2 weeks before Sprint 10 starts.

2. **Create a real PyPI account** (or claim the `paxman` project name on TestPyPI first). The OIDC trusted publisher is configured in Sprint 9; the project name must be reserved by Sprint 9.

3. **Decide the license** (MIT vs Apache-2.0). This is a 1-day decision; the team should have it made before Sprint 1.

### 5.2 During Sprint 0 (design closure)

4. **Write the Dict DSL spec, Input Profile spec, and CostHint spec** as separate docs under `docs/specs/`. These are the prerequisites for Sprint 1.

5. **Document the V1 release notes in advance.** The Sprint 10 deliverable D10.9 is the release notes; a skeleton can be drafted in Sprint 0 to capture the project owner's intent.

### 5.3 During Sprints 1-9

6. **Keep the documentation updated as the code evolves.** Every sprint includes 20% documentation. Per `EXTENDING.md` and `DEVELOPMENT.md`, docs are part of the contract.

7. **Run the `bandit` and `pip-audit` checks on every PR.** These are added to CI in Sprint 8 but should be checked manually before then.

8. **Document any deviations from the sprint plan in the changes log.** If a sprint's scope changes mid-flight, document the change here.

### 5.4 Post-v1.0.0

9. **V1.1.0 candidates** (from the retrospective): OpenAPI 3.1 full coverage, real inference providers, performance optimizations, migration tools.

10. **V2 candidates** (per `ARCHITECTURE.md` §17.2): LLM planner, async API, parallel execution, RAG, multi-agent coordination, capability marketplace, visual planners, graph execution, workflow orchestration, persistent execution, distributed tracing export.

---

## 6. Open questions deferred to the team

These are questions that arose during the planning exercise but were not answered. The project owners should decide before the relevant sprint starts.

1. **Q1: Should the V1 `paxman.normalize()` API accept `dict` input, or only `bytes` / `str`?**
   - The current `README.md` quickstart shows `input_data=raw_invoice` (a `str`). But `ARCHITECTURE.md` §2 shows `input_data` without a type.
   - **Decision needed before Sprint 4** (Executor receives input).

2. **Q2: What is the default `Policy` for `paxman.normalize()`?**
   - `Policy(allow_remote_inference=True, allow_local_inference=True, confidence_floor=0.80, unresolved_acceptable=False)` is the example in `ARCHITECTURE.md` §7.2.
   - **Recommendation:** Use this default. **Document explicitly in `paxman.normalize()`'s docstring.**

3. **Q3: Should the Executor be implemented as a class or as a function?**
   - The architecture docs imply a function (`executor.run(plan, ...)`), but Python idioms suggest a class with state.
   - **Recommendation:** A function. Easier to test, easier to mock. **Document this decision in Sprint 1's design notes.**

4. **Q4: What is the maximum number of fields per contract for V1?**
   - The performance targets imply 20 fields; `ARCHITECTURE.md` §14.2 says "very large contracts (>10,000 fields)" is NOT a perf guarantee.
   - **Recommendation:** Document the V1 cap at 1,000 fields. Validate contracts that exceed this with a `ConfigurationError`. **Document in `validator.py`.**

5. **Q5: Does Paxman support nested `MONEY` aggregation across fields?**
   - E.g., `total = sum(line_items[].price)` where both are `MONEY`.
   - The `validation` capability's reference constraints might cover this, but the `MONEY` Reconciler doesn't.
   - **Recommendation:** V1 supports per-field `MONEY` only. Cross-field aggregation is V2. **Document in `MIGRATION_GUIDE.md`.**

6. **Q6: How does Paxman handle `Bytes` inputs (PDF, PNG)?**
   - The V1 capability set includes `text_extraction` for "Pull plain text from raw input (PDF, image, HTML)" (`ARCHITECTURE.md` §4.3). But the current implementation in Sprint 3 only handles `text/plain` and `text/html`.
   - **Recommendation:** V1 `text_extraction` handles `text/plain` and `text/html` only. PDF and image extraction is V2 (requires OCR providers). **Document in the capability's docstring.**

7. **Q7: What is the storage model for `Evidence`?**
   - `SECURITY.md` §2.1 says evidence contains "Capability id and version", "Source span", "Field path", "Timestamp" — but the storage format (JSON in the artifact? separate file? reference by ID?) is not specified.
   - **Recommendation:** Evidence is a list of `EvidenceRef` objects embedded in the artifact's `FieldResult`. Each `EvidenceRef` has `capability_id`, `capability_version`, `field_path`, `span` (optional), `model_id` (optional for inference), `timestamp` (optional, default: redact in replay path). **Document in `artifact/evidence.py` docstring.**

---

## 7. V1 acceptance criteria checklist (planning-time status)

Per `V1_ACCEPTANCE_CRITERIA.md` §1-§4. As of this planning exercise:

- **§1 Functional Criteria** — 0% complete (no code).
- **§2 Quality Criteria** — 0% complete (no tests).
- **§3 Operational Criteria** — 0% complete (no packaging, no release).
- **§4 Documentation Criteria** — **100% complete** (all 11 docs are present and reviewed).

The 80% threshold for `v0.5.0` is met by Sprints 2-7 (functional criteria 80% complete). The 1.0.0 threshold is met by Sprint 10 (all criteria complete + 3 external users).

---

## 8. Effort estimate summary

| Sprint | Effort (id-ed) | Engineers × Weeks | Calendar |
|---|---|---|---|
| 0 | 3 | 1 × 1 week | Week 1 |
| 1 | 18 | 2 × 2 weeks | Weeks 2-3 |
| 2 | 14 | 4 × 2 weeks (parallel adapters) | Weeks 4-5 |
| 3 | 16 | 4 × 2 weeks | Weeks 6-7 |
| 4 | 15 | 4 × 2 weeks | Weeks 8-9 |
| 5 | 15 | 3 × 2 weeks | Weeks 10-11 |
| 6 | 16 | 4 × 2 weeks | Weeks 12-13 |
| 7 | 15 | 3 × 2 weeks | Weeks 14-15 |
| 8 | 14 | 2 × 2 weeks | Weeks 16-17 |
| 9 | 12 | 2 × 2 weeks | Weeks 18-19 |
| 10 | 8 (1-2 eng) + 1 week external user feedback | 1-2 × 3 weeks | Weeks 20-22 |
| **Total** | **~146 id-ed** | — | **~22 weeks (5.5 months)** |

The total is less than the initial audit estimate of 190 id-ed because of **parallelization** within sprints. The realistic calendar timeline is 5-5.5 months with a 4-person team.

---

## 9. What this exercise did NOT do

To be explicit about scope:

1. **Did not write any source code.** No `src/paxman/` exists. No `pyproject.toml`. No CI.
2. **Did not modify any existing project files.** The 13 top-level `.md` files and 7 ADRs are unchanged.
3. **Did not create any ADRs** (the Dict DSL and InputProfile ADRs are listed as **optional** in Sprint 0; the project owner decides).
4. **Did not recruit external users.** This is a prerequisite for Sprint 10 and is the project owner's responsibility.
5. **Did not commit to a specific PyPI publication date.** The 5.5-month calendar estimate assumes no major delays; the project owner should add a 4-week buffer for unexpected issues.

---

## 10. Next steps for the project owner

1. **Review the sprint plan.** Read `docs/sprints/README.md` first, then each sprint's planning doc.
2. **Approve or amend the recommendations in §3 above.** Especially: license (MIT vs Apache-2.0), Dict DSL scope, `InputProfile` scope, `CostHint` baseline values, MONEY rounding mode.
3. **Address the documentation gaps in §4** (especially §4.1 — the 3 high-priority gaps). These are 1-3 day docs that unblock Sprint 1.
4. **Decide the open questions in §6** before the relevant sprint starts.
5. **Recruit 3 external users for Sprint 10** (start at least 2 weeks before Sprint 10).
6. **Approve the sprint plan** (e.g., a `LGTM` on the PR or a `docs/sprints/APPROVED.md` marker).
7. **Start Sprint 0** — the design-closure phase.

---

## See also

- `docs/sprints/README.md` — sprint plan index.
- `docs/sprints/sprint-00-design-closure.md` — pre-sprint that closes the 3 design gaps.
- `docs/sprints/sprint-10-release.md` — final release sprint.
- `docs/adr/README.md` — MADR template for any new ADRs (Sprint 0 may add 1-2).
- `../V1_ACCEPTANCE_CRITERIA.md` — definition of done for 1.0.
- `../PRD.md` — product requirements.

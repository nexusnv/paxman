# Sprint 3 — Planner + 3 Capabilities

> **Duration:** 2 weeks
> **Goal:** Implement the **field-centric planner** (deterministic, rule-based) and the first **3 capabilities** (`text_extraction`, `regex_extraction`, `validation`). The Executor is not yet wired — this sprint ends with a planner that produces an `ExecutionPlan` but does not execute it.
> **Status:** Sprint 3 closes **PRD §10 V1 Acceptance Criteria item 1.2.partial** (3 of 5 V1 capabilities) and **§1.3 partial** (planner/ subsystem).

## Scope (in)

### Planner subsystem (`src/paxman/planner/`)
- `field_plan.py` — `FieldPlan`, `FieldPlanStep`, `ExecutionPlan` data models
- `input_profile.py` — `InputProfile` data model + `make_profile(input) -> InputProfile` (per Sprint 0 spec)
- `scoring.py` — candidate cost/confidence/coverage scoring (using `CostHint` from Sprint 0)
- `heuristics.py` — 7-step heuristic ordering rules (per `ARCHITECTURE.md` §4.2)
- `policies.py` — budget/accuracy/fallback policy application
- `_registry.py` — internal `CapabilityRegistry` handle
- `planner.py` — top-level `plan(canonical, profile, budget, policy, registry) -> ExecutionPlan`

### Capabilities subsystem — partial (`src/paxman/capabilities/`)
- `base.py` — `Capability` Protocol
- `spec.py` — `CapabilitySpec` data model (with `CostHint` from Sprint 0)
- `result.py` — `CapabilityResult`, `Candidate`, `EvidenceRef`, `Diagnostic` (no `confidence` field per ADR-0005)
- `registry.py` — capability lookup, version management
- `v1/text_extraction.py` — `text/plain` and `text/html` only in V1; provider SPI for OCR
- `v1/regex_extraction.py` — ECMAScript regex with named groups
- `v1/validation.py` — type/range/regex/enum/reference constraint checks
- Stub `InferenceProvider` (in `capabilities/v1/inference.py` — interface only, no real provider in this sprint)

### Tests
- Unit tests for every module above
- Property tests: **planner determinism** (Hypothesis, `derandomize=True`)
- Capability tests: known-input for each of the 3 capabilities
- `test_capability_result_has_no_confidence()` — static check that `CapabilityResult` has no `confidence` field (per ADR-0005)

### Tooling
- `import-linter` contract: `planner/` and `capabilities/` may NOT import from `executor/`, `reconciler/`, `artifact/`, or `api/`

## Scope (out)

- **Executor** (Sprint 4).
- **Reconciler** (Sprint 5).
- **Artifact + API** (Sprint 6).
- **`lookup` and `inference` capabilities** (Sprint 4 — `lookup` is a data-source concern; `inference` requires Executor context).
- **No real inference provider** — only the SPI and a stub. Real providers (OpenAI, Anthropic) are V2 per `EXTENDING.md` §3.4.

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D3.1 | `planner/field_plan.py` — data models | 2.0 |
| D3.2 | `planner/input_profile.py` — per Sprint 0 spec | 2.0 |
| D3.3 | `planner/scoring.py` — uses Sprint 0 `CostHint` values | 2.0 |
| D3.4 | `planner/heuristics.py` — 7-step ordering | 3.0 |
| D3.5 | `planner/policies.py` — budget/policy application | 2.0 |
| D3.6 | `planner/_registry.py` — registry handle | 1.0 |
| D3.7 | `planner/planner.py` — top-level `plan()` | 3.0 |
| D3.8 | `capabilities/base.py` — `Capability` Protocol | 1.0 |
| D3.9 | `capabilities/spec.py` — `CapabilitySpec` | 1.0 |
| D3.10 | `capabilities/result.py` — `CapabilityResult` (no `confidence` field) | 1.0 |
| D3.11 | `capabilities/registry.py` — versioned registry | 2.0 |
| D3.12 | `capabilities/v1/text_extraction.py` | 3.0 |
| D3.13 | `capabilities/v1/regex_extraction.py` | 2.0 |
| D3.14 | `capabilities/v1/validation.py` | 2.0 |
| D3.15 | `capabilities/v1/inference.py` (SPI + stub provider only) | 1.0 |
| D3.16 | Unit tests for all planner modules (≥1 per public function) | 3.0 |
| D3.17 | Unit tests for all 3 capabilities (known-input, determinism, spec) | 3.0 |
| D3.18 | Property tests: planner determinism (Hypothesis, 100 examples) | 1.5 |
| D3.19 | Static test: `CapabilityResult` has no `confidence` attribute | 0.2 |
| D3.20 | `import-linter` contracts for `planner/` and `capabilities/` | 0.5 |
| D3.21 | `docs/concepts/planning.md` (skeleton) | 1.0 |

**Total: ~35.2 id-ed.** Sized for **4 engineers × 2 weeks** with parallel work (planner 2 ppl + 2 capability authors + 1 test lead).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 4 engineers (1 senior, 3 mid-level) | 2 on planner, 2 on capabilities |
| **Tools** | Hypothesis (dev dep), all Sprint 1 + 2 deps | Standard Python dev env |
| **Tests** | Sprint 1 + 2 test infrastructure; fixture contracts (Pydantic + Dict DSL) from Sprint 2 | Done |
| **Decisions** | Sprint 0 `CostHint` values; `InputProfile` spec | Both from Sprint 0 |
| **Docs** | `ADR-0001` (field-centric), `ADR-0002` (rule-based planner), `ADR-0005` (confidence ownership), `ARCHITECTURE.md` §4.2, §4.3 | Read by all engineers |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **hypothesis** | ≥ 6.0 | Planner determinism property tests | Already dev dep |
| **re** (stdlib) | — | ECMAScript regex for `regex_extraction` | Python's `re` is ECMAScript-compatible enough for V1 |
| **html.parser** (stdlib) | — | `text/html` parsing for `text_extraction` | Stdlib only |
| **BeautifulSoup4** | latest | Optional, for richer `text/html` extraction | Defer to V2; use stdlib for V1 |

## API keys / secrets

None. The stub inference provider returns hard-coded completions; no real provider is wired.

## Exit criteria

1. `planner.plan(canonical_contract, profile, budget, policy, registry) -> ExecutionPlan` is a pure function (no clock, no random, no I/O).
2. Property test: for 100 random `(canonical, profile, budget, policy, registry)` tuples, the same tuple produces byte-equal `ExecutionPlan` JSON across two calls.
3. The 7-step heuristic ordering is implemented: explicit evidence → local deterministic → structured lookup → derived computation → local inference → remote inference → `UNRESOLVED`.
4. The Planner excludes remote inference when `Policy.allow_remote_inference=False` (heuristic step 6 dropped).
5. The Planner excludes local inference when `Policy.allow_local_inference=False` (heuristic step 5 dropped).
6. `text_extraction` capability handles `text/plain` and `text/html` inputs (≥1 unit test each).
7. `regex_extraction` capability extracts with named groups (≥1 unit test, including a multi-group pattern).
8. `validation` capability checks type, range, regex, enum (≥1 unit test each).
9. `CapabilityResult` does NOT have a `confidence` field (static test using `hasattr`/`getattr`).
10. `CapabilityResult.candidates` are returned with `value` (not yet `confidence`).
11. Test coverage on `planner/` ≥ 90%, on `capabilities/v1/{text_extraction,regex_extraction,validation}.py` ≥ 85% (V1 acceptance §2.2).
12. `mypy --strict src/paxman/{planner,capabilities}` is clean.
13. `import-linter` is clean for both subsystems.
14. `make ci` is green.
15. `docs/concepts/planning.md` exists as a skeleton (will be filled in Sprint 8).

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Planner determinism is broken by a hidden source of non-determinism (e.g., set iteration order) | Medium | High | Property test catches it. Mitigation: explicitly sort `registry.capabilities` by `id` before iteration. Pin Python's `PYTHONHASHSEED=0` in CI. |
| `InputProfile` is misclassified (e.g., a 10MB HTML blob is misidentified as `text/plain`) | Medium | Medium | Sprint 0 spec defines classification algorithm; cover with ≥5 test cases (empty, plain, html, base64, binary). |
| The 7-step heuristic is too rigid for the V1 use cases (e.g., always picking regex over inference even when the field is poorly-suited) | Medium | Medium | Property test that, for the "invoice from a well-known vendor" test case, the planner picks `regex_extraction` first. Document the heuristic as a default; per-field `ResolutionPolicy` override exists in `CanonicalField` (Sprint 2 already created the field). |
| `text_extraction`'s provider SPI is over-engineered (no real provider yet) | Medium | Low | Keep the provider interface minimal: `def extract(input) -> str`. Stub provider returns `input` for `text/plain`, uses `html.parser` for `text/html`. |
| `regex_extraction` named-group support is incomplete (e.g., not handling duplicate group names) | Low | Low | Document the regex flavor: ECMAScript, single named group per pattern in V1. Reject `(?P<name>...)(?P<name>...)`. |
| `validation` capability's reference-constraint check (e.g., "total == sum(line_items)") is not in scope but might be misread as in scope | Low | Low | Reference constraints are post-V1 (per `EXTENDING.md`). Validate only type, range, regex, enum in V1. |
| Stub inference provider accidentally drifts toward real-provider behavior | Low | Low | Stub is one class with one method that returns `Completion(text="...", model="stub", usage=Usage(tokens=0, ...))`. Add a test that the stub never makes network calls. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §1.2, §1.3.
- `../PACKAGE_STRUCTURE.md` §4 — `planner/` module spec.
- `../PACKAGE_STRUCTURE.md` §5 — `capabilities/` module spec.
- `../docs/adr/0001-field-centric-planning.md`.
- `../docs/adr/0002-rule-based-planner-v1.md`.
- `../docs/adr/0005-confidence-ownership.md`.
- `../ARCHITECTURE.md` §4.2, §4.3.
- `../EXTENDING.md` §2 — Capability SPI.
- `../TESTING_STRATEGY.md` §7 — capability tests.

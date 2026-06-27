# Paxman Package Architecture (V1)

> **Status:** Stable v1 (promoted from draft; this is the **source of truth** for module-level design).
> **Audience:** Engineers implementing or extending Paxman.
> **Related docs:** [PRD.md](https://github.com/nexusnv/paxman/wiki/Internal-Development/Decision-History/PRD), [ARCHITECTURE.md](./architecture.md), [GLOSSARY.md](./glossary.md)

This is the **stable mental model for the codebase**, derived from [ARCHITECTURE.md](./architecture.md) and [PRD.md](https://github.com/nexusnv/paxman/wiki/Internal-Development/Decision-History/PRD). It reflects the V1 product definition: a **contract-driven, field-centric, deterministic normalization engine**.

It supersedes the earlier `PACKAGE_STRUCTURE_draft.md`. The numbering is preserved where possible to keep references stable.

---

## 1. Top-Level Structure (Conceptual Layers)

Paxman is split into **seven strict subsystem zones**:

```text
paxman/
│
├── contract/        # canonicalization + validation of caller contracts
├── planner/         # field-centric plan synthesis (deterministic, rule-based)
├── capabilities/    # atomic, reusable operations (V1 surface)
├── executor/        # runs the plan, collects evidence, stops early
├── reconciler/      # merges candidates, assigns confidence, resolves truth
├── artifact/        # final normalized output + evidence + replay data
│
└── api/             # public surface (the ONLY thing users touch)
```

Everything else is derived from these boundaries. The `api/` layer is a **hard boundary** enforced by tests; the rest are internal.

> **Core principle:** Contracts define *what* output must look like. Planner defines *what to do*. Executor defines *how to run it*. Reconciler defines *what is ultimately true*. Artifact defines *what was produced*. API defines *what the user can ask for*.

---

## 2. Module Dependency DAG (Hard Rule)

The dependency graph is **strictly layered**. A module may import from its own layer, any layer to its right, and the cross-cutting modules at the bottom — **never** to its left.

```text
                  ┌──────────┐
                  │   api    │
                  └────┬─────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  ┌────────┐     ┌──────────┐    ┌────────────┐
  │contract│ ──▶ │ planner  │ ──▶ │ capabilities│
  └────────┘     └────┬─────┘    └──────┬─────┘
                       │                 │
                       ▼                 ▼
                  ┌──────────┐    ┌──────────┐
                  │ executor │ ──▶│reconciler│
                  └────┬─────┘    └────┬─────┘
                       │               │
                       └───────┬───────┘
                               ▼
                          ┌─────────┐
                          │ artifact│
                          └─────────┘

        ┌────────────────────────────────────────┐
        │  Cross-cutting (imported by all):       │
        │  - errors    - types     - logging     │
        │  - versioning  - protocols            │
        └────────────────────────────────────────┘
```

**Forbidden imports (enforced by CI / ruff / import-linter):**

- `contract/` may NOT import from `planner/`, `executor/`, `reconciler/`, `artifact/`, `capabilities/`, or `api/`.
- `planner/` may NOT import from `executor/`, `reconciler/`, `artifact/`, or `api/`.
- `capabilities/` may NOT import from `planner/`, `executor/`, `reconciler/`, `artifact/`, or `api/`.
- `executor/` may NOT import from `reconciler/`, `artifact/`, or `api/`.
- `reconciler/` may NOT import from `artifact/` or `api/`.
- `artifact/` may NOT import from `api/`.
- `api/` may import from any internal layer.
- No subsystem may import from `capabilities/v1/*` directly; the registry is the only entry point.

**Tooling:** this DAG is enforced by [`import-linter`](https://import-linter.readthedocs.io/) configured in `pyproject.toml`.

---

## 3. `contract/` — "Translation + Validation Boundary"

### 3.1 Meaning

`contract/` is Paxman's **adapter + validation subsystem**. It is the only layer that knows about external contract formats.

It converts caller-provided contracts (Pydantic, JSON Schema, Dict DSL, OpenAPI) into Paxman's **canonical internal representation**, and rejects anything invalid.

### 3.2 Structure

```text
contract/
├── canonical.py        # CanonicalContract + CanonicalField data models
├── validator.py        # rejects invalid contracts → INVALID_CONTRACT
├── semantics.py        # semantic tag handling, structural vs semantic layers
├── registry.py         # adapter lookup by contract format
├── _types.py           # internal: FieldType enum, Constraint, ResolutionPolicy
│
└── adapters/
    ├── base.py         # ContractAdapter protocol (the SPI)
    ├── pydantic.py     # Pydantic model → canonical
    ├── json_schema.py  # JSON Schema → canonical
    ├── dict_dsl.py     # internal Dict DSL → canonical
    └── openapi.py      # Optional OpenAPI → canonical
```

### 3.3 Public surface of this module

| Symbol | Visibility | Notes |
|---|---|---|
| `CanonicalContract` | Re-exported in `api.types` | The frozen internal form |
| `CanonicalField` | Re-exported in `api.types` | Per-field canonical spec |
| `FieldType` | Re-exported in `api.types` | `STRING`, `INTEGER`, ... |
| `ContractAdapter` | Re-exported in `api.protocols` | SPI for adding new adapters |
| `ResolutionPolicy` | Re-exported in `api.types` | Per-field fallback policy |
| `register_adapter` | `api` | Register a third-party adapter at runtime |
| `pydantic.adapt(model_class)` | `api.normalize` accepts Pydantic directly | Convenience |

### 3.4 Internal invariants (must hold; tested)

1. **Adapters only produce canonical output; they never execute or plan.**
2. **Validator is mandatory** — invalid contracts fail immediately with `INVALID_CONTRACT`.
3. **Core types:** `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`.
4. **`MONEY` is first-class** (precision, currency, ISO 4217, FX, rounding).
5. **`CanonicalField` carries:** `id`, `path`, `name`, `type`, `required`, `critical`, `nullable`, `confidence_threshold`, `evidence_required`, `semantic_tags`, `fallback_policy`.
6. **`CanonicalContract` carries:** `id`, `version`, `fields`, `constraints`, `policies`.
7. **No adapter may leak its source representation downstream** — the only output of an adapter is a `CanonicalContract`.
8. **Adapters are pure functions** — same input → same `CanonicalContract` (no random, no clock, no I/O).

### 3.5 Per-module testing strategy

- **Unit tests** — adapter output for representative Pydantic / JSON Schema / Dict DSL / OpenAPI contracts.
- **Golden tests** — frozen canonical snapshots for each adapter.
- **Validator tests** — every error path.
- **Property tests** — roundtrip: Pydantic → canonical → Pydantic should preserve the structure (within Pydantic v2's expressible subset).
- **No I/O** — adapter tests do not touch network, disk, or clock.

> Contract = "the only place that knows about external schemas"

---

## 4. `planner/` — "Field-Centric Plan Synthesis"

### 4.1 Meaning

The planner is the **deterministic brain** of Paxman. It does NOT execute anything.

It reads the canonical contract, analyzes the input profile, and produces a **field-by-field execution plan** — one plan per required field, not one plan per document.

### 4.2 Structure

```text
planner/
├── planner.py         # top-level: contract + input + budget → plan
├── heuristics.py      # ordering rules (explicit evidence → ... → UNRESOLVED)
├── scoring.py         # candidate cost / confidence / coverage scoring
├── policies.py        # budget, accuracy, fallback policies
├── field_plan.py      # FieldPlan + FieldPlanStep data models
├── input_profile.py   # lightweight input classifier (no capability invocation)
└── _registry.py       # internal: capability registry handle
```

### 4.3 Public surface

| Symbol | Visibility | Notes |
|---|---|---|
| `ExecutionPlan` | Internal | Not re-exported in `api/` |
| `FieldPlan` | Internal | Per-field plan |
| `FieldPlanStep` | Internal | One capability invocation in a chain |
| `Heuristic` | `api.protocols` | SPI for new heuristics |
| `register_heuristic` | `api` | Pluggable heuristic (post-V1) |

### 4.4 Internal invariants

1. **Field-centric, not document-centric.** Each required field gets its own `FieldPlan`.
2. **Deterministic.** Given the same canonical contract + input profile + config + capability set, the planner MUST produce the same plan.
3. **Rule-based in V1.** No LLM planner, no agent planner, no AI-generated planning logic.
4. **Heuristic ordering** (highest to lowest preference):
   1. Explicit evidence
   2. Local deterministic extraction
   3. Structured lookup
   4. Derived computation
   5. Local inference
   6. Remote inference
   7. `UNRESOLVED`
5. **Planner never touches raw input execution** — it only emits `FieldPlan`s.
6. **Planner does NOT assign confidence** — capabilities return candidates; the Reconciler assigns final confidence. The Planner may emit a `target_confidence` (read from the field's `confidence_threshold`) but never scores a candidate. See [ADR-0005](../adr/0005-confidence-ownership.md).

### 4.5 Per-module testing strategy

- **Unit tests** — heuristic selection for each (input profile × contract shape) combination.
- **Golden tests** — frozen `ExecutionPlan` snapshots for representative inputs.
- **Property tests** — determinism: identical inputs → byte-identical `ExecutionPlan` JSON.
- **Budget tests** — planner respects `max_remote_inference_calls`, `max_total_cost_usd`, etc.
- **No I/O** — planner tests use fake capability registries and fake input profiles.

> Planner = "synthesizes the cheapest trustworthy path per field"

---

## 5. `capabilities/` — "Atomic Operations"

### 5.1 Meaning

Capabilities are the **only executable primitives**. They are reusable atomic operations with metadata describing input, output, cost, and determinism.

LLMs are **providers behind inference capabilities**, not capabilities themselves.

### 5.2 Structure

```text
capabilities/
├── base.py                # Capability protocol (the SPI)
├── spec.py                # CapabilitySpec data model
├── result.py              # Candidate, EvidenceRef, Diagnostic
├── registry.py            # capability lookup + metadata
│
└── v1/
    ├── text_extraction.py     # pull text out of raw input
    ├── regex_extraction.py    # pattern-based local extraction
    ├── lookup.py              # structured / retrieval-based extraction
    ├── inference.py           # model-backed inference (LLM is a provider)
    └── validation.py          # verify a candidate value
```

### 5.3 Public surface

| Symbol | Visibility | Notes |
|---|---|---|
| `Capability` | `api.protocols` | SPI for new capabilities |
| `CapabilitySpec` | Internal | Metadata |
| `Candidate` | Internal | Single proposed value |
| `EvidenceRef` | Internal | Pointer to a piece of evidence |
| `Diagnostic` | Internal | Structured note |
| `register_capability` | `api` | Register a third-party capability at runtime |
| `get_capability(id, version)` | `api` | Look up a registered capability |

### 5.4 Internal invariants

1. **V1 capability surface is deliberately small:**
   - `text_extraction`
   - `regex_extraction`
   - `lookup` (deterministic backend: yes; vector backend: no)
   - `inference` (always non-deterministic when model is remote)
   - `validation`
2. **Capabilities never assign confidence.** They return candidates + evidence + diagnostics only.
3. **Confidence is exclusively owned by the Reconciler** (the Planner may emit a `target_confidence` but never scores a candidate). This prevents confidence inflation. See [ADR-0005](../adr/0005-confidence-ownership.md).
4. **Every capability MUST expose a `CapabilitySpec`** with input/output, cost, determinism flag.
5. **Capabilities are stateless and side-effect-free** except for declared external effects (which MUST be captured in evidence).
6. **Capabilities never read the canonical contract directly** — they receive a `CapabilityContext` built by the Executor.

### 5.5 Per-module testing strategy

- **Unit tests per capability** — known input → known candidates + evidence.
- **Determinism tests** for deterministic capabilities (regex, validation) — property test.
- **Provider-mock tests** for non-deterministic capabilities (text_extraction, inference) — mock the provider, assert shape of `CapabilityResult`.
- **No raw input in capability tests** — fixtures only.

> Capabilities = "pure atomic operations, never the source of truth"

---

## 6. `executor/` — "Deterministic Runner"

### 6.1 Meaning

The Executor **runs the plan** produced by the Planner. It does not replan, reroute, or optimize.

It walks the per-field plans in order, invokes capabilities, collects evidence, and stops early when the contract is satisfied with acceptable confidence.

### 6.2 Structure

```text
executor/
├── executor.py         # top-level execution driver
├── field_runner.py     # executes one FieldPlan
├── context.py          # CapabilityContext builder
├── evidence.py         # evidence + diagnostics collection
├── early_stop.py       # short-circuit when contract is satisfied
├── budget_tracker.py   # tracks cost / latency / invocations against Budget
└── execution_state.py  # transient in-flight state (never authoritative)
```

### 6.3 Public surface

| Symbol | Visibility | Notes |
|---|---|---|
| `Executor` | Internal | Not re-exported |
| `CandidateResult` | Internal | Per-field output of execution |

### 6.4 Internal invariants

1. **Executor follows the plan exactly as the Planner defined it.** No replanning, no rerouting, no structural retries.
2. **Executor passes context forward** — never mutates the plan.
3. **Executor stops early** when a field hits its `confidence_threshold` (the Executor knows the target because the Planner embeds it in the `FieldPlan`; the Executor does not score the candidate — the Reconciler does).
4. **Executor returns explicit `UNRESOLVED` candidates** when it cannot satisfy a field — never silent guessing.
5. **Executor never assigns final confidence** — only collects candidate evidence.
6. **Executor never reads raw input directly** — it receives an opaque `InputData` handle and passes a `CapabilityContext` to each capability.

### 6.5 Per-module testing strategy

- **Unit tests** — sequential execution of a 3-field plan; assertion on invocation order and stop conditions.
- **Mocked capabilities** — no real capabilities in Executor tests; capabilities are mocks.
- **Budget tests** — Executor short-circuits when budget is exhausted.
- **Early-stop tests** — Executor stops on first successful candidate per field.
- **No planner mocking needed** — Executor tests inject a fake `ExecutionPlan`.

> Executor = "hands that execute the plan, never rewrite it"

---

## 7. `reconciler/` — "Truth Resolution"

### 7.1 Meaning

The Reconciler is a **first-class subsystem**. It is where Paxman converts uncertainty into trustworthy normalized output.

It owns the **final truth** and the **final confidence** (the only subsystem that does).

### 7.2 Structure

```text
reconciler/
├── reconciler.py        # top-level: candidates → resolved truth
├── merge.py             # candidate merging strategies
├── conflict.py          # conflict detection
├── evidence_compare.py  # compare evidence quality across candidates
├── confidence.py        # confidence assignment (bands: CERTAIN/HIGH/MEDIUM/LOW/UNTRUSTED)
├── unresolved.py        # explicit unresolved state handling
├── validation.py        # apply Validation capability to candidates
├── money.py             # MONEY arithmetic + currency policy
└── truth.py             # TruthLayer data models (Contract / Candidate / Resolved)
```

### 7.3 Public surface

| Symbol | Visibility | Notes |
|---|---|---|
| `ResolvedResult` | Internal | Per-field resolved output |
| `TruthLayer` | Internal | Tagged-union of Contract / Candidate / Resolved |
| `ConfidenceBand` | Re-exported in `api.types` | `CERTAIN`, `HIGH`, `MEDIUM`, `LOW`, `UNTRUSTED` |

### 7.4 Internal invariants

1. **Reconciler is the ONLY layer that assigns final confidence and final truth.** See [ADR-0005](../adr/0005-confidence-ownership.md).
2. **Three truth layers are explicit:**
   - **Contract Truth** — what the caller requires
   - **Candidate Truth** — what capabilities discovered
   - **Resolved Truth** — what the Reconciler accepts into the artifact
3. **Reconciler never executes capabilities.**
4. **Reconciler never reads raw input.**
5. **Reconciler never sees external schemas** — only `CanonicalContract`.
6. **Unresolved fields are explicit**, never silent.
7. **Confidence bands are fixed:** `CERTAIN`, `HIGH`, `MEDIUM`, `LOW`, `UNTRUSTED`. The internal float is `0.0–1.0`; the band is derived deterministically from the float and the field's `confidence_threshold`.

### 7.5 Per-module testing strategy

- **Unit tests per merging strategy** — union, intersection, prefer-by-evidence.
- **Conflict tests** — same field, two candidates, two evidence sources.
- **Confidence calibration tests** — fixed inputs → fixed confidence bands.
- **Property tests** — Reconciler is monotonic: a strictly better candidate (higher evidence quality) never lowers confidence.
- **`MONEY` arithmetic tests** — currency mismatch, FX, precision.
- **No capability mocking needed** — Reconciler takes candidates, not capabilities.

> Reconciler = "where uncertainty becomes trustworthy normalized output"

---

## 8. `artifact/` — "The Product + Replay Source"

### 8.1 Meaning

The artifact is the **final output bundle** returned by Paxman. It contains normalized data, evidence, diagnostics, unresolved fields, plan metadata, and replay data.

It is the **only** replay mechanism.

### 8.2 Structure

```text
artifact/
├── artifact.py          # ExecutionArtifact + FieldResult data models
├── confidence.py        # confidence band mapping (float ↔ CERTAIN/HIGH/MEDIUM/LOW/UNTRUSTED)
├── replay.py            # replay hash computation + rehydration
├── evidence.py          # evidence references + provenance
├── diagnostics.py       # structured diagnostics
├── statistics.py        # execution statistics
├── serializer.py        # stable JSON encoding (sorted keys, no whitespace)
└── _hash.py             # replay hash internals
```

### 8.3 Public surface

| Symbol | Visibility | Notes |
|---|---|---|
| `ExecutionArtifact` | Re-exported in `api.types` | The product |
| `FieldResult` | Internal | Per-field result |
| `Status` | Re-exported in `api.types` | `SUCCESS`, `PARTIAL_SUCCESS`, `UNRESOLVED`, `INVALID_CONTRACT`, `EXECUTION_FAILED` |
| `replay(artifact, contract, paxman_version)` | `api` | Rehydrate an artifact |
| `ReplayError` family | `api.errors` | Replay-specific errors |

### 8.4 Internal invariants

1. **`ExecutionArtifact` is the product** — it contains:
   - `normalized_data`
   - `field_results`
   - `unresolved_fields`
   - `evidence`
   - `diagnostics`
   - `execution_plan`
   - `replay_hash`
   - `statistics`
2. **`FieldResult` carries:** `field_id`, `status`, `value`, `confidence`, `evidence_refs`.
3. **Statuses:** `SUCCESS`, `PARTIAL_SUCCESS`, `UNRESOLVED`, `INVALID_CONTRACT`, `EXECUTION_FAILED`.
4. **Replay hash captures:** canonical contract representation + input fingerprint + planner version + capability versions + configuration + constraints.
5. **Artifact is replayable without recomputation** — rehydration only.
6. **No persistence in core.** The caller stores the artifact.
7. **JSON serialization is deterministic** — sorted keys, no whitespace, RFC 8785 (or equivalent).
8. **Schema version is embedded** — `artifact.paxman_version`, `artifact.planner_version`, `artifact.capability_versions[]`.

### 8.5 Per-module testing strategy

- **Replay equality tests** — given an artifact, `replay(artifact, contract) == artifact` (byte-equal JSON).
- **Hash determinism** — same inputs → same hash (Hypothesis property test).
- **Version mismatch tests** — wrong Paxman version raises `VersionMismatchError`.
- **Tamper tests** — modifying any field changes the hash and is detected on replay.
- **Schema migration tests** — old artifacts replay cleanly on a compatible new version.

> Artifact = "frozen, evidence-backed, replayable truth"

---

## 9. `api/` — "The Only Thing Users See"

### 9.1 Meaning

The API is the **public surface**. It hides everything else. The complexity lives inside Planner, Executor, and Reconciler — not at the call site.

### 9.2 Structure

```text
api/
├── normalize.py        # paxman.normalize(input_data, contract, budget, policy)
├── replay.py           # paxman.replay(artifact, contract)
├── types.py            # re-exports: CanonicalContract, CanonicalField, FieldType,
│                       #            ExecutionArtifact, Status, ConfidenceBand,
│                       #            ResolutionPolicy, Budget, Policy
├── errors.py           # public error types (re-export from errors.py)
├── protocols.py        # public SPIs: ContractAdapter, Capability, Heuristic
├── registry.py         # public registration: register_adapter, register_capability
└── version.py          # __version__ string
```

### 9.3 Public surface (V1)

```python
import paxman

# Top-level functions
paxman.normalize(input_data, contract, budget=None, policy=None) -> ExecutionArtifact
paxman.replay(artifact, contract) -> ExecutionArtifact
paxman.register_adapter(adapter: ContractAdapter) -> None
paxman.register_capability(capability: Capability) -> None
paxman.__version__ -> str

# Types
paxman.CanonicalContract
paxman.CanonicalField
paxman.FieldType
paxman.Status
paxman.ConfidenceBand
paxman.ResolutionPolicy
paxman.Budget
paxman.Policy
paxman.ExecutionArtifact
paxman.CurrencyPolicy

# Errors
paxman.PaxmanError
paxman.InvalidContractError
paxman.ExecutionError
paxman.CapabilityError
paxman.InferenceProviderError
paxman.BudgetExceededError
paxman.ReconciliationError
paxman.ReplayError
paxman.VersionMismatchError
paxman.HashMismatchError
paxman.ConfigurationError

# Protocols
paxman.ContractAdapter
paxman.Capability
```

### 9.4 Internal invariants

1. **Tiny surface.** The whole API should be learnable in minutes.
2. **No internal concepts leak out** (no `FieldPlan`, no `CapabilitySpec`, no `TruthLayer` exposed by name).
3. **No pipeline mutation allowed from API.**
4. **No stage awareness exposed directly** — the API is "normalize this against this contract under this budget".
5. **Stable and versioned.** The artifact is the version contract, not the API.
6. **CI enforces the public surface** — `tests/test_public_api.py` fails if anything is added without an ADR.

> API = "stable, minimal, deterministic surface"

---

## 10. Cross-Cutting Concerns

These live as **shared modules** at the package root, **not** as layers. Every layer may import from them. They may not import from any layer.

```text
paxman/
├── errors.py            # PaxmanError hierarchy
├── types.py             # shared enums, IDs, paths
├── protocols.py         # shared Protocols (subset of api.protocols)
├── versioning.py        # Paxman core version, capability versions, planner version
├── logging.py           # structured, deterministic logging (no timestamps in replay path)
├── budget.py            # Budget + Policy types
├── clock.py             # injectable Clock (for deterministic tests)
├── ids.py               # prefixed IDs (e.g., `field_`, `cap_`, `art_`)
└── serialization.py     # stable JSON encoder (sorted keys, no whitespace)
```

| Module | Visibility | Notes |
|---|---|---|
| `errors.py` | Public (re-exported in `api.errors`) | Exception hierarchy |
| `types.py` | Internal | Shared enums only; public types live in `api.types` |
| `protocols.py` | Internal (subset re-exported in `api.protocols`) | `ContractAdapter`, `Capability`, etc. |
| `versioning.py` | Internal | Version constants |
| `logging.py` | Internal | Logger factory |
| `budget.py` | Public (re-exported in `api.types`) | `Budget`, `Policy` |
| `clock.py` | Internal | For test injection |
| `ids.py` | Internal | Prefixed IDs |
| `serialization.py` | Internal | Stable JSON encoder |

---

## 11. System Boundary Rules (Hard Enforcement)

These are the **real architecture enforcement rules**. They are tested in CI.

### 11.1 Rule 1 — Contract Is the Only External-Schema Boundary

Adapters live inside `contract/`. Nothing else in Paxman knows about Pydantic, JSON Schema, OpenAPI, or any external schema language.

### 11.2 Rule 2 — Planner Never Executes

The planner emits `FieldPlan`s. It never calls a capability, never reads raw input beyond a lightweight input profile, and never touches the artifact.

### 11.3 Rule 3 — Capabilities Never Assign Confidence

Capabilities return `candidates + evidence + diagnostics`. Confidence is exclusively owned by the Reconciler (the Planner may emit a `target_confidence` but does not score candidates). See [ADR-0005](../adr/0005-confidence-ownership.md).

### 11.4 Rule 4 — Executor Never Replans

The executor runs the plan exactly as the Planner defined it. It can stop early, but it cannot reroute, retry structurally, or reorder.

### 11.5 Rule 5 — Reconciler Is the Only Truth Authority

The final `value` and `confidence` on a `FieldResult` are set by the Reconciler — nowhere else.

### 11.6 Rule 6 — Artifact Is the Only Replay Source

Replay rehydrates the captured truth. It does not recompute, re-execute, or reinterpret.

### 11.7 Rule 7 — API Hides Everything

The public surface exposes only `normalize`, `replay`, public types, and public errors. No subsystem names, no plan structure, no capability names leak out.

### 11.8 Rule 8 — No Persistence in Core

Paxman returns an `ExecutionArtifact` and stops. Storage, queues, and databases are the caller's responsibility.

### 11.9 Rule 9 — Cross-Cutting Modules May Not Import From Layers

`errors.py`, `types.py`, `protocols.py`, `versioning.py`, `logging.py`, `budget.py`, `clock.py`, `ids.py`, `serialization.py` are at the bottom of the DAG. They may not import from any subsystem layer.

### 11.10 Enforcement

| Rule | Enforced by |
|---|---|
| 1, 2, 3, 4, 5, 6, 7, 9 | `import-linter` config in `pyproject.toml` |
| 7 (additional) | `tests/test_public_api.py` snapshots the public surface |
| 8 | Manual code review; no storage imports anywhere |

---

## 12. V1 Capability Set (Explicit)

Per [PRD.md §8.1 FR-6](https://github.com/nexusnv/paxman/wiki/Internal-Development/Decision-History/PRD), V1 ships with exactly:

- `text_extraction`
- `regex_extraction`
- `lookup`
- `inference`
- `validation`

Everything else (capability marketplace, visual planners, graph execution, LLM planners, workflow orchestration, persistent execution, RAG, multi-agent coordination) is **postponed to V2**.

---

## 13. V1 Contract Adapter Set (Explicit)

Per [ARCHITECTURE.md §4.1](./architecture.md), V1 ships with:

- Pydantic Adapter (required)
- JSON Schema Adapter (required)
- Dict DSL Adapter (required)
- Optional OpenAPI Adapter (best-effort)

---

## 14. Determinism Guarantees

Determinism is **required**, not aspirational.

Given the same:

- Canonical contract
- Input profile
- Configuration
- Capability set
- Budget + policy
- Paxman core version
- Planner version
- Capability versions

Paxman MUST produce the same:

- `FieldPlan`s
- Execution order
- `ExecutionArtifact` (modulo declared non-deterministic capability outputs, which are recorded as evidence)

Replay reproduces the same artifact **without recomputation**.

See [REPLAY_AND_DETERMINISM.md](./replay-and-determinism.md) for the full replay model.

---

## 15. Public Protocols (SPIs)

These are the only stable extension points in V1.

### 15.1 `ContractAdapter` (in `api.protocols`)

```python
class ContractAdapter(Protocol):
    """SPI: translate an external contract format to/from CanonicalContract."""

    @property
    def format_id(self) -> str:
        """Stable identifier (e.g., 'pydantic', 'json_schema:draft-2020-12')."""
        ...

    def adapt(self, external: Any) -> CanonicalContract: ...
    def export(self, canonical: CanonicalContract) -> Any: ...
```

### 15.2 `Capability` (in `api.protocols`)

```python
class Capability(Protocol):
    """SPI: an atomic operation."""

    @property
    def spec(self) -> CapabilitySpec: ...

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult: ...
```

### 15.3 `Heuristic` (in `api.protocols`, post-V1)

```python
class Heuristic(Protocol):
    """SPI: a planner heuristic (post-V1)."""

    def select(self, field: CanonicalField, ctx: HeuristicContext) -> list[FieldPlanStep]: ...
```

### 15.4 `InferenceProvider` (internal, in `capabilities/inference.py`)

```python
class InferenceProvider(Protocol):
    """SPI: a model provider behind the inference capability (internal)."""

    def complete(self, request: CompletionRequest) -> Completion: ...
```

See [EXTENDING.md](./extending.md) for step-by-step guides.

---

## 16. Type Stub and Type-Checking Strategy

- The package ships `py.typed` (PEP 561 marker) at the package root.
- `mypy --strict` is the CI default for the public surface.
- The internal modules are type-checked with `mypy --strict` as well, but with allowance for `from __future__ import annotations` and `Protocol` use.
- `pyright` is run in CI for cross-validation.
- Type hints are mandatory on every public symbol and every internal symbol in `contract/`, `planner/`, `reconciler/`, `artifact/`.

---

## 17. Build and Packaging Strategy

### 17.1 Build backend

- **Backend:** `hatchling` (modern, fast, PEP 517 compliant).
- **Source layout:** `src/paxman/` (src-layout to prevent accidental imports from the project root).
- **Wheel + sdist** published to PyPI.

### 17.2 `pyproject.toml` layout (skeleton)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "paxman"
version = "0.1.0"  # dynamic from git
requires-python = ">=3.11"
license = { text = "MIT" }  # or Apache-2.0 — final TBD
authors = [{ name = "Paxman team" }]
description = "Contract-driven deterministic normalization engine."
readme = "README.md"

# Core dependencies (intentionally small)
dependencies = [
    "attrs>=23.0",
    "typing-extensions>=4.0",
]

[project.optional-dependencies]
# Adapter extras
pydantic = ["pydantic>=2.5"]
json-schema = ["jsonschema>=4.20"]
openapi = ["openapi-spec-validator>=0.6"]
# Provider extras
inference = []  # V1: no remote provider by default
# Convenience
all = ["paxman[pydantic,json-schema,openapi]"]

# Dev extras (also as PEP 735 dependency groups)
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "pytest-xdist>=3.3",
    "hypothesis>=6.0",
    "ruff>=0.4",
    "mypy>=1.10",
    "pyright>=1.1",
    "import-linter>=2.0",
    "interrogate>=1.7",
    "structlog>=24.1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/paxman"]

[tool.hatch.build.targets.wheel.force-include]
"src/paxman/py.typed" = "paxman/py.typed"

[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["docs/"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "ANN", "ASYNC", "S", "RUF"]
ignore = ["S101"]  # asserts OK in tests

[tool.mypy]
strict = true
python_version = "3.11"
files = ["src/paxman"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
markers = [
    "deterministic: tests that verify deterministic behavior",
    "replay: tests that verify replay equivalence",
    "property: hypothesis property tests",
    "slow: tests that take >1s",
]

[tool.importlinter:contract:internal-dag]
name = "Internal subsystem DAG"
type = "layers"
layers = [
    "paxman.api",
    "paxman.artifact",
    "paxman.reconciler",
    "paxman.executor",
    "paxman.capabilities",
    "paxman.planner",
    "paxman.contract",
    "paxman",  # cross-cutting modules (errors, types, ...)
]
```

### 17.3 Dependency policy

| Category | Where declared | Examples |
|---|---|---|
| **Core (always installed)** | `[project].dependencies` | `attrs`, `typing-extensions` |
| **Adapter extras** | `[project.optional-dependencies]` | `pydantic`, `jsonschema`, `openapi-spec-validator` |
| **Inference extras (V2+)** | `[project.optional-dependencies]` | `openai`, `anthropic` (V1: no remote provider) |
| **Dev extras** | `[project.optional-dependencies]` (or PEP 735) | `pytest`, `mypy`, `ruff`, `import-linter`, `hypothesis` |

**Hard rule:** core dependencies must be **≤ 3 packages** and **no transitive heavyweight deps** (no numpy, no pytorch, no requests by default). This keeps `pip install paxman` cheap and safe.

See [DEPENDENCIES.md](./dependencies.md) for the full policy.

---

## 18. Tooling Configuration

| Tool | Purpose | Config location | CI behavior |
|---|---|---|---|
| `ruff` | Lint + format | `pyproject.toml` `[tool.ruff]` | Required to pass |
| `mypy` | Static type checking | `pyproject.toml` `[tool.mypy]` | Required to pass on public surface; advisory on internals |
| `pyright` | Cross-validation type checking | `pyrightconfig.json` | Required to pass |
| `import-linter` | Enforce the module DAG | `pyproject.toml` `[tool.importlinter]` | Required to pass |
| `pytest` | Test runner | `pyproject.toml` `[tool.pytest.*]` | Required to pass with ≥ 90% coverage on core |
| `hypothesis` | Property-based testing | test files | Used for determinism and replay tests |
| `interrogate` | Docstring coverage | `pyproject.toml` `[tool.interrogate]` | Required: 100% on public surface |
| `pre-commit` | Git hooks | `.pre-commit-config.yaml` | Local; CI runs the same hooks |

---

## 19. Test Layout

```text
tests/
├── unit/
│   ├── contract/
│   ├── planner/
│   ├── capabilities/
│   ├── executor/
│   ├── reconciler/
│   ├── artifact/
│   └── api/
├── integration/
│   ├── end_to_end/
│   └── cross_subsystem/
├── property/
│   ├── determinism/
│   └── replay/
├── fixtures/                   # see tests/fixtures/README.md
│   ├── README.md
│   ├── DATASET_LICENSES.md     # attribution for every vendored file
│   ├── contracts/              # LAYER 3: pydantic, json_schema, dict_dsl, openapi
│   ├── inputs/                 # LAYER 4: vendored open datasets + LAYER 1: adversarial
│   ├── artifacts/              # LAYER 3: golden ExecutionArtifact JSON
│   └── generated/              # LAYER 2: programmatic (gitignored)
├── public_api/                 # tests that the public surface is stable
└── conftest.py
```

The full test data policy, dataset catalog, and licensing rules are in **[docs/TEST_DATA.md](../contributing/test-data.md)**. Briefly: Layer 1 = hand-written edge cases, Layer 2 = programmatic (factory_boy, faker, hypothesis), Layer 3 = curated fixtures with golden artifacts, Layer 4 = vendored open-dataset samples, Layer 5 = real production data (never committed).

See [TESTING_STRATEGY.md](../contributing/testing-strategy.md) for the test strategy and [docs/TEST_DATA.md](../contributing/test-data.md) for the test data policy.

---

## 20. One-Line Mental Model

> Paxman is a contract-driven deterministic normalization engine: the `contract` subsystem canonicalizes and validates the caller's schema, the `planner` synthesizes a field-by-field plan, `capabilities` execute the plan atomically, the `executor` collects candidate evidence, the `reconciler` assigns final confidence and truth, and the `artifact` freezes the evidence-backed result for replay behind a tiny public `api` — with the module DAG enforced by `import-linter` and the public surface enforced by snapshot tests.

---

## 21. References

- [PRD.md](https://github.com/nexusnv/paxman/wiki/Internal-Development/Decision-History/PRD) — Product requirements, success metrics, V1 acceptance criteria.
- [ARCHITECTURE.md](./architecture.md) — System architecture, ADRs, sequence diagram.
- [GLOSSARY.md](./glossary.md) — Full domain vocabulary.
- [V1_ACCEPTANCE_CRITERIA.md](https://github.com/nexusnv/paxman/wiki/Internal-Development/Decision-History/V1-acceptance-criteria) — V1 definition of done.
- [REPLAY_AND_DETERMINISM.md](./replay-and-determinism.md) — Replay model deep dive.
- [SECURITY.md](../security/index.md) — Threat model and PII handling.
- [TESTING_STRATEGY.md](../contributing/testing-strategy.md) — Test seams and determinism tests.
- [docs/TEST_DATA.md](../contributing/test-data.md) — Test data policy, dataset catalog, licensing rules.
- [DEVELOPMENT.md](../contributing/development.md) — Local dev setup.
- [EXTENDING.md](./extending.md) — How to add a capability, adapter, or provider.
- [DEPENDENCIES.md](./dependencies.md) — Core vs optional dependencies.
- [docs/adr/](../adr/) — Architecture Decision Records.

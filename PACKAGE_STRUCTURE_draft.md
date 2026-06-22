# Paxman Package Architecture (V1)

This is the **stable mental model for the codebase**, derived from `ARCHITECHTURE.md` and `PRD.md`.

It reflects the V1 product definition: a **contract-driven, field-centric, deterministic normalization engine**.

---

# 1. Top-Level Structure (Conceptual Layers)

Paxman is split into 6 strict subsystem zones, plus an `api/` public surface:

```
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

Everything else is derived from these boundaries.

> **Core principle:** Contracts define *what* output must look like. Planner defines *what to do*. Executor defines *how to run it*. Reconciler defines *what is ultimately true*. Artifact defines *what was produced*.

---

# 2. CONTRACT — "Translation + Validation Boundary"

## Meaning

Contract is Paxman's **adapter + validation subsystem**. It is the only layer that knows about external contract formats.

It converts caller-provided contracts (Pydantic, JSON Schema, Dict DSL, OpenAPI) into Paxman's **canonical internal representation**, and rejects anything invalid.

---

## Structure

```
contract/
├── canonical.py        # CanonicalContract + CanonicalField data models
├── validator.py        # rejects invalid contracts → INVALID_CONTRACT
├── semantics.py        # semantic tag handling, structural vs semantic layers
│
└── adapters/
    ├── pydantic.py     # Pydantic model → canonical
    ├── json_schema.py  # JSON Schema → canonical
    ├── dict_dsl.py     # internal Dict DSL → canonical
    └── openapi.py      # Optional OpenAPI → canonical
```

---

## Guardrails

* Adapters only produce canonical output; they never execute or plan.
* Validator is mandatory — invalid contracts fail immediately with `INVALID_CONTRACT`.
* Core types: `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`.
* `MONEY` is first-class (precision, currency, ISO 4217, FX, rounding).
* `CanonicalField` carries: `id`, `path`, `name`, `type`, `required`, `critical`, `nullable`, `confidence_threshold`, `evidence_required`, `semantic_tags`, `fallback_policy`.
* `CanonicalContract` carries: `id`, `version`, `fields`, `constraints`, `policies`.
* No adapter is allowed to leak its source representation downstream.

> Contract = "the only place that knows about external schemas"

---

# 3. PLANNER — "Field-Centric Plan Synthesis"

## Meaning

Planner is the **deterministic brain** of Paxman. It does NOT execute anything.

It reads the canonical contract, analyzes the input profile, and produces a **field-by-field execution plan** — one plan per required field, not one plan per document.

---

## Structure

```
planner/
├── planner.py         # top-level: contract + input + budget → plan
├── heuristics.py      # ordering rules (explicit evidence → local deterministic → ... → UNRESOLVED)
├── scoring.py         # candidate cost / confidence / coverage scoring
├── policies.py        # budget, accuracy, fallback policies
└── field_plan.py      # FieldPlan data model (one per required field)
```

---

## Guardrails

* **Field-centric, not document-centric.** Each required field gets its own `FieldPlan`.
* **Deterministic.** Given the same canonical contract + input profile + config + capability set, the planner must produce the same plan.
* **Rule-based in V1.** No LLM planner, no agent planner, no AI-generated planning logic.
* **Heuristic ordering** (highest to lowest preference):
  1. Explicit evidence
  2. Local deterministic extraction
  3. Structured lookup
  4. Derived computation
  5. Local inference
  6. Remote inference
  7. UNRESOLVED
* Planner owns confidence **assignment** (not capabilities).
* Planner never touches raw input execution; it only emits `FieldPlan`s.

> Planner = "synthesizes the cheapest trustworthy path per field"

---

# 4. CAPABILITIES — "Atomic Operations"

## Meaning

Capabilities are the **only executable primitives**. They are reusable atomic operations with metadata describing input, output, cost, and determinism.

LLMs are **providers behind inference capabilities**, not capabilities themselves.

---

## Structure

```
capabilities/
├── base.py                # Capability abstract interface
├── registry.py            # capability lookup + metadata
├── metadata.py            # CapabilitySpec (input/output types, cost, determinism)
│
└── v1/
    ├── text_extraction.py     # pull text out of raw input
    ├── regex_extraction.py    # pattern-based local extraction
    ├── lookup.py              # structured / retrieval-based extraction
    ├── inference.py           # model-backed inference (LLM is a provider)
    └── validation.py          # verify a candidate value
```

---

## Guardrails

* V1 capability surface is **deliberately small**:
  * Text extraction
  * Regex extraction
  * Lookup / retrieval
  * Inference
  * Validation
* **Capabilities never assign confidence.** They return candidates + evidence + diagnostics only.
* Confidence is exclusively owned by the Planner and Reconciler (prevents confidence inflation).
* Every capability must expose a `CapabilitySpec` (input/output, cost, determinism).
* Capabilities are stateless and side-effect-free except for declared external effects (which must be captured in evidence).

> Capabilities = "pure atomic operations, never the source of truth"

---

# 5. EXECUTOR — "Deterministic Runner"

## Meaning

Executor **runs the plan** produced by the Planner. It does not replan, reroute, or optimize.

It walks the per-field plans in order, invokes capabilities, collects evidence, and stops early when the contract is satisfied with acceptable confidence.

---

## Structure

```
executor/
├── executor.py         # top-level execution driver
├── field_runner.py     # executes one FieldPlan
├── evidence.py         # evidence + diagnostics collection
├── early_stop.py       # short-circuit when contract is satisfied
└── execution_state.py  # transient in-flight state (never authoritative)
```

---

## Guardrails

* Executor follows the plan **exactly as Planner defined it**. No replanning, no rerouting, no structural retries.
* Executor passes context forward, never mutates the plan.
* Executor stops early when the contract is satisfied at acceptable confidence.
* Executor returns explicit `UNRESOLVED` when it cannot satisfy a field — never silent guessing.
* Executor never assigns final confidence — only collects candidate evidence.

> Executor = "hands that execute the plan, never rewrite it"

---

# 6. RECONCILER — "Truth Resolution"

## Meaning

Reconciler is a **first-class subsystem**. It is where Paxman converts uncertainty into trustworthy normalized output.

It owns the final truth.

---

## Structure

```
reconciler/
├── reconciler.py        # top-level: candidates → resolved truth
├── merge.py             # candidate merging strategies
├── conflict.py          # conflict detection
├── evidence_compare.py  # compare evidence quality across candidates
├── confidence.py        # confidence assignment (bands: CERTAIN/HIGH/MEDIUM/LOW/UNTRUSTED)
├── unresolved.py        # explicit unresolved state handling
└── truth.py             # TruthLayer data models (Contract / Candidate / Resolved)
```

---

## Guardrails

* Reconciler is the **only** layer that assigns final confidence and final truth.
* Three truth layers are explicit:
  * **Contract Truth** — what the caller requires
  * **Candidate Truth** — what capabilities discovered
  * **Resolved Truth** — what Reconciler accepts into the artifact
* Reconciler never executes capabilities.
* Reconciler never reads raw input.
* Reconciler never sees external schemas.
* Unresolved fields are explicit, never silent.

> Reconciler = "where uncertainty becomes trustworthy normalized output"

---

# 7. ARTIFACT — "The Product + Replay Source"

## Meaning

The artifact is the **final output bundle** returned by Paxman. It contains normalized data, evidence, diagnostics, unresolved fields, plan metadata, and replay data.

It is the **only** replay mechanism.

---

## Structure

```
artifact/
├── artifact.py          # ExecutionArtifact + FieldResult data models
├── confidence.py        # confidence band mapping (float ↔ CERTAIN/HIGH/MEDIUM/LOW/UNTRUSTED)
├── replay.py            # replay hash computation
├── evidence.py          # evidence references + provenance
├── diagnostics.py       # structured diagnostics
├── statistics.py        # execution statistics
└── serializer.py        # stable encoding rules
```

---

## Guardrails

* `ExecutionArtifact` is the **product** — it contains:
  * `normalized_data`
  * `field_results`
  * `unresolved_fields`
  * `evidence`
  * `diagnostics`
  * `execution_plan`
  * `replay_hash`
  * `statistics`
* `FieldResult` carries: `field_id`, `status`, `value`, `confidence`, `evidence_refs`.
* Statuses: `SUCCESS`, `PARTIAL_SUCCESS`, `UNRESOLVED`, `INVALID_CONTRACT`, `EXECUTION_FAILED`.
* Replay hash captures: canonical contract representation + input fingerprint + planner version + capability versions + configuration + constraints.
* Artifact is replayable **without recomputation** — rehydration only.
* No persistence in core. The caller stores the artifact.

> Artifact = "frozen, evidence-backed, replayable truth"

---

# 8. API — "The Only Thing Users See"

## Meaning

API is the **public surface**. It hides everything else. The complexity lives inside Planner, Executor, and Reconciler — not at the call site.

---

## Structure

```
api/
├── normalize.py        # paxman.normalize(input_data, contract, budget, policy)
├── replay.py           # replay from artifact
├── types.py            # public type aliases (CanonicalContract, ExecutionArtifact, ...)
└── errors.py           # public error types (INVALID_CONTRACT, EXECUTION_FAILED, ...)
```

---

## Guardrails

* **Tiny surface.** The whole API should be learnable in minutes.
* No internal concepts leak out (no `FieldPlan`, no `CapabilitySpec`, no `TruthLayer` exposed by name).
* No pipeline mutation allowed from API.
* No stage awareness exposed directly — the API is "normalize this against this contract under this budget".
* Stable and versioned. The artifact is the version contract, not the API.

> API = "stable, minimal, deterministic surface"

---

# 9. Cross-Cutting Concerns

These live as **shared modules**, not as layers:

```
paxman/
├── errors.py            # INVALID_CONTRACT, EXECUTION_FAILED, INVALID_INPUT, ...
├── versioning.py        # Paxman core version, capability versions, planner version
├── types.py             # shared enums, IDs, paths
└── logging.py           # structured, deterministic logging (no timestamps in replay path)
```

---

# 10. Key System Boundary Rules

These are the **real architecture enforcement rules**:

---

## Rule 1: Contract Is the Only External-Schema Boundary

Adapters live inside `contract/`. Nothing else in Paxman knows about Pydantic, JSON Schema, OpenAPI, or any external schema language.

---

## Rule 2: Planner Never Executes

Planner emits `FieldPlan`s. It never calls a capability, never reads raw input beyond a lightweight input profile, and never touches the artifact.

---

## Rule 3: Capabilities Never Assign Confidence

Capabilities return `candidates + evidence + diagnostics`. Confidence is exclusively owned by the Planner and Reconciler.

---

## Rule 4: Executor Never Replans

Executor runs the plan exactly as the Planner defined it. It can stop early, but it cannot reroute, retry structurally, or reorder.

---

## Rule 5: Reconciler Is the Only Truth Authority

The final `value` and `confidence` on a `FieldResult` are set by the Reconciler — nowhere else.

---

## Rule 6: Artifact Is the Only Replay Source

Replay rehydrates the captured truth. It does not recompute, re-execute, or reinterpret.

---

## Rule 7: API Hides Everything

The public surface exposes only `normalize`, `replay`, public types, and public errors. No subsystem names, no plan structure, no capability names leak out.

---

## Rule 8: No Persistence in Core

Paxman returns an `ExecutionArtifact` and stops. Storage, queues, and databases are the caller's responsibility.

---

# 11. V1 Capability Set (Explicit)

Per `PRD.md §7.8` and `ARCHITECHTURE.md §16.1`, V1 ships with exactly:

* Text extraction
* Regex extraction
* Lookup / retrieval
* Inference
* Validation

Everything else (capability marketplace, visual planners, graph execution, LLM planners, workflow orchestration, persistent execution, RAG, multi-agent coordination) is **postponed to V2**.

---

# 12. V1 Contract Adapter Set (Explicit)

Per `ARCHITECHTURE.md §5`, V1 ships with:

* Pydantic Adapter
* JSON Schema Adapter
* Dict DSL Adapter
* Optional OpenAPI Adapter

---

# 13. Determinism Guarantees

Determinism is **required**, not aspirational.

Given the same:
* canonical contract
* input profile
* configuration
* capability set
* budget + policy

Paxman MUST produce the same:
* `FieldPlan`s
* execution order
* `ExecutionArtifact` (modulo declared non-deterministic capability outputs, which must be recorded as evidence)

Replay reproduces the same artifact **without recomputation**.

---

# 14. One-Line Mental Model

If everything else is forgotten:

> Paxman is a contract-driven deterministic normalization engine: the Contract subsystem canonicalizes and validates the caller's schema, the Planner synthesizes a field-by-field plan, Capabilities execute the plan atomically, the Reconciler assigns final confidence and truth, and the Artifact freezes the evidence-backed result for replay behind a tiny public API.

# Paxman Glossary

> **Status:** Stable v1.
> **Audience:** Anyone reading Paxman docs. This is the **single source of truth** for vocabulary.
> **Related docs:** [ARCHITECTURE.md](./architecture.md), [PACKAGE_STRUCTURE.md](./package-structure.md)

All Paxman documentation links to this glossary. If a term is defined here, it is used **only** with that meaning across the project.

---

## A

### Adapter (Contract Adapter)

A pluggable component that translates an external contract format (Pydantic, JSON Schema, OpenAPI, etc.) into Paxman's internal `CanonicalContract` and back.

**Examples:**

- `PydanticAdapter` — Pydantic model class ↔ `CanonicalContract`
- `JsonSchemaAdapter` — JSON Schema document ↔ `CanonicalContract`
- `DictDSLAdapter` — Paxman's internal DSL ↔ `CanonicalContract`
- `OpenAPIAdapter` — OpenAPI spec ↔ `CanonicalContract` (V1, best-effort)

**Related:** [Contract](#contract), [Canonical Contract](#canonical-contract), [Contract Adapter System](#contract-adapter-system)

### Artifact

The frozen, evidence-backed, replayable output bundle returned by `paxman.normalize()`. The artifact is the **product** of Paxman. It contains `normalized_data`, `field_results`, `unresolved_fields`, `evidence`, `diagnostics`, `execution_plan`, `replay_hash`, and `statistics`.

**Related:** [ExecutionArtifact](#executionartifact), [Replay](#replay), [Replay Hash](#replay-hash)

### API (Public API)

The single import `paxman` and the small set of functions, types, errors, and protocols re-exported from `paxman/__init__.py`. Everything else is internal.

**Stable surface (V1):** `paxman.normalize`, `paxman.replay`, `paxman.register_adapter`, `paxman.register_capability`, plus the public types and errors listed in [PACKAGE_STRUCTURE.md §9](./package-structure.md).

**Related:** [API Subsystem](#api-subsystem)

### API Subsystem

The `paxman.api` internal module that wraps all subsystems and exposes the public surface. It is the **only** layer users import from.

---

## B

### Band (Confidence Band)

One of the five fixed labels a confidence score maps to: `CERTAIN`, `HIGH`, `MEDIUM`, `LOW`, `UNTRUSTED`. The mapping from float to band is deterministic and lives in the Reconciler.

**Related:** [Confidence](#confidence), [Reconciler](#reconciler)

### Budget

A caller-supplied hard cap on the cost, latency, and number of capability invocations for a single run. The Executor tracks the budget and short-circuits when exhausted.

**Fields:** `max_total_cost_usd`, `max_total_latency_ms`, `max_remote_inference_calls`, `max_capability_invocations`.

**Related:** [Policy](#policy), [BudgetExceededError](#budgetexceedederror)

### BudgetExceededError

Raised by the Executor when a budget field is exhausted. The artifact is returned with status `PARTIAL_SUCCESS` and a diagnostic in `diagnostics`.

**Related:** [Budget](#budget)

---

## C

### Candidate

A single proposed value for a field, returned by a capability. A candidate is **not yet** the resolved value. Candidates are passed from the Executor to the Reconciler.

**Related:** [Candidate Truth](#candidate-truth), [Reconciliation](#reconciliation)

### Candidate Truth

One of Paxman's three truth layers. The set of all candidates produced by capabilities, before the Reconciler resolves them.

**Related:** [Contract Truth](#contract-truth), [Resolved Truth](#resolved-truth)

### Canonical Contract

The internal, language-agnostic representation of a contract after adapter translation. It is a `CanonicalContract` object with `id`, `version`, `fields[]`, `constraints[]`, and `policies`. Every other Paxman subsystem reads only the canonical form.

**Related:** [Contract](#contract), [Contract Adapter](#adapter-contract-adapter)

### Capability

A reusable, versioned atomic operation that produces candidates for one or more field types. The V1 surface is small: `text_extraction`, `regex_extraction`, `lookup`, `inference`, `validation`.

**Related:** [CapabilitySpec](#capabilityspec), [Capability Registry](#capability-registry), [CapabilityResult](#capabilityresult)

### Capability Registry

The internal index of all registered capabilities. The Planner consults the registry when synthesizing a `FieldPlan`. Registration is via `paxman.register_capability()`.

### CapabilityResult

The output of a capability invocation: `candidates[]`, `evidence_refs[]`, `diagnostics[]`. Capabilities do not assign confidence.

**Related:** [Capability](#capability), [Evidence](#evidence)

### CapabilitySpec

The metadata describing a capability: `id`, `version`, `input_type`, `output_type`, `cost_estimate`, `deterministic` flag, `required_providers[]`.

### Clock (Injectable)

A `Clock` abstraction used by tests to inject a fixed time. Production uses the real clock; the replay path uses no clock at all.

**Related:** [Determinism](#determinism)

### Confidence

A float in `[0.0, 1.0]` representing the Reconciler's trust in a resolved value, plus a derived band (`CERTAIN` / `HIGH` / `MEDIUM` / `LOW` / `UNTRUSTED`).

**Ownership rule:** confidence is **only** assigned by the Reconciler. Capabilities return candidates without confidence. The Planner emits a `target_confidence` per field but does not score candidates. See [ADR-0005](../adr/0005-confidence-ownership.md).

**Related:** [Band](#band-confidence-band), [Confidence Threshold](#confidence-threshold), [Reconciler](#reconciler)

### Confidence Threshold

The minimum confidence required to mark a field `SUCCESS` instead of `PARTIAL_SUCCESS`. Set per-field on the `CanonicalContract`.

**Related:** [Confidence](#confidence)

### Conflict

A disagreement between two or more candidates for the same field. The Reconciler detects conflicts and either picks the highest-evidence candidate or marks the field `PARTIAL_SUCCESS` with both candidates' evidence.

**Related:** [Reconciler](#reconciler)

### Contract

A caller-supplied schema describing the target shape of normalized output. The contract is the entry point to Paxman: `paxman.normalize(input_data, contract=...)`. The contract may be a Pydantic model, a JSON Schema document, a Paxman Dict DSL spec, or an OpenAPI schema.

**Ownership rule:** the **caller** owns the contract. Paxman never owns schemas, domain ontologies, or business standards.

**Related:** [Canonical Contract](#canonical-contract), [Contract Adapter](#adapter-contract-adapter), [Contract Validator](#contract-validator)

### Contract Adapter System

The `paxman.contract` subsystem. The only layer that knows about external contract formats.

**Related:** [Contract](#contract), [Adapter (Contract Adapter)](#adapter-contract-adapter)

### Contract Policy

A per-contract override of the call-site `Policy`. Example: "this contract's `tax_amount` field may never be inferred; it must be explicit or `UNRESOLVED`."

**Related:** [Policy](#policy), [Contract](#contract)

### Contract Validator

The component of the `contract/` subsystem that rejects invalid contracts with `InvalidContractError`. Validation is mandatory; the Executor never receives an invalid contract.

**Related:** [Contract](#contract), [Contract Adapter System](#contract-adapter-system)

### Currency Policy

A policy object attached to a `MONEY` field that describes how cross-currency arithmetic is handled. Options include `STRICT_MATCH` (default; reject cross-currency), `ALLOW_FX` (apply FX rate), and `REJECT_WITHOUT_RATE` (require an explicit FX rate).

**Related:** [MONEY](#money), [Policy](#policy)

---

## D

### Data Flow

The sequence of data structures that cross subsystem boundaries during a run: `input_data` → `CanonicalContract` → `InputProfile` → `ExecutionPlan` → `FieldPlan[]` → `CandidateResult[]` → `ResolvedResult[]` → `ExecutionArtifact`.

### Determinism

A property of the **planner** and **executor**: given the same canonical contract, input profile, configuration, capability set, budget, and policy, the planner produces the same `ExecutionPlan` and the executor runs the same capabilities in the same order. Determinism is required for replay; it does **not** require capabilities themselves to be deterministic. Non-deterministic capability outputs are recorded as evidence.

**Related:** [Replay](#replay), [Capability](#capability), [Inference](#inference)

### Diagnostic

A structured note attached to a candidate or to the artifact (e.g., "skipped remote inference because `policy.allow_remote_inference=False`"). Distinct from errors — diagnostics are informational.

---

## E

### Early Stop

A property of the Executor: when a `FieldPlan` has produced a candidate that meets the field's `confidence_threshold`, the Executor stops invoking further capabilities for that field. The Executor never retries structurally; it only short-circuits within a `FieldPlan`'s `capability_chain`.

**Related:** [Executor](#executor), [Field Plan](#field-plan)

### Evidence

Provenance metadata attached to a candidate or resolved value: source span, capability id + version, model id (if inference), timestamp of capture, and any other capability-specific metadata. Evidence is the audit trail.

**Related:** [EvidenceRef](#evidenceref), [Artifact](#artifact)

### EvidenceRef

A pointer to a piece of evidence stored in the artifact. `FieldResult.evidence_refs` is a list of these. The full evidence payloads are stored in `ExecutionArtifact.evidence` (when `policy.embed_evidence_payload=True`); otherwise only references are stored.

**Related:** [Evidence](#evidence)

### ExecutionArtifact

The concrete Python type of an artifact. Public, re-exported as `paxman.ExecutionArtifact`.

**Related:** [Artifact](#artifact)

### ExecutionPlan

The planner's output: an ordered list of `FieldPlan`s. Internal, not re-exported.

**Related:** [Field Plan](#field-plan), [Planner](#planner)

### Executor

The `paxman.executor` subsystem. Runs the plan exactly as the Planner defined it. Stops early when a field meets its confidence threshold. Never assigns final confidence.

**Related:** [Field Plan](#field-plan), [Early Stop](#early-stop), [Reconciler](#reconciler)

### Extension Point

A public SPI for adding new functionality. The V1 extension points are `ContractAdapter`, `Capability`, and (post-V1) `Heuristic`. See [EXTENDING.md](./extending.md).

---

## F

### Field

A single property in a `CanonicalContract` or a contract. Has a `path`, `type`, `required`, `critical`, `nullable`, `confidence_threshold`, `evidence_required`, `semantic_tags`, and `fallback_policy`.

**Related:** [Canonical Field](#canonical-field), [Required Field](#required-field), [Critical Field](#critical-field)

### Field Plan (FieldPlan)

The planner's per-field plan. Specifies an ordered `capability_chain` and an `early_stop_threshold`. One per required field.

**Related:** [Field](#field), [Planner](#planner)

### Field Type

One of the nine V1 types: `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`.

**Related:** [Type](#type)

### Frozen

A property of the artifact: once emitted, the artifact is **immutable** for replay purposes. Modifying any field of an artifact changes its `replay_hash` and the tamper is detected on replay.

**Related:** [Artifact](#artifact), [Replay Hash](#replay-hash)

---

## H

### Hash Mismatch

A replay-time error: the `replay_hash` of the supplied artifact does not match the hash recomputed from its contents. This indicates tampering. The error is `HashMismatchError`.

**Related:** [Replay](#replay), [Tamper Detection](#tamper-detection)

### Heuristic

A planner rule that ranks capabilities for a field. V1 ships a single heuristic chain (explicit evidence → local deterministic → ... → `UNRESOLVED`). Custom heuristics are post-V1.

**Related:** [Planner](#planner), [Field Plan](#field-plan)

---

## I

### Inference

The capability of producing candidates via a model. In V1, "inference" is the **capability**; the model is the **provider**. The same capability may be backed by different providers at different times.

**Related:** [Capability](#capability), [Inference Provider](#inference-provider)

### Inference Provider

A model implementation that satisfies the `InferenceProvider` SPI. In V1, the only shipped provider is a local stub. V2+ will ship OpenAI, Anthropic, etc.

**Related:** [Inference](#inference)

### Invalid Contract

A contract that failed `ContractValidator`. Produces `InvalidContractError`. The Executor is never invoked.

**Related:** [Contract Validator](#contract-validator)

### Input Profile

A lightweight classification of the raw input (size, type, content density). The Planner uses it to choose heuristics. The Input Profile is built **without** invoking capabilities.

---

## L

### Lookup

The capability of producing a candidate by structured or retrieval-based lookup. The V1 lookup capability supports both deterministic backends (e.g., a local dict) and vector backends (post-V1).

**Related:** [Capability](#capability)

---

## M

### Merging

The Reconciler's job of combining multiple candidates for the same field. Strategies include: union, intersection, prefer-by-evidence-quality, prefer-by-confidence.

**Related:** [Reconciler](#reconciler), [Conflict](#conflict)

### MONEY

A first-class field type for monetary values. Carries a numeric amount, an ISO-4217 currency code, and (optionally) a precision. Cross-currency arithmetic is governed by a `CurrencyPolicy`.

**Related:** [Currency Policy](#currency-policy), [Field Type](#field-type)

---

## N

### Non-Deterministic Capability

A capability whose output may vary for the same input (e.g., `inference` backed by a remote LLM). Paxman records the actual output as evidence and the replay path does not re-invoke the capability.

**Related:** [Determinism](#determinism), [Replay](#replay)

### Normalized Data

The portion of the artifact that conforms to the contract shape. `ExecutionArtifact.normalized_data` is a Python dict (or Pydantic model, when serialized back).

**Related:** [Artifact](#artifact)

---

## O

### Observability

The set of hooks and metrics Paxman emits. See [ARCHITECTURE.md §12](./architecture.md) for the full model.

**Related:** [Structured Logging](#structured-logging), [Metrics](#metrics)

### OpenAPI Adapter

A best-effort `ContractAdapter` for OpenAPI 3.x. In V1 it covers a useful subset of OpenAPI features, not the full spec.

---

## P

### Path (Field Path)

A dotted JSON-Path-like identifier of a field within the contract (e.g., `line_items[].price`). Used in `CanonicalField.path` and in evidence references.

### Planner

The `paxman.planner` subsystem. The deterministic, rule-based brain. Produces `ExecutionPlan` from `CanonicalContract` + `InputProfile` + `Budget` + `Policy` + capability registry.

**Related:** [Field Plan](#field-plan), [Heuristic](#heuristic)

### Policy

A caller-supplied set of soft preferences: `allow_remote_inference`, `allow_local_inference`, `confidence_floor`, `unresolved_acceptable`, `currency_policy`, `emit_metrics`, `log_raw_input`, `record_inference_io`, `embed_evidence_payload`.

**Related:** [Budget](#budget), [Contract Policy](#contract-policy)

### Protocol (Public SPI)

A `typing.Protocol` exposed in `paxman.protocols` that callers may implement to extend Paxman. V1 SPIs: `ContractAdapter`, `Capability`. Post-V1: `Heuristic`.

### Provider

A pluggable implementation behind a capability. The V1 model is "LLM as a provider behind the inference capability." Providers are internal; capabilities are public.

**Related:** [Inference Provider](#inference-provider)

---

## R

### Replay

The act of rehydrating a previously produced `ExecutionArtifact` to its original state **without recomputation**. Replay verifies the `replay_hash`, checks version compatibility, and returns a new `ExecutionArtifact` that is byte-equal to the original.

**Related:** [Artifact](#artifact), [Replay Hash](#replay-hash)

### Replay Hash

The deterministic SHA-256 (or similar) signature over the canonical contract + input fingerprint + planner version + capability versions + configuration + constraints. The hash uniquely identifies an artifact.

**Related:** [Artifact](#artifact), [Replay](#replay)

### Required Field

A field marked `required=True` in the contract. If unresolved, the artifact status is at most `PARTIAL_SUCCESS` (or `UNRESOLVED` if `policy.unresolved_acceptable=False`).

**Related:** [Field](#field), [Critical Field](#critical-field)

### Resolved Truth

One of Paxman's three truth layers. The output of the Reconciler — the final value and final confidence accepted into the artifact.

**Related:** [Contract Truth](#contract-truth), [Candidate Truth](#candidate-truth)

### Reconciler

The `paxman.reconciler` subsystem. Merges candidates, detects conflicts, assigns final confidence, and resolves truth. The only place that mutates Candidate Truth into Resolved Truth.

**Related:** [Merging](#merging), [Confidence](#confidence)

### Resolution Policy

A per-field fallback policy that tells the planner what to do when the heuristic chain is exhausted. Options include: `UNRESOLVED` (default), `USE_DEFAULT`, `REQUIRE_HUMAN`.

**Related:** [Field](#field), [Policy](#policy)

### Result Types (Field)

The Reconciler's per-field output: `FieldResult` with `status`, `value`, `confidence`, and `evidence_refs`. Distinct from `Candidate`.

**Related:** [Candidate](#candidate), [FieldResult](#fieldresult)

### Rehydration

The internal process that turns a serialized artifact back into a live `ExecutionArtifact` object on replay. Rehydration is pure deserialization — no planner, executor, or reconciler is invoked.

**Related:** [Replay](#replay)

---

## S

### Semantic Tag

A string attached to a field in the canonical contract that describes its meaning (e.g., `currency`, `iso4217`, `email`, `phone`). Used by the planner to choose capabilities. Distinct from structural metadata.

**Related:** [Canonical Field](#canonical-field)

### Status

One of the five labels attached to a `FieldResult` or an `ExecutionArtifact`: `SUCCESS`, `PARTIAL_SUCCESS`, `UNRESOLVED`, `INVALID_CONTRACT`, `EXECUTION_FAILED`. See [ARCHITECTURE.md §6](./architecture.md).

### Structured Logging

The logging format Paxman emits (via `structlog` or an injected logger). Determinism-safe: no timestamps in the replay path.

**Related:** [Observability](#observability)

### Subsystem

One of the seven internal modules: `contract/`, `planner/`, `capabilities/`, `executor/`, `reconciler/`, `artifact/`, `api/`. Each has strict responsibilities and forbidden imports.

**Related:** [Architecture Overview](./architecture.md#1-architecture-overview)

---

## T

### Tamper Detection

The replay path's ability to detect any modification to an artifact. The `replay_hash` is recomputed on replay and compared to the recorded hash; mismatch raises `HashMismatchError`.

**Related:** [Replay](#replay), [Hash Mismatch](#hash-mismatch)

### Target Confidence

The minimum confidence a field's first successful candidate must reach for the Executor to early-stop. This is the field's `confidence_threshold` from the `CanonicalContract`. The Reconciler is the only place that decides whether a candidate actually meets it (and it never re-invokes capabilities — the candidate is given).

**Related:** [Confidence Threshold](#confidence-threshold), [Early Stop](#early-stop)

### Truth Layer

One of three explicit data layers in Paxman: Contract Truth, Candidate Truth, Resolved Truth.

**Related:** [Contract Truth](#contract-truth), [Candidate Truth](#candidate-truth), [Resolved Truth](#resolved-truth)

### Type (Field Type)

See [Field Type](#field-type).

### Truth Comparison

The Reconciler's process of comparing two candidates' evidence quality (e.g., source span coverage, capability determinism, provider trustworthiness). The better-evidenced candidate wins ties.

**Related:** [Reconciler](#reconciler)

---

## U

### UNRESOLVED

A field status indicating that no candidate met the field's `confidence_threshold`. The field is included in `ExecutionArtifact.unresolved_fields` with a `reason` (e.g., "no capability applicable", "budget exhausted", "inference disallowed by policy").

**Related:** [Status](#status), [Unresolved Field](#unresolved-field)

### Unresolved Field

A required field that the engine could not resolve with sufficient confidence. Always reported explicitly, never silently. Carries a `reason` and a list of attempted capabilities.

**Related:** [UNRESOLVED](#unresolved)

---

## V

### Validation (Capability)

The V1 capability of verifying a candidate value against a constraint. Deterministic. Used by the Reconciler to gate acceptance of inference candidates.

**Related:** [Capability](#capability), [Reconciler](#reconciler)

### Versioning

Paxman's multi-dimensional versioning model: library semver, planner version, capability versions, and contract schema versions. See [ARCHITECTURE.md §9](./architecture.md) for the full strategy.

**Related:** [Library Version](#library-version), [Capability Version](#capability-version), [Contract Schema Version](#contract-schema-version)

### Version Mismatch

A replay-time error: the artifact's recorded `paxman_version`, `planner_version`, or capability versions are not supported by the running Paxman. Raises `VersionMismatchError`.

**Related:** [Replay](#replay)

---

## W

### W3C PROV (informational reference)

A W3C standard for provenance. Paxman's evidence model is inspired by W3C PROV but is **not** a strict implementation; it is a JSON-friendly subset suitable for `ExecutionArtifact`. See [W3C PROV](https://www.w3.org/TR/prov-overview/) for the upstream specification.

---

## Conventions

- **Subsystem names** are `lowercase` (`contract`, `planner`, `capabilities`, `executor`, `reconciler`, `artifact`, `api`).
- **Status enums** are `SCREAMING_SNAKE_CASE` (`SUCCESS`, `PARTIAL_SUCCESS`, `UNRESOLVED`, `INVALID_CONTRACT`, `EXECUTION_FAILED`).
- **Confidence bands** are `SCREAMING_SNAKE_CASE` (`CERTAIN`, `HIGH`, `MEDIUM`, `LOW`, `UNTRUSTED`).
- **Truth layers** are capitalized in prose: "Contract Truth", "Candidate Truth", "Resolved Truth".
- **Field types** are `SCREAMING_SNAKE_CASE` (`STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`).
- **Capability IDs** are `snake_case` (`text_extraction`, `regex_extraction`, `lookup`, `inference`, `validation`).
- **Error codes** are `SCREAMING_SNAKE_CASE` strings attached to every exception.
- **Python classes** are `PascalCase`. **Functions and modules** are `snake_case`. **Constants** are `SCREAMING_SNAKE_CASE`.

---

## See also

- [ARCHITECTURE.md](./architecture.md) — Subsystem responsibilities, error model, versioning.
- [PACKAGE_STRUCTURE.md](./package-structure.md) — Module layout, public/private split.
- [docs/adr/](../adr/) — Architecture Decision Records that justify many of these terms.

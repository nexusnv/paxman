# Capabilities

> **Status:** V1
> **Audience:** Paxman users inspecting capability output; Paxman
> contributors adding or extending capabilities.
> **Related docs:** [GLOSSARY.md §Capability](../reference/glossary.md),
> [EXTENDING.md §2](../reference/extending.md) (adding a new capability),
> [EXTENDING.md §3](../reference/extending.md) (adding a new inference
> provider), [ARCHITECTURE.md §5 Capabilities Subsystem](../reference/architecture.md),
> [docs/specs/capability-cost-model.md](../specs/capability-cost-model.md)
> (cost model, scoring, weights).

A **capability** is Paxman's unit of work — an atomic, reusable
operation that takes an input, runs an algorithm, and returns one or
more **candidates** for a field. Capabilities do not assign
confidence (per [ADR-0005](../adr/0005-confidence-ownership.md));
they are tool calls; the Reconciler grades their output.

This document explains the V1 capability surface, the capability
metadata model, the cost model, and the boundary rules that
capabilities must respect.

---

## 1. The five V1 capabilities

Paxman V1 ships **exactly five capabilities** (per [PRD.md §5.1](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/Decision-History/PRD.md)):

| Capability | Tier | Input | Output | V1 use case |
|---|---|---|---|---|
| `text_extraction` | `LOCAL_DETERMINISTIC` | raw input | `bytes` (text payload) | Pull text out of `text/plain` / `text/html` (PDF/OCR is V2). |
| `regex_extraction` | `LOCAL_DETERMINISTIC` | `CapabilityContext` (text + span) | `list[Candidate]` (one per regex match) | Pull structured values with named groups. |
| `lookup` | `STRUCTURED_LOOKUP` | `CapabilityContext` (key) | `list[Candidate]` (one per lookup hit) | V1: in-memory dict backend. Vector search is V2. |
| `inference` | `LOCAL_INFERENCE` / `REMOTE_INFERENCE` | `CapabilityContext` (text + prompt) | `list[Candidate]` (one per completion) | Delegate to a model provider. V1 ships a stub; real providers are V2. |
| `validation` | `LOCAL_DETERMINISTIC` | `CapabilityContext` (text + candidate) | `list[Candidate]` (filtered + diagnostic) | Reject candidates that fail type/range/regex/enum/ISO-4217 checks. |

Two capabilities are **non-deterministic** in general: `inference`
(when backed by a non-deterministic model). The other three are
deterministic. Non-determinism is recorded in the artifact's evidence
and does **not** break replay (replay rehydrates the recorded truth;
it does not re-invoke capabilities).

---

## 2. The Capability SPI

Every capability implements the `Capability` Protocol (see
[paxman.protocols](../reference/extending.md) and
[EXTENDING.md §2](../reference/extending.md)):

```python
class Capability(Protocol):
    @property
    def spec(self) -> CapabilitySpec: ...
    def invoke(self, ctx: CapabilityContext) -> CapabilityResult: ...
```

`CapabilityResult` carries:

- `candidates: tuple[Candidate, ...]` — zero or more candidates.
- `evidence: tuple[EvidenceRef, ...]` — pointers to where the
  value came from (capability id, version, source span). Note: the
  field is named `evidence` (not `evidence_refs`) on
  `CapabilityResult`; only `Candidate.evidence_refs` uses the
  `_refs` suffix.
- `diagnostics: tuple[Diagnostic, ...]` — informational notes (e.g.
  "regex did not match", "validation rejected value X").

`CapabilityResult` has **no `confidence` field** (per ADR-0005). The
Reconciler assigns confidence later. The static test
`tests/unit/test_capability_result.py` enforces this.

A `Candidate` carries:

- `value` — the resolved value (typed per the field's `FieldType`).
- `evidence_refs: tuple[EvidenceRef, ...]` — additional evidence
  specific to this candidate.
- `diagnostics: tuple[Diagnostic, ...]` — per-candidate notes
  (rare; most diagnostics are result-level).

---

## 3. CapabilitySpec (metadata)

Every capability carries a `CapabilitySpec` that the planner reads to
score the capability and pick the cheapest sufficient chain for a
field:

| Field | Type | Purpose |
|---|---|---|
| `id` | `str` | Stable identifier (e.g. `"regex_extraction"`, `"inference"`). |
| `version` | `str` | Capability version (semver); the planner picks the **highest** registered version. |
| `input_type` | `FieldType` | The field type this capability **consumes**. |
| `output_type` | `FieldType` | The field type this capability **produces**. |
| `tier` | `CapabilityTier` | One of `LOCAL_DETERMINISTIC`, `STRUCTURED_LOOKUP`, `LOCAL_INFERENCE`, `REMOTE_INFERENCE`. |
| `cost_estimate` | `CostHint` | Upper-bound cost (USD, ms, invocations, tokens). |
| `deterministic` | `bool` | `True` for `LOCAL_DETERMINISTIC` and `STRUCTURED_LOOKUP`. `False` for any capability backed by a non-deterministic provider. |
| `required_providers` | `tuple[str, ...]` | Provider names required to invoke this capability. Empty for non-inference. |

The Planner uses `(tier, cost_estimate, deterministic)` to **score**
the capability and decide whether to put it in the `FieldPlan`
chain. The full scoring formula is in
[docs/specs/capability-cost-model.md §4](../specs/capability-cost-model.md).
The short version:

```
score = tier_weight + (usd * USD_WEIGHT) + (ms * MS_WEIGHT)
```

with `tier_weight` (10000), `USD_WEIGHT` (1000000), `MS_WEIGHT` (1).
The V1 weights are calibrated to make **USD dominate ms dominate
tier**.

---

## 4. The CapabilityContext (input)

`invoke()` receives a `CapabilityContext` with:

- `raw_input: bytes` — the raw input bytes (UTF-8 encoded, with
  replacement applied at the API layer). The capability may
  decode and parse this as needed (e.g. `text_extraction` for
  `text/html`).
- `field_path: str` — the dotted path of the field being resolved
  (e.g. `"line_items[0].price"`).
- `field_type_name: str` — the field's `FieldType` value name
  (e.g. `"STRING"`). Stored as a string to keep the context
  JSON-serializable.
- `config: Mapping[str, object]` — capability-specific
  configuration (e.g. the regex pattern for `regex_extraction`).
  Defaults to `{}`.
- `input_profile_type: str` — the `InputProfile.input_type` for
  the raw input (e.g. `"text"`, `"html"`). Defaults to `"text"`.
- `span: tuple[int, int] | None` — optional `(start, end)`
  byte-offset pair into the raw input. Defaults to `None`.

Capabilities **do not** receive the raw `CanonicalContract` or the
`Budget`/`Policy`. The planner, executor, and reconciler share
those; capabilities see only what they need (their per-step
input).

---

## 5. The cost model

Paxman budgets and tracks cost in three dimensions:

| Dimension | Unit | Bounded by |
|---|---|---|
| `usd` | USD (Decimal) | `Budget.max_total_cost_usd` |
| `ms` | Latency in milliseconds | `Budget.max_total_latency_ms` |
| `invocations` | Per-capability call count | `Budget.max_capability_invocations` |
| `remote_inference_calls` | `inference` calls (any provider) | `Budget.max_remote_inference_calls` |
| `tokens` | Optional token estimate | Reported only (no budget cap in V1). |

`BudgetTracker` (in the executor) tracks running totals and
**short-circuits** when a budget is exhausted. The pre-loop check
runs before each field; the per-step check runs before each
capability invocation within a field's chain.

The full cost model — including the V1 weights, the scoring formula,
and the budget-exhaustion semantics — is in
[docs/specs/capability-cost-model.md](../specs/capability-cost-model.md).

---

## 6. The capability registry

Capabilities are registered globally via
`paxman.register_capability(...)`. The registry is a
**version-aware** dict: `{(id, version): Capability}`. The planner
uses `registry.get_latest(id)` to find the highest registered version
of a capability.

Registering a capability with an already-registered `(id, version)`
raises `InvalidContractError` (the registry uses the same error
type for all registration conflicts, including adapters).

The V1 capabilities are **auto-registered on import** by
`paxman.capabilities.v1.__init__` (which `paxman.__init__` triggers
on first use).

---

## 7. Determinism and non-determinism

A capability's `spec.deterministic` flag tells the planner and
reconciler whether to expect deterministic output. Four of the V1
capabilities are deterministic by design:

- `text_extraction` — same input → same text.
- `regex_extraction` — same input + pattern → same matches.
- `lookup` — same input → same lookup hit (or miss).
- `validation` — same input → same accept/reject.

`inference` is **non-deterministic by default** because it is backed
by a model. Paxman V1 ships a `StubInferenceProvider` that is also
non-deterministic in its default configuration (the
`CyclingStubInferenceProvider` rotates through 3 fixed vendor names
to simulate the non-determinism of a real provider; the default
`StubInferenceProvider` always returns the same text).

Non-determinism does **not** break replay. The artifact records
the actual completion text in the evidence; replay rehydrates the
artifact and does not re-invoke the capability. See
[REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md) §5.3.

---

## 8. Boundary rules

Capabilities **must not**:

- **Assign confidence.** Per [ADR-0005](../adr/0005-confidence-ownership.md),
  only the Reconciler assigns confidence. `CapabilityResult` has no
  `confidence` field; the static test in
  `tests/unit/test_capability_result.py` enforces this.
- **Read the `CanonicalContract`.** Capabilities receive a
  `CapabilityContext`; the contract is the planner's concern.
- **Read the raw input directly.** The Executor passes a
  pre-processed `CapabilityContext` (text + span + config).
- **Mutate executor state.** Capabilities are stateless across
  invocations.
- **Cache results in a way that breaks determinism** (for
  `deterministic=True` capabilities).

Capabilities **must**:

- **Return a `CapabilityResult`.** Always — even on failure.
- **Be stateless.** No mutable state across invocations.
- **Capture external effects in evidence.** If you call an external
  service, record the call (provider, model, prompt hash, completion
  hash) in evidence.
- **Fail loudly on unrecoverable errors** via `CapabilityError`.
- **Declare a `CapabilitySpec`.** The Planner reads it.

---

## 9. The V1 surface (in code)

| Module | Class | Tier |
|---|---|---|
| `paxman.capabilities.v1.text_extraction` | `TextExtractionCapability` | `LOCAL_DETERMINISTIC` |
| `paxman.capabilities.v1.regex_extraction` | `RegexExtractionCapability` | `LOCAL_DETERMINISTIC` |
| `paxman.capabilities.v1.lookup` | `LookupCapability` | `STRUCTURED_LOOKUP` |
| `paxman.capabilities.v1.inference` | `InferenceCapability` | `LOCAL_INFERENCE` / `REMOTE_INFERENCE` |
| `paxman.capabilities.v1.validation` | `ValidationCapability` | `LOCAL_DETERMINISTIC` |

The V1 inference capability is **pluggable**: it takes an
`InferenceProvider` (the `InferenceProvider` SPI) at registration
time. The default provider is `StubInferenceProvider`; the
`CyclingStubInferenceProvider` is a test-only stub for non-determinism
exercises. Real providers (OpenAI, Anthropic, Cohere) are V2; see
[EXTENDING.md §3](../reference/extending.md).

---

## 10. When to add a new capability

Add a new capability when:

- You have a domain-specific extraction or validation step that
  doesn't fit the V1 surface.
- You want to ship a new algorithm (e.g. a custom regex library, a
  custom lookup table, a custom model wrapper).
- You are shipping a new field type that the V1 capabilities cannot
  handle.

Do **not** add a new capability when:

- The operation can be expressed as a V1 capability (e.g. don't add
  `phone_extraction` — use `regex_extraction` with a phone regex).
- The operation is a "policy" rather than an operation (use
  `ResolutionPolicy` or `ContractPolicy` instead).
- The operation needs to read the contract or the raw input directly
  (it must go through `CapabilityContext`).

Capabilities require an **ADR** (see
[docs/adr/index.md](../adr/index.md)) because they add a new
public SPI. Custom extensions published as separate PyPI packages
(`paxman-<your-capability>`) do not require an ADR for the Paxman
core repo, but the extension should document its SPI compliance.

---

## 11. See also

- [EXTENDING.md §2](../reference/extending.md) — full step-by-step for
  adding a capability.
- [EXTENDING.md §3](../reference/extending.md) — full step-by-step for
  adding an inference provider.
- [docs/specs/capability-cost-model.md](../specs/capability-cost-model.md) —
  the full cost model and scoring formula.
- [ARCHITECTURE.md §5 Capabilities Subsystem](../reference/architecture.md) —
  internal architecture of the capabilities subsystem.
- [ADR-0005](../adr/0005-confidence-ownership.md) — confidence
  ownership (why capabilities don't assign confidence).
- [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md) —
  determinism in the presence of non-deterministic capabilities.

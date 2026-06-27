# Reconciliation

> **Status:** V1
> **Audience:** Paxman users inspecting the resolved output; Paxman
> contributors extending the Reconciler.
> **Related docs:** [GLOSSARY.md §Reconciler, §ConfidenceBand](../reference/glossary.md),
> [ARCHITECTURE.md §7 Reconciler Subsystem](../reference/architecture.md),
> [ADR-0003](../adr/0003-separate-reconciler.md) (separate
> Reconciler), [ADR-0005](../adr/0005-confidence-ownership.md)
> (confidence ownership), [docs/specs/dict-dsl-spec.md](../specs/dict-dsl-spec.md)
> (MONEY in the contract).

The **Reconciler** is Paxman's truth-resolution subsystem. It is the
**sole confidence authority** (per
[ADR-0005](../adr/0005-confidence-ownership.md)) and the only place
where the artifact's final values are decided. It takes the
Executor's per-field `CandidateResult` records and the
`CanonicalContract`, and produces one `ResolvedResult` per field.

This document explains the three truth layers, the merge and
conflict logic, confidence assignment, MONEY reconciliation, and
the boundary rules that the Reconciler must respect.

---

## 1. The Reconciler's role

The Reconciler is the **only** subsystem that:

- Assigns `confidence` (a float in `[0.0, 1.0]`) and
  `confidence_band` (one of the 5 V1 bands) to a value.
- Decides the final `value` for a field (the value that goes into
  the artifact's `normalized_data`).
- Merges multiple candidates from the same or different capabilities.
- Detects conflicts and produces a `CONFLICT` diagnostic.
- Handles MONEY currency matching and FX.

The Reconciler is **declarative**: it does not invoke capabilities,
does not read the raw input, and does not see external schemas. It
takes `CandidateResult[]` and a `CanonicalContract` and produces
`ResolvedResult[]`. This boundary is enforced by `import-linter`.

```text
Executor (per field)
       │
       │  CandidateResult[]
       │  (one per required field; zero or more candidates each)
       ▼
Reconciler
       │
       │  ResolvedResult[]
       │  (one per required field; confidence + band + value)
       ▼
Artifact
```

---

## 2. The three truth layers

Per `PACKAGE_STRUCTURE.md` §7.4, Paxman has **three explicit truth
layers**:

| Layer | Source | Authoritative for |
|---|---|---|
| **Contract Truth** | The `CanonicalContract` | Field paths, types, required flags, constraints. |
| **Candidate Truth** | The `CandidateResult[]` from the Executor | What capabilities discovered (value + evidence). |
| **Resolved Truth** | The `ResolvedResult[]` from the Reconciler | What goes into the artifact (value + confidence). |

The three layers are **explicit** so callers can introspect the
delta between "what the contract asked for" and "what the
Reconciler accepted." The artifact carries the Resolved Truth; the
Contract Truth is in the contract you supplied; the Candidate Truth
is in the executor's evidence (you can access it through the
artifact's `evidence` list).

```python
@enum.unique
class TruthLayer(enum.Enum):
    CONTRACT = "CONTRACT"
    CANDIDATE = "CANDIDATE"
    RESOLVED = "RESOLVED"
```

---

## 3. The ResolvedResult

The Reconciler's output for one field is a `ResolvedResult`:

| Field | Type | Purpose |
|---|---|---|
| `field_id` | `str` | The `CanonicalField.id`. |
| `field_path` | `str` | The dotted path (e.g. `"line_items[0].price"`). |
| `field_type_name` | `str` | The `FieldType` value name (e.g. `"STRING"`). |
| `value` | typed value or `None` | The final value, or `None` if unresolved. |
| `confidence` | `float` | In `[0.0, 1.0]`. The Reconciler is the sole authority (per ADR-0005). |
| `confidence_band` | `ConfidenceBand` | The band derived from `confidence`. |
| `truth_layer` | `TruthLayer` | Always `RESOLVED` for a successful resolution. |
| `evidence_refs` | `tuple[EvidenceRef, ...]` | Evidence supporting the resolution. |
| `status` | `str` | `"RESOLVED"` or `"UNRESOLVED"`. |
| `diagnostics` | `tuple[Diagnostic, ...]` | Per-field diagnostics (CONFLICT, MISMATCH, ...). |

`ResolvedResult` is **frozen, slotted, hashable** (attrs `frozen=True,
slots=True`). The Reconciler constructs the only valid instances.

---

## 4. The merge and conflict logic

The Reconciler walks the `CandidateResult[]` field-by-field, in
declaration order. For each field, it:

1. **Collects** the candidates from the result.
2. **Validates** each candidate against the field's constraints
   (type, range, regex, enum, ISO-4217). Invalid candidates are
   dropped with a `VALIDATION_FAILED` diagnostic.
3. **Detects conflicts** — candidates that disagree on the value.
   A conflict is recorded as a `CONFLICT` diagnostic on the field.
4. **Picks the best candidate.** The tie-breaking order is:
   - **Validation passed** (the candidate passed all field-level
     constraints). Invalid candidates are dropped before merging.
   - **Highest confidence** (the float assigned by `assign_confidence`).
   - **Most evidence refs** (more evidence is better).
   - **Deterministic capability** (deterministic beats non-deterministic
     for tie-breaking).
5. **Assigns confidence** via `assign_confidence(evidence)`.
6. **Emits diagnostics** for everything that happened (CONFLICT,
   MISMATCH, VALIDATION_FAILED, etc.).

If **no candidate** passes validation, the field is `UNRESOLVED` with
`confidence=0.0` and `confidence_band=UNTRUSTED`.

### 4.1 What "conflict" means

A **conflict** is two or more candidates that disagree on the value
and both passed validation. For example:

- Candidate A: `supplier_name = "ACME Corp"` (from `regex_extraction`).
- Candidate B: `supplier_name = "Globex Industries"` (from
  `inference` with non-deterministic model).

If both pass the `validation` step (e.g. both are non-empty strings),
the Reconciler detects a conflict, records a `CONFLICT` diagnostic,
and picks the best candidate by the tie-breaking order. The
rejected candidate is still in the `evidence_refs` (so the caller
can see what was considered) but the artifact's `normalized_data`
has the chosen value.

### 4.2 What "mismatch" means

A **mismatch** is a candidate that disagrees with another on a
**structured** field (e.g. MONEY with different currencies, OBJECT
with different shapes, ARRAY with different lengths). The
Reconciler's MONEY logic in
[§6](#6-money-and-currency-policy) handles currency mismatches with
`CurrencyPolicy`.

---

## 5. Confidence assignment

The Reconciler is the **sole** confidence authority (per
[ADR-0005](../adr/0005-confidence-ownership.md)). Confidence
assignment is a **deterministic, documented rubric** — the same
evidence always produces the same float.

### 5.1 The rubric (V1, fixed)

The `assign_confidence` rubric (in
`paxman.reconciler.confidence`) is:

```
base = 0.50
+ 0.10 per agreeing candidate (cap at 3 → +0.30)
+ 0.05 per evidence ref (cap at 5 → +0.25)
+ 0.10 if validation passed
- 0.15 if conflict was detected
+ 0.05 per unique capability source (cap at 3 → +0.15)
clamp to [0.0, 1.0]
```

This produces a globally comparable score: every Reconciler call
with the same evidence produces the same float. The same input
produces the same output (the determinism invariant for replay).

### 5.2 The band mapping (V1, fixed)

| Band | Range |
|---|---|
| `CERTAIN` | `[0.95, 1.00]` |
| `HIGH` | `[0.80, 0.95)` |
| `MEDIUM` | `[0.60, 0.80)` |
| `LOW` | `[0.30, 0.60)` |
| `UNTRUSTED` | `[0.00, 0.30)` |

The bands are half-open: the lower bound is inclusive, the upper
bound is exclusive (except `CERTAIN`, which includes 1.0).

### 5.3 Property tests

Property tests in `tests/property/test_reconciler_property_*.py`
verify:

- **Determinism** — same evidence → same float, byte-equal.
- **Monotonicity** — strictly better evidence never lowers confidence.
- **Boundedness** — the float is always in `[0.0, 1.0]`.

---

## 6. MONEY and currency policy

`MONEY` is a first-class field type (per
[ADR-0004](../adr/0004-money-first-class-type.md)). The Reconciler
handles MONEY specially because the **currency** is part of the
value — `Decimal("100.00")` and `Decimal("100.00")` are not equal if
one is USD and the other is EUR.

The Reconciler's MONEY logic (in `paxman.reconciler.money`) handles:

- **Same-currency candidates** — agree on amount and currency →
  merged as a single value.
- **Cross-currency candidates** — `CurrencyPolicy` decides:
  - `STRICT_MATCH` (default) — reject cross-currency candidates
    with a `CURRENCY_MISMATCH` diagnostic.
  - `ALLOW_FX` — accept if the contract has an `fx_rate` field. The
    Reconciler converts the secondary candidate's amount to the
    primary currency using the `fx_rate`.
  - `REJECT_WITHOUT_RATE` — accept cross-currency only if both
    candidates carry an `fx_rate`; otherwise reject.

`Decimal` precision is preserved end-to-end (per
[ADR-0010](../adr/0010-budget-money-decimal.md)). The cost pipeline
(`Budget`, `CostHint`, `BudgetTracker`, `ExecutionState`) is
`Decimal`-based.

### 6.1 Currency policy precedence

The effective `CurrencyPolicy` is `derive_effective_policy(...).currency_policy`:

- Call-site `Policy.currency_policy` is the default.
- `ContractPolicy.currency_policy` (carried by the contract) takes
  precedence for fields in the contract.

The Reconciler applies the effective policy per field.

---

## 7. UNRESOLVED fields

A field is `UNRESOLVED` if:

- The Executor's `CandidateResult` had no candidates (the chain was
  exhausted without producing a value).
- Every candidate was rejected by validation.
- A cross-currency MONEY conflict was detected and the policy is
  `STRICT_MATCH`.

An `UNRESOLVED` `ResolvedResult` has:

- `value = None`
- `confidence = 0.0`
- `confidence_band = UNTRUSTED`
- `status = "UNRESOLVED"`
- A descriptive diagnostic (`CHAIN_EXHAUSTED`, `VALIDATION_FAILED`,
  `CURRENCY_MISMATCH`, etc.).

The artifact's overall `Status` is then computed by
`_compute_overall_status(...)` in `paxman.api.normalize`:

- All fields resolved → `Status.SUCCESS`.
- Any required field unresolved → `Status.UNRESOLVED`
  (or `Status.PARTIAL_SUCCESS` if
  `Policy.unresolved_acceptable=True`).
- Only optional fields unresolved → `Status.PARTIAL_SUCCESS`.

---

## 8. Boundary rules

The Reconciler **must not**:

- **Invoke capabilities.** Capability invocation is the Executor's
  job.
- **Read the raw input.** The Reconciler sees only
  `CandidateResult[]` and the `CanonicalContract`.
- **See external schemas.** The Reconciler only operates on the
  CanonicalContract; it never sees a Pydantic model or a JSON
  Schema document.
- **Mutate candidates.** The `CandidateResult` is the Executor's
  immutable output; the Reconciler reads from it but never mutates
  it.

The Reconciler **must**:

- **Be deterministic.** Same inputs → same `ResolvedResult[]`
  byte-for-byte.
- **Assign confidence.** It is the **only** subsystem that may do so.
- **Preserve evidence.** Every evidence ref that supports a
  resolution is preserved in the `ResolvedResult.evidence_refs`.
- **Emit diagnostics.** Validation failures, conflicts, and
  cross-currency mismatches all surface as structured diagnostics
  on the `ResolvedResult` (and the artifact).

---

## 9. The V1 surface (in code)

| Module | Class / function | Purpose |
|---|---|---|
| `paxman.reconciler.reconciler` | `reconcile(...)` | The top-level `reconcile` function. |
| `paxman.reconciler.truth` | `ResolvedResult`, `TruthLayer` | The output data model. |
| `paxman.reconciler.confidence` | `assign_confidence(...)`, `float_to_band(...)` | The V1 rubric + band mapping. |
| `paxman.reconciler.merge` | (internal) | The merge logic. |
| `paxman.reconciler.conflict` | (internal) | The conflict detection. |
| `paxman.reconciler.evidence_compare` | (internal) | Evidence comparison for tie-breaking. |
| `paxman.reconciler.unresolved` | (internal) | The `UNRESOLVED` case. |
| `paxman.reconciler.validation` | (internal) | Field-level validation (delegated from the Reconciler). |
| `paxman.reconciler.money` | (internal) | MONEY reconciliation + currency policy. |

The Reconciler module is a **private** subsystem — it is not a
public API; do not import from it directly in user code. The public
surface for reconciliation is the artifact's `field_results` and
`unresolved_fields` lists.

---

## 10. Common pitfalls

| Pitfall | Why it bites | Fix |
|---|---|---|
| Two capabilities produce different values and you expected the Reconciler to pick the first | The Reconciler picks the **best** by the tie-breaking order, not the first. | Inspect the `evidence_refs` to see what was considered. |
| MONEY field with no `currency_policy` in the contract | The default is `STRICT_MATCH`; cross-currency candidates are rejected. | Set `CurrencyPolicy.ALLOW_FX` and add an `fx_rate` field. |
| Custom logic that "always picks the inference result" | The Reconciler does not know which capability produced each candidate. | Use `evidence_refs` and the per-candidate metadata to disambiguate. |
| Expecting the Reconciler to re-validate candidates | The Reconciler delegates to `paxman.reconciler.validation`; it does not re-invoke the `validation` capability. | The Executor's `validation` step is the source of truth. |
| Confidence for an `UNRESOLVED` field | The Reconciler sets `confidence=0.0`, `band=UNTRUSTED`. | Treat `UNRESOLVED` as "no value" — check `status` first. |

---

## 11. See also

- [ARCHITECTURE.md §7 Reconciler Subsystem](../reference/architecture.md) —
  internal architecture of the Reconciler subsystem.
- [ADR-0003](../adr/0003-separate-reconciler.md) — separate
  Reconciler rationale.
- [ADR-0004](../adr/0004-money-first-class-type.md) — MONEY as a
  first-class type.
- [ADR-0005](../adr/0005-confidence-ownership.md) — confidence
  ownership.
- [ADR-0010](../adr/0010-budget-money-decimal.md) — the
  cost-pipeline Decimal switch.
- [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md) —
  Reconciler determinism in the replay path.

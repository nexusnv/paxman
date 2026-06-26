# Planning

> **Status:** V1
> **Audience:** Paxman users inspecting the plan; Paxman contributors
> extending the planner.
> **Related docs:** [GLOSSARY.md §Plan, §Planner](../../GLOSSARY.md),
> [ARCHITECTURE.md §4 Planner Subsystem](../../ARCHITECTURE.md),
> [ADR-0001](../adr/0001-field-centric-planning.md) (field-centric
> planning), [ADR-0002](../adr/0002-rule-based-planner-v1.md)
> (rule-based V1 planner), [docs/specs/capability-cost-model.md](../specs/capability-cost-model.md)
> (scoring formula).

The **planner** is the deterministic, rule-based brain of Paxman. It
synthesizes a per-field `ExecutionPlan` from a `CanonicalContract`,
an `InputProfile`, a `Budget`, a `Policy`, and the capability
registry. The planner is a **pure function** (per [ADR-0002](../adr/0002-rule-based-planner-v1.md)):
the same inputs always produce the same plan, byte-for-byte.

This document explains the planner's role, the heuristic chain, the
scoring formula, the budget and policy gates, and the determinism
guarantees.

---

## 1. What planning is — and isn't

The planner **only synthesizes** the plan. It does not run
capabilities, does not consume budget, does not produce evidence,
and does not assign confidence. The Executor's job is to **run** the
plan; the Reconciler's job is to **grade** the candidates.

```text
                  ┌────────────────┐
                  │  Canonical     │
                  │  Contract      │
                  └───────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  InputProfile  │ ← make_profile(input_data)
                  └───────┬────────┘
                          │
                          │  + Budget, Policy, Registry
                          ▼
                  ┌────────────────┐
                  │   Planner      │  ← pure function
                  │   (rule-based) │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ ExecutionPlan  │ ← one FieldPlan per required field
                  └────────────────┘
```

The plan is a **declarative** artifact: a list of capability chains
with their step configs and `target_confidence` thresholds. The
Executor interprets the plan; the planner never sees the Executor.

---

## 2. Field-centric planning

Per [ADR-0001](../adr/0001-field-centric-planning.md), Paxman is
**field-centric**, not document-centric. Each required field gets
its own `FieldPlan`:

```python
@dataclass(frozen=True)
class FieldPlan:
    field_path: str
    steps: tuple[FieldPlanStep, ...]   # capability chain
    target_confidence: float            # read from field's confidence_threshold
    notes: tuple[str, ...]              # planner-side notes (V1: empty)
```

A `FieldPlanStep` carries:

- `capability_id` — e.g. `"regex_extraction"`.
- `capability_version` — the **resolved** version (e.g. `"1.0"`).
- `tier` — `LOCAL_DETERMINISTIC` / `STRUCTURED_LOOKUP` / `LOCAL_INFERENCE` / `REMOTE_INFERENCE`.
- `config` — frozen per-step config (e.g. the regex pattern for
  `regex_extraction`). Wrapped in `types.MappingProxyType` to
  prevent post-construction mutation.

The Executor walks the `FieldPlan` in step order, invokes the
capability at each step, and collects candidates. If a step
**already satisfies** the field (e.g. `regex_extraction` returns a
non-empty `Candidate` with a passing `validation`), the Executor
**stops** — there is no reason to keep spending budget.

The `ExecutionPlan` carries:

- `contract_id` — the canonical contract's id.
- `input_content_hash` — the SHA-256 of the input (matches the
  `InputProfile.content_hash`).
- `fields` — `tuple[FieldPlan, ...]` in **declaration order**
  (not dict-iteration order).
- `diagnostics` — planner-emitted notes (e.g. budget exclusions).

Declaration order matters: the Executor walks fields in plan order,
not in dict-iteration order. The plan encodes order explicitly.

---

## 3. The 7-step heuristic chain

For each required field, the planner walks this chain in order (per
[ARCHITECTURE.md §4.2](../../ARCHITECTURE.md) and the Oracle M7
clarification):

1. **Explicit evidence.** A planner rule on the `InputProfile` that
   decides whether the input already contains the field's value
   (e.g. a `KEY: VALUE` line in a `text/plain` payload for a `STRING`
   field tagged `header`).
2. **Local deterministic extraction.** `regex_extraction`,
   `validation` (and any other `LOCAL_DETERMINISTIC`-tier
   capabilities registered for this `output_type`).
3. **Structured lookup.** `lookup` (V1: in-memory dict backend).
4. **Derived computation.** Formula over resolved fields (V2).
5. **Local inference.** `inference` with a local model.
6. **Remote inference.** `inference` with a remote provider.
7. **`UNRESOLVED`.** Terminal; no chain. The field's
   `CandidateResult.status` is `UNRESOLVED`.

Each step picks **the highest-scoring capability** for the field's
`output_type` from the available registry, subject to:

- **Policy gates.** `Policy.allow_remote_inference=False` drops step 6.
  `Policy.allow_local_inference=False` drops step 5.
- **Budget gates.** A `Budget.max_total_cost_usd < Decimal("0.001")`
  drops both 5 and 6 (inference's minimum USD cost is `0.001`).
- **Capability availability.** A step with no registered capability
  for the field's `output_type` is dropped.
- **Step config.** For `regex_extraction`, the planner must have a
  pattern (read from the field's `constraints` or a
  `regex` semantic tag). If no pattern is available, the step is
  skipped.

The chain stops at the first step that produces a non-empty
candidate set. If all steps are exhausted without producing a
candidate, the plan emits an `UNRESOLVED` `CandidateResult` for the
field.

---

## 4. Scoring

The planner scores every `(capability, field)` pair and picks the
best within each tier. The full scoring formula is in
[docs/specs/capability-cost-model.md §4](../specs/capability-cost-model.md).
The V1 weights are:

| Weight | Value | Purpose |
|---|---|---|
| `TIER_WEIGHT` | `10000` | Tier penalty: lower tier → lower score. |
| `USD_WEIGHT` | `1000000` | USD cost dominates. |
| `MS_WEIGHT` | `1` | Latency is the tie-breaker. |

```
score = tier_weight(tier) + (usd * 1_000_000) + (ms * 1)
```

`lower is better`. The V1 calibration makes USD dominate ms dominate
tier — a slightly slower deterministic capability beats a much
cheaper non-deterministic one.

The score is computed once per `(capability, field)` pair during
planning; the planner stores the result in the `FieldPlanStep` for
replay (replay rehydrates the plan, but does not re-plan; the
recorded score is part of the evidence).

---

## 5. Budget and policy gates

The planner respects `Budget` and `Policy` constraints when
synthesizing the plan. The gates are applied **at plan time** (not
at execute time):

| Gate | Effect on the plan |
|---|---|
| `Policy.allow_remote_inference=False` | Step 6 (remote inference) is dropped from every `FieldPlan`. |
| `Policy.allow_local_inference=False` | Step 5 (local inference) is dropped from every `FieldPlan`. |
| `Budget.max_total_cost_usd < Decimal("0.001")` | Steps 5 and 6 are dropped (inference's minimum USD cost is `0.001`). |
| `Policy.unresolved_acceptable=True` | The Executor's post-loop status is `PARTIAL_SUCCESS` instead of `UNRESOLVED` if any required field is unresolved. |
| `Policy.currency_policy=ALLOW_FX` (no `fx_rate` field) | The Reconciler rejects cross-currency MONEY candidates. |

The Executor also applies **dynamic** budget gates during
execution (the `BudgetTracker` short-circuits when the running
total exceeds `max_total_cost_usd`). The planner cannot predict
this; it only encodes the **expected** plan based on the call-site
constraints.

---

## 6. Effective policy

The planner and reconciler compute an **effective policy** =
`derive_effective_policy(call_site_policy, contract_policy)`:

- `call_site_policy` — the `Policy` passed to `paxman.normalize()`.
- `contract_policy` — the `ContractPolicy` carried by the canonical
  contract (per-contract overrides).

The contract's `ContractPolicy` takes precedence over the call-site
`Policy` for fields in the contract. The combined
`EffectivePolicy` is passed to `build_field_plan(...)` and to the
Reconciler.

This means a contract can declare a higher `confidence_floor` than
the call-site default, and the planner will respect the contract's
value for those fields. See
[paxman.planner.policies](../../EXTENDING.md) for the full logic.

---

## 7. Determinism

The planner is a **pure function** (per
[ADR-0002](../adr/0002-rule-based-planner-v1.md)). It:

- Does not read the clock.
- Does not read random state.
- Does not perform I/O.
- Does not invoke capabilities.

The only source of non-determinism in the planner is the capability
registry's iteration order. Mitigations:

- The registry sorts capabilities by `(score, id)` before iteration
  (per [docs/specs/capability-cost-model.md §7 EC5](../specs/capability-cost-model.md)).
- `PYTHONHASHSEED=0` is set in CI (per Sprint 3 risk register).

Property tests in `tests/property/test_planner_determinism.py`
verify byte-equal plans for 100 random
`(contract, input, policy)` tuples.

---

## 8. Key types

| Type | Module | Purpose |
|---|---|---|
| `InputProfile` | `paxman.planner.input_profile` | Lightweight metadata about the raw input. |
| `FieldPlan` | `paxman.planner.field_plan` | Per-field plan (capability chain + target confidence). |
| `FieldPlanStep` | `paxman.planner.field_plan` | A single capability invocation. |
| `ExecutionPlan` | `paxman.planner.field_plan` | The planner's full output (one `FieldPlan` per required field). |
| `PlanDiagnostic` | `paxman.planner.field_plan` | A planner-emitted note (e.g. budget exclusion). |
| `EffectivePolicy` | `paxman.planner.policies` | The combined call-site + contract policy for one run. |

The full public surface is re-exported from
`paxman.planner.__init__`. The Planner module is a **private**
subsystem — it is not a public API; do not import from it directly
in user code.

---

## 9. Inspection and debugging

The plan is serializable via the stable JSON encoder. To inspect a
plan:

```python
from paxman import planner, profile
import json

plan = planner.plan(canonical_contract, profile(input_data), budget, policy, registry)
print(json.dumps(plan.to_dict(), indent=2))
```

For unit tests, use `paxman.testing.plans()` (a Hypothesis strategy
that generates random `ExecutionPlan` instances with stable
`replay_hash`).

---

## 10. Common pitfalls

| Pitfall | Why it bites | Fix |
|---|---|---|
| Registering a capability with a non-canonical `version` (e.g. `"v1"`) | The registry's tie-breaker falls back to insertion order. | Use a real semver (`"1.0"`, `"1.0.1"`). |
| Setting `Policy.allow_remote_inference=True` with `Budget.max_total_cost_usd = 0` | The plan is empty (every step is budget-excluded). | Either set a positive budget or disable remote inference. |
| Calling `planner.plan()` with a `Policy` that has no `currency_policy` | The Reconciler defaults to `STRICT_MATCH` and rejects MONEY candidates. | Set `currency_policy` explicitly. |
| Expecting the planner to short-circuit on a `regex_extraction` hit | The planner does not invoke capabilities; the Executor does. | The Executor short-circuits per the `EarlyStop` policy. |
| Mixing `confidence_floor` per-field with the call-site `Policy.confidence_floor` | The contract-level value overrides; the call-site value is ignored. | Document the precedence in the contract's `ContractPolicy`. |

---

## 11. See also

- [ARCHITECTURE.md §4 Planner Subsystem](../../ARCHITECTURE.md) —
  internal architecture of the planner subsystem.
- [ADR-0001](../adr/0001-field-centric-planning.md) — field-centric
  planning rationale.
- [ADR-0002](../adr/0002-rule-based-planner-v1.md) — rule-based
  V1 planner rationale (no LLM in the critical path).
- [ADR-0005](../adr/0005-confidence-ownership.md) — confidence
  ownership (planner emits `target_confidence` only).
- [docs/specs/capability-cost-model.md](../specs/capability-cost-model.md) —
  `CostHint` and the scoring formula.
- [docs/specs/input-profile-spec.md](../specs/input-profile-spec.md) —
  the `InputProfile` data model.
- [Sprint 3 spec](../sprints/sprint-03-planner-and-capabilities.md) —
  the implementation plan.
- [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md) —
  planner determinism in the replay path.

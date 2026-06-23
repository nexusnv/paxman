# Planning

> **Status:** Skeleton (per Sprint 3 D3.21). This document will be
> filled in during Sprint 8 (docs & community) and is currently a
> brief overview of the planner subsystem.

## What is planning?

The **planner** is the deterministic, rule-based brain of Paxman. It
synthesizes a per-field execution plan from a canonical contract, an
input profile, a budget, a policy, and a capability registry. The
planner is a **pure function** (per `ADR-0002`) — same inputs →
same plan, byte-for-byte.

## Key types

| Type | Module | Purpose |
|---|---|---|
| `InputProfile` | `paxman.planner.input_profile` | Lightweight metadata about the raw input. |
| `FieldPlan` | `paxman.planner.field_plan` | Per-field plan (capability chain + target confidence). |
| `FieldPlanStep` | `paxman.planner.field_plan` | A single capability invocation. |
| `ExecutionPlan` | `paxman.planner.field_plan` | The planner's full output (one `FieldPlan` per required field). |
| `PlanDiagnostic` | `paxman.planner.field_plan` | A planner-emitted note (e.g., budget exclusion). |
| `EffectivePolicy` | `paxman.planner.policies` | The combined call-site + contract policy for one run. |

## The 7-step heuristic chain

Per `ARCHITECTURE.md` §4.2 and `ADR-0002`, the planner walks this
chain in order for each required field:

1. **Explicit evidence** — a planner rule on the `InputProfile` that
   decides whether the input already contains the field's value.
2. **Local deterministic extraction** — `regex_extraction`,
   `validation` (and other `LOCAL_DETERMINISTIC`-tier capabilities).
3. **Structured lookup** — `lookup` (V2 — Sprint 4).
4. **Derived computation** — formula over resolved fields (V2).
5. **Local inference** — `inference` with a local model.
6. **Remote inference** — `inference` with a remote provider.
7. **`UNRESOLVED`** — terminal; no chain.

Policy and budget gate each step:

- `Policy.allow_remote_inference=False` → step 6 is dropped.
- `Policy.allow_local_inference=False` → step 5 is dropped.
- `Budget.max_total_cost_usd < 0.001` → both 5 and 6 are dropped
  (inference's minimum USD cost is 0.001).

## Determinism

The planner is a **pure function** (per `ADR-0002`). It:

- Does not read the clock.
- Does not read random state.
- Does not perform I/O.
- Does not invoke capabilities.

The only source of non-determinism in the planner is the capability
registry's iteration order. Mitigations:

- The registry sorts capabilities by `(score, id)` before iteration
  (per `docs/specs/capability-cost-model.md` §7 EC5).
- `PYTHONHASHSEED=0` is set in CI (per Sprint 3 risk register).

Property tests in `tests/property/test_planner_determinism.py`
verify byte-equal plans for 100 random (contract, input, policy)
tuples.

## Where to look next

- [Sprint 3 spec](../sprints/sprint-03-planner-and-capabilities.md) — the implementation plan.
- [ARCHITECTURE.md §4.2](../../ARCHITECTURE.md) — the full planner subsystem design.
- [ADR-0001](../adr/0001-field-centric-planning.md) — field-centric planning.
- [ADR-0002](../adr/0002-rule-based-planner-v1.md) — rule-based planner rationale.
- [ADR-0005](../adr/0005-confidence-ownership.md) — confidence ownership (planner emits `target_confidence`; Reconciler assigns confidence).
- [Capability cost model](../specs/capability-cost-model.md) — `CostHint` and the scoring formula.
- [Input profile spec](../specs/input-profile-spec.md) — the `InputProfile` data model.

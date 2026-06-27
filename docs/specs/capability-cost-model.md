# Capability Cost Model

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Related docs:** [ARCHITECTURE.md §4.3](../reference/architecture.md#43-capabilities--atomic-operations), [ARCHITECTURE.md §7](../reference/architecture.md#7-configuration-model), [EXTENDING.md §2](../reference/extending.md#2-adding-a-new-capability), [ADR-0002](../adr/0002-rule-based-planner-v1.md), [ADR-0005](../adr/0005-confidence-ownership.md), [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md)

This document specifies the `CostHint` type, the V1 baseline cost values for all five capabilities, the scoring rubric the planner uses to rank capabilities, and the interaction between cost estimates and budget enforcement.

---

## 1. Overview

Every V1 capability exposes a `CostHint` as part of its `CapabilitySpec` (see [ARCHITECTURE.md §4.3](../reference/architecture.md#43-capabilities--atomic-operations)). The `CostHint` is a three-tuple of approximate token count, wall-clock latency in milliseconds, and USD cost for a single invocation.

The planner uses `CostHint` for two purposes:

1. **Heuristic ordering** — when multiple capabilities can satisfy a field, the planner ranks them by ascending cost, following the heuristic chain in [ARCHITECTURE.md §4.2](../reference/architecture.md#42-planner--field-centric-plan-synthesis): explicit evidence, local deterministic, structured lookup, derived computation, local inference, remote inference, `UNRESOLVED`.
2. **Budget enforcement** — the planner estimates total cost by summing `CostHint.usd` over the planned capability chain and compares against `Budget.max_total_cost_usd` ([ARCHITECTURE.md §7.1](../reference/architecture.md#71-budget-hard-limits)).

**Critical: the values documented here are heuristics, not measurements.** They are round numbers chosen for planner scoring fidelity. They do not reflect actual runtime cost, which depends on input size, provider pricing, and network conditions. The cost model is intentionally coarse-grained; V1 does not perform per-call cost measurement. See the risk register note in [CHANGES_LOG.md §3.1](https://github.com/nexusnv/paxman/wiki/Internal-Development/Decision-History/CHANGES-LOG#31-sprint-0-design-closure--recommended-decisions).

---

## 2. The `CostHint` Type

### 2.1 Definition

```python
from attrs import frozen


@frozen
class CostHint:
    """Approximate cost estimate for a single capability invocation.

    Values are heuristics for planner scoring, not runtime measurements.
    All fields are non-negative.
    """

    tokens: int   # approximate token count; 0 for non-LLM capabilities
    ms: int       # approximate wall-clock latency in milliseconds
    usd: Decimal  # approximate USD cost (MONEY is Decimal per ADR-0004 / ADR-0010); Decimal("0") for free capabilities
```

### 2.2 Field semantics

| Field | Unit | Range | Zero means | Non-zero means |
|---|---|---|---|---|
| `tokens` | token count (prompt + completion) | `>= 0` | Capability does not invoke an LLM | Capability invokes an LLM; value is the approximate total tokens |
| `ms` | milliseconds (wall-clock) | `>= 0` | (discouraged; see EC3) | Approximate latency for one invocation |
| `usd` | US dollars | `>= 0` (Decimal) | Capability is free (local, no billable API) | Capability has a per-invocation cost |

### 2.3 Validation rules

The following invariants are enforced at capability registration time (per [EXTENDING.md §2.1](../reference/extending.md#21-when-to-add-a-new-capability)):

- `tokens >= 0` — negative token counts are invalid.
- `ms >= 0` — negative latency is invalid.
- `usd >= 0` (Decimal) — negative cost is invalid.

Violation of any rule raises `InvalidCapabilitySpec` with `error_code="INVALID_COST_HINT"` and a `context` dict containing the offending field and value.

---

## 3. V1 Capability Cost Table

The following table defines the baseline `CostHint` values for the five V1 capabilities. These values were established in [CHANGES_LOG.md §3.1](https://github.com/nexusnv/paxman/wiki/Internal-Development/Decision-History/CHANGES-LOG#31-sprint-0-design-closure--recommended-decisions).

| Capability | `tokens` | `ms` | `usd` | `deterministic` | Notes |
|---|---|---|---|---|---|
| `text_extraction` | 0 | 5 | 0.0 | No | Provider-dependent. Local text decode is fast and free. Remote OCR providers may be slower and billable (V2). |
| `regex_extraction` | 0 | 1 | 0.0 | Yes | Pure-Python `re` module. Deterministic. Microsecond-scale actual latency; 1 ms is a conservative floor. |
| `lookup` | 0 | 1 | 0.0 | Yes | In-process table lookup against a deterministic backend. Vector backends are V2 and would add `(tokens=0, ms=10, usd=0.0)`. |
| `inference` | 500 | 1500 | 0.001 | No | V1 stub provider. Values represent a typical small LLM call: ~1k-token prompt, ~1.5 s p50 latency, ~$0.001 per invocation. |
| `validation` | 0 | 1 | 0.0 | Yes | Pure-Python constraint check. Deterministic. Microsecond-scale actual latency; 1 ms is a conservative floor. |

### 3.1 Rationale for individual values

**`text_extraction` (0, 5, 0.0):** V1 handles `text/plain` and `text/html` only (no OCR). Local decode is cheap. The 5 ms accounts for HTML parsing overhead. Remote OCR providers (V2) will carry non-zero `tokens` and `usd`.

**`regex_extraction` (0, 1, 0.0):** Pure-Python `re.match` / `re.search` on pre-extracted text. No I/O, no network, no model. The 1 ms floor prevents the planner from treating it as instantaneous, which would produce misleading budget estimates.

**`lookup` (0, 1, 0.0):** In-process dictionary or table lookup. The deterministic backend has no I/O. Vector-based retrieval (V2) would add latency for embedding computation and similarity search.

**`inference` (500, 1500, 0.001):** The V1 stub provider simulates a small LLM call. 500 tokens is the approximate output; the prompt is counted separately by the provider. 1500 ms reflects a typical p50 for a small model. $0.001 is an order-of-magnitude estimate for a 1k-token call at V2-era pricing.

**`validation` (0, 1, 0.0):** Pure-Python constraint evaluation (e.g., range check, regex match, enum membership). No I/O, no network, no model.

---

## 4. Scoring Rubric

The planner ranks capabilities by **ascending cost** within each tier of the heuristic chain. The scoring formula combines tier membership, USD cost, and latency into a single sortable score.

### 4.1 Heuristic tiers

Per [ARCHITECTURE.md §4.2](../reference/architecture.md#42-planner--field-centric-plan-synthesis), the planner assigns each capability to a tier:

| Tier rank | Tier name | Example capabilities |
|---|---|---|
| 0 | Explicit evidence | (input already contains the value) |
| 1 | Local deterministic | `regex_extraction`, `validation` |
| 2 | Structured lookup | `lookup` |
| 3 | Derived computation | (formula over resolved fields) |
| 4 | Local inference | `inference` (local model) |
| 5 | Remote inference | `inference` (remote provider) |
| 6 | Unresolved | (terminal; no capability selected) |

### 4.2 Scoring formula

```text
score(capability) = (
    tier_rank * TIER_WEIGHT
    + capability.cost_estimate.usd * USD_WEIGHT
    + capability.cost_estimate.ms * MS_WEIGHT
)
```

### 4.3 V1 weights

| Weight | Value | Rationale |
|---|---|---|
| `TIER_WEIGHT` | `10000` | Tier dominates. A capability in tier N always scores lower than any capability in tier N+1, regardless of cost. |
| `USD_WEIGHT` | `1000000` | Within the same tier, USD cost is the primary differentiator. A $1 capability ranks 1,000,000 points above a free one. |
| `MS_WEIGHT` | `1` | Latency is the tiebreaker within the same tier and USD cost. |

### 4.4 Example scores

| Capability | Tier | `tier_rank * 10000` | `usd * 1000000` | `ms * 1` | **Total score** |
|---|---|---|---|---|---|
| `regex_extraction` | Local deterministic | 10,000 | 0 | 1 | **10,001** |
| `validation` | Local deterministic | 10,000 | 0 | 1 | **10,001** |
| `lookup` | Structured lookup | 20,000 | 0 | 1 | **20,001** |
| `text_extraction` | Local deterministic | 10,000 | 0 | 5 | **10,005** |
| `inference` | Remote inference | 50,000 | 1,000 | 1,500 | **51,500** |

In this example, `regex_extraction` and `validation` tie at 10,001. The tie-break rule is defined in [§7 Edge Cases, EC5](#ec5-two-capabilities-with-identical-costhint).

### 4.5 Determinism of the scoring formula

The scoring formula is **input-independent**. It depends only on:

- The capability's `CostHint` (a static property of the `CapabilitySpec`).
- The capability's tier assignment (determined by the planner's heuristic chain, which is a pure function of the canonical contract and input profile).

Given the same canonical contract, input profile, budget, policy, and capability registry, the planner always produces the same score for every capability. This is required by [ADR-0002](../adr/0002-rule-based-planner-v1.md).

### 4.6 Weight overrides

The V1 weights are initial defaults. The planner may override them per-contract via `ResolutionPolicy` if the caller specifies a custom scoring strategy. Custom weights must be recorded in the artifact's `diagnostics` for replay transparency.

---

## 5. Determinism Considerations

The cost model is **stable across calls**. This section documents the invariants that preserve planner determinism.

### 5.1 `CostHint` is a property of the capability, not of the call

`CostHint` is declared on the `CapabilitySpec` at registration time. It does not change between invocations. The planner reads `CostHint` from the registry, not from runtime measurements.

### 5.2 The planner may NOT use wall-clock measurements to update cost

The planner is a pure function ([ADR-0002](../adr/0002-rule-based-planner-v1.md)). It must not read the system clock or measure actual capability latency during planning. If a capability's actual cost diverges from `CostHint`, the divergence is **diagnostic** (recorded in the artifact's `statistics`) but does not affect planning.

### 5.3 Replay re-uses the same `CostHint`

During replay ([REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md)), the artifact is rehydrated without re-invoking capabilities. The `CostHint` recorded in the `ExecutionPlan` is the same value that was used during planning. Replay does not re-measure cost.

### 5.4 Non-deterministic capabilities and cost stability

A non-deterministic capability (e.g., `inference`) may produce different output on each invocation, but its `CostHint` is static. The cost model does not track output-dependent cost variation. This is a deliberate simplification for V1.

---

## 6. Budget Enforcement

### 6.1 Cost estimation

The planner estimates the total cost of a plan by summing `CostHint.usd` over every capability invocation in every `FieldPlan`:

```text
estimated_cost = sum(
    capability.cost_estimate.usd
    for field_plan in execution_plan
    for capability in field_plan.capability_chain
)
```

### 6.2 Budget check

If `estimated_cost > Budget.max_total_cost_usd`, the planner takes one of two actions:

1. **Downgrade** — replace expensive capabilities with cheaper alternatives from a lower tier (e.g., replace `inference` with `regex_extraction` if the field permits it).
2. **Raise `BudgetExceededError`** — if no cheaper alternative exists, the planner raises `BudgetExceededError` with `error_code="BUDGET_EXCEEDED"` and a `context` dict containing `{"estimated_cost": ..., "max_budget": ...}`.

### 6.3 Conservative estimation

The planner's cost estimate is **conservative**: it may over-estimate (e.g., by assuming every capability in the chain will be invoked even if early-stop prevents some). This is acceptable because:

- Over-estimation prevents budget overruns.
- Under-estimation would violate the caller's budget constraint.
- The estimate is a planning heuristic, not an accounting report.

### 6.4 Executor short-circuit

Per [ARCHITECTURE.md §7.1](../reference/architecture.md#71-budget-hard-limits), the Executor short-circuits when the budget is exceeded at runtime. The artifact is returned with status `PARTIAL_SUCCESS` and a `BudgetExceededError` diagnostic. Fields resolved before the budget was exceeded retain their values; fields not yet attempted are marked `UNRESOLVED`.

### 6.5 Interaction with `max_total_latency_ms`

The same estimation pattern applies to latency: the planner sums `CostHint.ms` over the capability chain and compares against `Budget.max_total_latency_ms`. The same downgrade-or-raise logic applies.

---

## 7. Edge Cases

### EC1: Capability with `usd > 0` but `deterministic=True`

**Scenario:** A paid deterministic API (e.g., a billable OCR service that returns deterministic results for the same input).

**V1 behavior:** Allowed. The `CostHint` and `deterministic` fields are independent. The planner scores by `CostHint` regardless of determinism. A paid deterministic capability is ranked by its USD cost within its tier.

### EC2: Capability with `tokens=0` but `usd > 0`

**Scenario:** A flat-fee API that charges per call but does not bill per token.

**V1 behavior:** Allowed. The planner ranks primarily by USD cost (`USD_WEIGHT=1000000`), so a capability with `tokens=0, usd=0.01` is ranked higher (more expensive) than one with `tokens=500, usd=0.001`. The `tokens` field is informational; it does not affect the scoring formula.

### EC3: Capability with `ms=0`

**Scenario:** A capability that claims zero latency.

**V1 behavior:** Discouraged but accepted. A real capability has non-zero latency; `ms=0` is a user-side error in the `CostHint` declaration. The planner accepts it without validation (the `ms >= 0` rule permits zero). If the capability never returns, the caller observes a timeout, not a planning error. Capability authors SHOULD declare at least `ms=1` for any non-trivial capability.

### EC4: `CostHint` with negative values

**Scenario:** A capability is registered with `tokens=-1`, `ms=-100`, or `usd=-0.01`.

**V1 behavior:** Rejected at registration time. The `CapabilitySpec` validator raises `InvalidCapabilitySpec` with `error_code="INVALID_COST_HINT"` and `context={"field": "tokens", "value": -1}`. Negative values are structurally invalid.

### EC5: Two capabilities with identical `CostHint`

**Scenario:** `regex_extraction` and `validation` both have `CostHint(tokens=0, ms=1, usd=0.0)` and are in the same tier.

**V1 behavior:** Tie-break by `capability.id` (lexicographic ascending). The planner is deterministic; given the same registry, the same input always picks the same capability. In this example, `regex_extraction` < `validation` lexicographically, so `regex_extraction` is preferred.

### EC6: Inference capability in a `Budget(max_total_cost_usd=0)` plan

**Scenario:** The caller sets a zero-cost budget, which excludes the `inference` capability (`usd=0.001`).

**V1 behavior:** The planner emits a `Diagnostic` (warning code `BUDGET_EXCLUDES_INFERENCE`, message `"Budget max_total_cost_usd=0 excludes inference capabilities; fields requiring inference will be UNRESOLVED"`) and proceeds with non-inference capabilities only. Fields that can only be satisfied by `inference` become `UNRESOLVED`. The artifact status is `PARTIAL_SUCCESS` (or `UNRESOLVED` if no field resolves).

---

## 8. Custom Capabilities (Extension)

Per [EXTENDING.md §2](../reference/extending.md#2-adding-a-new-capability), third-party capabilities register their own `CostHint` as part of their `CapabilitySpec`.

### 8.1 Source of truth

The `CapabilitySpec.cost_estimate` field is the **sole source of truth** for a capability's cost. The planner reads this value at plan time; it does not infer cost from capability behavior.

### 8.2 Recommended benchmarking practice

Third-party capability authors SHOULD provide measured values from a **100-iteration benchmark** on representative hardware. The benchmark should:

- Measure wall-clock latency (p50, p99) for `ms`.
- Count tokens (if applicable) for `tokens`.
- Compute average USD cost (if applicable) for `usd`.

Round to the nearest integer for `tokens` and `ms`; round to 6 decimal places for `usd`.

### 8.3 Unknown cost convention

If the cost is unknown at registration time, the convention is:

```python
cost_estimate=CostHint(tokens=0, ms=0, usd=0.0)
```

This makes the planner treat the capability as **free and instantaneous**. This is conservative for the caller (the capability will be preferred over paid alternatives) but may lead to budget under-estimation if the capability actually has non-zero cost. Capability authors SHOULD update the `CostHint` once measured values are available.

---

## 9. Out of Scope (V1)

The following cost-model features are explicitly deferred to V2:

| Feature | Status | Rationale |
|---|---|---|
| Per-call cost measurement | V2 | V1 uses static `CostHint`; runtime cost is recorded in `statistics` but does not affect planning. |
| Cost-aware caching | V2 | V1 does not cache capability results; replay rehydrates from the artifact. |
| Cost prediction based on input size | V2 | V1 treats all invocations of the same capability as the same cost, regardless of input size. |
| Multi-currency budgets | V2 | V1 budgets are USD only. Non-USD budgets must be converted at the call site before passing to `paxman.normalize()`. |
| Cost reports in the artifact | V2 | V1 includes `cost_estimate` (the static `CostHint`) per `FieldPlan`. Actual measured cost is recorded in `statistics` but not in per-field results. |

---

## 10. See also

- [ARCHITECTURE.md §4.3](../reference/architecture.md#43-capabilities--atomic-operations) — `CapabilitySpec` shape and V1 capability table.
- [ARCHITECTURE.md §7](../reference/architecture.md#7-configuration-model) — `Budget` and `Policy` definitions.
- [EXTENDING.md §2](../reference/extending.md#2-adding-a-new-capability) — how to register a custom capability with `CostHint`.
- [ADR-0002](../adr/0002-rule-based-planner-v1.md) — rule-based planner; determinism requirement.
- [ADR-0005](../adr/0005-confidence-ownership.md) — confidence is Reconciler-owned; capabilities never assign confidence.
- [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md) — replay protocol; `CostHint` stability across replays.

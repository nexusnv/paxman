# ADR-0001: Field-Centric Planning (not Document-Centric)

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Paxman must normalize input against a caller-supplied contract. Two architectural options for planning exist:

1. **Document-centric** — plan to "parse the entire document" or "extract everything from the input" in one pass, then reconcile against the contract.
2. **Field-centric** — plan independently for each required field; each field gets its own execution plan.

How should Paxman structure its planner?

## Decision Drivers

- **Cost optimization** — different fields have different cost/confidence profiles; an expensive inference may be needed for one field but wasteful for another.
- **Targeted inference** — only fields that need inference should pay for it.
- **Deterministic execution** — per-field plans are easier to make deterministic and replayable.
- **Selective capability invocation** — per-field plans allow using different capabilities for different fields.
- **Cost is a first-class concern** (PRD §4.6) — calls for the cheapest sufficient path per field.

## Considered Options

### Option A — Document-centric planning

Plan one pipeline that extracts everything from the input and reconciles against the contract. A single execution graph per (contract, input).

**Pros:**

- Single execution graph is easier to visualize.
- Intermediate data is shared across fields.

**Cons:**

- Cannot use cheaper deterministic methods for some fields while using inference for others.
- All-or-nothing: if one field needs an expensive capability, the whole run pays for it.
- Harder to short-circuit per field.
- Harder to test in isolation.

### Option B — Field-centric planning (chosen)

Plan one `FieldPlan` per required field. The executor walks the field plans in deterministic order.

**Pros:**

- Each field gets the cheapest sufficient path.
- Per-field early stop when a field meets its confidence threshold.
- Per-field confidence and unresolved handling.
- Easier to test in isolation.
- Aligned with the V1 heuristic chain (explicit evidence → ... → UNRESOLVED).

**Cons:**

- No shared intermediate state across fields (caller must use `ContractPolicy` to express cross-field derived computations).
- Slightly more bookkeeping (one plan per field).

### Option C — Hybrid (per-document super-plan with per-field sub-plans)

**Pros:**

- Best of both worlds in theory.

**Cons:**

- Adds a layer of complexity.
- Field plans still need to be independent for replay.
- We can achieve the same effect with field plans + a `derived` capability in V2.

## Decision Outcome

**Chosen option: B (Field-centric).** Each required field gets its own `FieldPlan`. The Executor walks them in deterministic order. This aligns with:

- PRD §4.2 ("The pipeline is synthesized, not fixed")
- PRD §7.2 ("Adaptive Plan Synthesis")
- ARCHITECTURE.md §4.2
- The V1 heuristic chain is per-field.

## Consequences

### Positive

- Cost optimization is per-field.
- Testable in isolation.
- Determinism is straightforward.
- Each field has explicit `target_confidence` and `fallback_policy`.

### Negative

- Cross-field derived computations (e.g., `total = sum(line_items[].price)`) must be expressed via a `derived` capability in V2.
- The Planner must produce a list of plans, not a single plan. This is a minor complexity.

### Neutral

- The `derived` capability and cross-field resolution is a V2 feature.

## Validation

- The Planner unit tests assert one `FieldPlan` per required field.
- The Executor unit tests assert sequential execution in plan order.
- The integration test fixtures include contracts with derived fields (deferred to V2).

## References

- PRD.md §4.2, §7.2
- ARCHITECTURE.md §4.2 (planner)
- PACKAGE_STRUCTURE.md §4 (planner module)

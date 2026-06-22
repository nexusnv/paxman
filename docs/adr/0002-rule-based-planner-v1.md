# ADR-0002: Rule-Based Planner for V1

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Paxman must synthesize a deterministic execution plan. Two architectural options for V1 exist:

1. **Rule-based planner** — a fixed heuristic chain (explicit evidence → local deterministic → ... → `UNRESOLVED`) that picks the next capability based on contract field metadata, input profile, budget, and policy.
2. **LLM-based planner** — an LLM decides which capabilities to invoke for each field.

How should the V1 planner be implemented?

## Decision Drivers

- **Determinism is required** (PRD §4.5) — given the same inputs, the planner must produce the same plan.
- **No AI in the V1 critical path** (PRD §7.6) — V1 planning must be rule-based.
- **Tiny API** (PRD §4.7) — the caller should not need to configure a model.
- **Cost is first-class** (PRD §4.6) — using an LLM to plan is expensive.
- **Replayability** (PRD §7.4) — plans must be reproducible from contract + input + budget + policy.

## Considered Options

### Option A — Rule-based planner (chosen)

A fixed heuristic chain. For each required field, the planner evaluates the chain in order and selects the first applicable capability that fits the budget and policy.

**Pros:**

- Deterministic by construction.
- Cheap (no inference cost).
- Easy to test and reason about.
- Plays well with replay.

**Cons:**

- Less flexible than an LLM-based planner.
- May miss non-obvious plans for unusual input types.
- Requires hand-tuning the heuristic chain.

### Option B — LLM-based planner

Use an LLM to generate the `FieldPlan[]` from the contract and input profile.

**Pros:**

- Flexible; can plan for unusual input types.
- Could discover novel capability combinations.

**Cons:**

- Non-deterministic by default.
- Expensive (one inference per field, at minimum).
- Adds a provider dependency to the core.
- Violates PRD §7.6 (no LLM in the V1 critical path).
- Replay is harder (plan may differ between runs).

### Option C — Hybrid: rule-based with LLM refinement

Run the rule-based planner first; if the plan is "low confidence," ask an LLM to refine it.

**Pros:**

- Best of both worlds in theory.

**Cons:**

- Doubles complexity.
- The "low confidence" threshold is itself heuristic.
- Replay is harder.

## Decision Outcome

**Chosen option: A (Rule-based).** The V1 planner is a pure function over (canonical contract, input profile, budget, policy, capability registry). The heuristic chain is documented in [ARCHITECTURE.md §4.2](./../ARCHITECTURE.md) and [PACKAGE_STRUCTURE.md §4](./../PACKAGE_STRUCTURE.md).

LLM-based planning is **postponed to V2** (see [ARCHITECTURE.md §17.2](./../ARCHITECTURE.md)).

## Consequences

### Positive

- Determinism is automatic.
- No inference cost in the planner.
- Replay is straightforward.
- Easy to add a new capability without retraining a planner.

### Negative

- The heuristic chain is hand-tuned. V2 may add learned heuristics on top.
- Unusual input/contract combinations may produce sub-optimal plans.

### Neutral

- The `Heuristic` protocol is exposed as a post-V1 extension point.

## Validation

- Property tests verify that the same inputs produce the same plan.
- The planner test suite covers every combination of input profile and contract shape.
- Determinism tests assert byte-equal `ExecutionPlan` JSON for the same inputs.

## References

- PRD.md §4.5, §7.6
- ARCHITECTURE.md §4.2, §17.1
- PACKAGE_STRUCTURE.md §4

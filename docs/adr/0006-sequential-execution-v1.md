# ADR-0006: Sequential Execution in V1

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

The Executor runs the plan produced by the Planner. The question is: should it run field plans in parallel or sequentially?

## Decision Drivers

- **Determinism** (PRD §4.5) — parallel execution introduces scheduling non-determinism.
- **Replayability** (PRD §7.4) — replay must reproduce the same artifact.
- **Simplicity** — sequential execution is easier to test and reason about.
- **V1 scope** — the V1 capability surface is small; parallel execution gains are limited.

## Considered Options

### Option A — Sequential execution (chosen)

The Executor walks `FieldPlan[]` in plan order. Each field plan is executed to completion (or to its early-stop threshold) before the next one starts.

**Pros:**

- Trivially deterministic.
- Trivially replayable.
- Easy to test.
- No scheduling, no race conditions.

**Cons:**

- Slower for large contracts with many fields.
- Does not exploit independent fields.

### Option B — Parallel field execution

The Executor runs independent field plans in parallel using a thread or process pool.

**Pros:**

- Faster for large contracts.
- Exploits multi-core CPUs.

**Cons:**

- Non-deterministic by default (scheduling order).
- Race conditions on shared state.
- Replay is harder.
- Tests are harder to write.
- Adds a thread/process pool to the core.

### Option C — Configurable: sequential by default, parallel opt-in

A `Policy.parallelism` knob that lets callers opt in to parallel execution.

**Pros:**

- Best of both worlds in theory.

**Cons:**

- Doubles the Executor code path.
- The "is this field independent?" analysis is itself complex.
- V1 doesn't need this.

## Decision Outcome

**Chosen option: A (Sequential).** The V1 Executor runs field plans in plan order, sequentially. Each field plan is run to completion (or to its early-stop threshold) before the next one starts.

**Parallelism is postponed to V2** ([ARCHITECTURE.md §17.2](../reference/architecture.md)). When V2 adds it, it will be opt-in and will only parallelize fields that the Planner has proven independent (no derived computation dependencies).

## Consequences

### Positive

- Determinism is automatic.
- Replay is straightforward.
- The Executor is small and easy to reason about.

### Negative

- V1 is slower for large contracts.
- V1 does not exploit multi-core CPUs.

### Neutral

- Async API (`async def normalize`) is V2.

## Validation

- The Executor unit tests verify that capabilities are invoked in plan order.
- The replay tests verify byte-equal artifacts across runs.
- The integration tests measure p50/p99 latency on a 20-field contract as a baseline (see [PRD §9](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/Decision-History/PRD.md) for targets).

## References

- PRD.md §4.5, §7.4
- ARCHITECTURE.md §11, §17.2
- PACKAGE_STRUCTURE.md §6

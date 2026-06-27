# ADR-0003: Separate Reconciler Subsystem

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

After the Executor collects candidate values for each field, those candidates must be merged, conflicts resolved, confidence assigned, and the final value chosen. Two architectural options exist:

1. **Reconciler as a separate subsystem** — a dedicated `paxman.reconciler` module owns truth resolution.
2. **Reconciler folded into the Executor** — the Executor emits resolved results directly.

How should truth resolution be structured in Paxman?

## Decision Drivers

- **Truth resolution is a first-class concern** (PRD §7.7) — confidence is exclusively owned by Planner and Reconciler.
- **The Reconciler is the only truth authority** (PACKAGE_STRUCTURE.md §11.5) — separation enforces this.
- **Testability** — merging, conflict detection, and confidence assignment are complex and need their own test seams.
- **MONEY arithmetic** — currency handling is a Reconciler primitive, not a capability.

## Considered Options

### Option A — Separate Reconciler subsystem (chosen)

A dedicated `paxman.reconciler` module with strict boundaries: it never executes capabilities, never reads raw input, never sees external schemas. It takes `CandidateResult[]` and produces `ResolvedResult[]`.

**Pros:**

- Clear responsibility: the Reconciler owns final truth and final confidence.
- The Executor's job is bounded (run the plan, collect evidence).
- Testable in isolation with crafted `CandidateResult[]`.
- `MONEY` arithmetic and currency policy live in one place.
- Confidence calibration is centralized.

**Cons:**

- One more subsystem to maintain.
- Candidates and evidence cross an additional boundary.

### Option B — Reconciler folded into the Executor

The Executor emits resolved results.

**Pros:**

- Fewer subsystems.
- One fewer data handoff.

**Cons:**

- The Executor's job becomes too large.
- The "Executor never assigns final confidence" rule becomes harder to enforce.
- Testing the merging logic requires the full Executor pipeline.
- The "Reconciler is the only truth authority" rule becomes a comment in code rather than a structural guarantee.

## Decision Outcome

**Chosen option: A (Separate Reconciler).** This is consistent with [ARCHITECTURE.md §4.5](../reference/architecture.md) and [PACKAGE_STRUCTURE.md §7](../reference/package-structure.md).

## Consequences

### Positive

- Strong structural guarantee: the only place that assigns final confidence is `paxman.reconciler`.
- Testable in isolation.
- `MONEY` arithmetic is centralized.
- Conflict detection is centralized.

### Negative

- One more subsystem to understand.

### Neutral

- The data shape `CandidateResult` becomes a public-ish type for the Executor → Reconciler hand-off (still internal).

## Validation

- The Reconciler test suite covers every merging strategy in isolation.
- A static check verifies that no module outside `paxman.reconciler` imports `ConfidenceBand` for **assignment** (read access is allowed via the artifact).
- Property tests verify that the Reconciler is monotonic w.r.t. evidence quality.

## References

- PRD.md §7.3, §7.7
- ARCHITECTURE.md §4.5
- PACKAGE_STRUCTURE.md §7, §11.5

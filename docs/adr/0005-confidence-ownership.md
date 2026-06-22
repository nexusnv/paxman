# ADR-0005: Confidence Ownership — Planner + Reconciler, Not Capabilities

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Confidence is a critical part of Paxman's output. The question is: which subsystem(s) may assign confidence to a candidate or resolved value?

The earlier drafts of `PACKAGE_STRUCTURE_draft.md` (now superseded by [PACKAGE_STRUCTURE.md](../PACKAGE_STRUCTURE.md)) had contradictory statements:
- §3 guardrails: "Planner owns confidence assignment (not capabilities)."
- §4 guardrails: "Confidence is exclusively owned by the Planner and Reconciler."
- §6 guardrails: "Reconciler is the only layer that assigns final confidence and final truth."

This ADR resolves the contradiction.

## Decision Drivers

- **No confidence inflation** — capabilities should not assign confidence because each capability would calibrate differently, leading to incomparable scores.
- **Globally comparable confidence** — confidence must be a single scale that the Reconciler can compare across capabilities.
- **Determinism** — confidence assignment must be deterministic given the same inputs.
- **Replayability** — the same `ConfidenceBand` for the same field across replays.

## Considered Options

### Option A — Reconciler is the only confidence assigner (chosen)

The Reconciler is the **sole** subsystem that assigns a confidence score (float) and band to a candidate or resolved value. The Planner may emit a `target_confidence` per field (read from the field's `confidence_threshold`) but does not score candidates. Capabilities return candidates without confidence.

**Pros:**

- Strongest structural guarantee: one place assigns confidence.
- Globally comparable: all confidence comes from the same calibration.
- Easy to test: confidence logic is centralized.
- Replay is straightforward: the same candidates produce the same confidence.

**Cons:**

- The Reconciler has more responsibility.
- Capabilities can't provide a "self-assessed confidence" hint.

### Option B — Capabilities return confidence; Reconciler picks the best

Each capability returns a confidence score; the Reconciler picks the highest-confidence candidate.

**Pros:**

- Capabilities "know" how good their output is.

**Cons:**

- Confidence inflation: each capability calibrates differently, leading to incomparable scores.
- Hard to test deterministically across capabilities.
- Replay is harder: capabilities may be non-deterministic.

### Option C — Planner assigns an initial confidence; Reconciler finalizes

The Planner emits a `target_confidence` and the Reconciler re-scores candidates based on evidence quality.

**Pros:**

- Combines the "field has a target" with "evidence is graded" intuitions.

**Cons:**

- Two places assign confidence, complicating the rule.
- The "initial" vs "final" distinction is not load-bearing.

## Decision Outcome

**Chosen option: A (Reconciler is the only confidence assigner).** The Reconciler is the **sole** subsystem that assigns a confidence float and band. The Planner may emit a `target_confidence` per field, but this is a threshold, not a score. Capabilities return candidates without confidence.

**Concretely:**

- `CapabilityResult` has no `confidence` field. Candidates are returned with `value`, `evidence_refs`, and `diagnostics` only.
- `FieldPlan` has a `target_confidence` field (read from the field's `confidence_threshold`) that the Executor uses for early stop.
- The Reconciler assigns the final `confidence` (float) and `confidence_band` on `FieldResult`.

This ADR supersedes the contradictory language in the earlier `PACKAGE_STRUCTURE_draft.md` §3, §4, §6. The new [PACKAGE_STRUCTURE.md](../PACKAGE_STRUCTURE.md) §7.4, §7.5, §11.3, §11.5 are consistent with this decision.

## Consequences

### Positive

- Strongest structural guarantee: one place assigns confidence.
- Globally comparable confidence.
- Confidence calibration is centralized.
- Replay is straightforward.

### Negative

- Capabilities can't "self-assess" their output.
- The Reconciler must reason about evidence quality, not just trust capability output.

### Neutral

- The Planner still emits a `target_confidence` per field (read-only from the contract).

## Validation

- Static check: no module outside `paxman.reconciler` imports the `ConfidenceBand` constructor for assignment.
- `CapabilityResult` schema has no `confidence` field. Capabilities that try to set confidence fail type-check.
- Property test: same candidates + same contract + same evidence → same confidence (deterministic).
- Property test: monotonic — strictly better evidence never lowers confidence.

## References

- PRD.md §7.3, §7.7
- ARCHITECTURE.md §4.2, §4.5, §8
- PACKAGE_STRUCTURE.md §4, §5, §7, §11.3, §11.5

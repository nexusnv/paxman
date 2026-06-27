# ADR Index

> **Status:** Active.
> **Related docs:** [ARCHITECTURE.md](../reference/architecture.md), [PACKAGE_STRUCTURE.md](../reference/package-structure.md), [GLOSSARY.md](../reference/glossary.md)

Paxman uses [MADR](https://adr.github.io/madr/) (Markdown Architectural Decision Records) for capturing significant architectural decisions. Each ADR is short, decision-focused, and immutable once accepted.

## Format

Each ADR follows MADR 4.0 with the following sections:

- **Title** — the decision as an H1 heading.
- **Status** — Proposed / Accepted / Deprecated / Superseded.
- **Date** — when the decision was made.
- **Context and Problem Statement** — why is this decision needed?
- **Decision Drivers** — factors influencing the decision.
- **Considered Options** — the options evaluated.
- **Decision Outcome** — the chosen option and rationale.
- **Consequences** — positive, negative, neutral.
- **Validation** — how the decision will be verified.
- **References** — links to relevant docs.

## Index

| # | Title | Status | Date | Summary |
|---|---|---|---|---|
| [0001](./0001-field-centric-planning.md) | Field-Centric Planning | Accepted | 2026-06-22 | Each required field gets its own `FieldPlan`. |
| [0002](./0002-rule-based-planner-v1.md) | Rule-Based Planner for V1 | Accepted | 2026-06-22 | V1 planner is a pure function; no LLM in the critical path. |
| [0003](./0003-separate-reconciler.md) | Separate Reconciler Subsystem | Accepted | 2026-06-22 | Reconciler is its own subsystem, owning final truth and final confidence. |
| [0004](./0004-money-first-class-type.md) | MONEY as a First-Class Type | Accepted | 2026-06-22 | `MONEY` is a structured type with currency + precision; not a tagged `DECIMAL`. |
| [0005](./0005-confidence-ownership.md) | Confidence Ownership | Accepted | 2026-06-22 | Reconciler is the **sole** confidence assigner. Planner emits `target_confidence` only. Capabilities return no confidence. |
| [0006](./0006-sequential-execution-v1.md) | Sequential Execution in V1 | Accepted | 2026-06-22 | V1 Executor runs field plans sequentially. Parallelism is V2. |
| [0007](./0007-contract-adapter-set-v1.md) | V1 Contract Adapter Set | Accepted | 2026-06-22 | Required: Pydantic, JSON Schema, Dict DSL. Optional: OpenAPI. Not in V1: ERP, agent tool, wrapper. |
| [0008](./0008-license-decision.md) | License Decision | Accepted | 2026-06-22 | MIT chosen for V1. Apache-2.0 is the documented alternative if patent concerns emerge. The full trade-off analysis is preserved on the [project wiki](https://github.com/nexusnv/paxman/wiki/Internal-Development/License-decision—full-analysis). |
| [0009](./0009-dict-dsl-v1.md) | Dict DSL V1 Surface | Accepted | 2026-06-22 | Pure-Python `dict` DSL with 5 concepts (FieldSpec, Constraint, Tag, Policy, Contract). Rejected custom grammar and JSON Schema subset. |

## Conventions

- **Numbering** — four-digit, monotonically increasing. `0001`, `0002`, ...
- **Filename** — `<number>-<kebab-case-title>.md`.
- **Status transitions** — once Accepted, an ADR is never modified. If a decision is reversed or refined, a new ADR is written and the old one is marked Superseded with a link.
- **No "light" ADRs** — significant decisions get an ADR. Minor tweaks do not.

## When to write an ADR

Write an ADR when:

- Adding a new public API surface.
- Adding a new public SPI.
- Changing a system boundary rule.
- Adding a new dependency to the core.
- Changing the artifact format.
- Changing the replay model.
- Deprecating or removing public API.

Do not write an ADR for:

- Bug fixes.
- Refactors that don't change behavior or boundaries.
- Documentation updates.
- Internal naming.

## ADR template

```markdown
# ADR-NNNN: <Title>

> **Status:** Proposed | Accepted | Deprecated | Superseded
> **Date:** YYYY-MM-DD
> **Deciders:** <list>
> **Supersedes:** <ADR-NNNN or none>
> **Superseded by:** <ADR-NNNN or none>

## Context and Problem Statement

<2-3 paragraphs>

## Decision Drivers

- <driver 1>
- <driver 2>

## Considered Options

### Option A — <name>

<description>

**Pros:** ...

**Cons:** ...

### Option B — <name>

<description>

**Pros:** ...

**Cons:** ...

## Decision Outcome

<Chosen option and rationale.>

## Consequences

### Positive

- ...

### Negative

- ...

### Neutral

- ...

## Validation

- <how the decision will be verified>

## References

- <links>
```

# Initiatives

> **Status:** Active.
> **Audience:** Paxman contributors and maintainers.
> **Related docs:** [Contributing](../contributing/index.md), [Engineering Standards](../contributing/engineering-standards.md)

Initiatives are **cross-cutting engineering quality efforts** that span
multiple PRs and are tracked as GitHub issues with a synthesized position.
Unlike ADRs (which are immutable architectural decisions) or sprint docs
(which are time-boxed planning artifacts), Initiatives describe an ongoing
engineering investment with a stated success criterion.

## Active Initiatives

| Initiative | Issue | Status | Success Criterion |
|---|---|---|---|
| [Pyright Strict Mode](./pyright-strict-mode.md) | [#26](https://github.com/nexusnv/paxman/issues/26) | PR-1 in progress | B (future capability enablement) |

## When to create an Initiative

Create an Initiative doc when:

- An engineering quality effort spans **multiple PRs** and needs a shared success criterion.
- The effort is **not a product feature** (it doesn't ship user-facing functionality).
- The effort is **not an ADR** (it's a process/tooling investment, not an architectural decision).
- The effort needs a **tracking document** that outlives any single PR.

## Initiative lifecycle

1. **Proposal:** Open a GitHub issue describing the engineering quality effort.
2. **Synthesis:** The issue discussion converges on a synthesized position (success criterion, implementation plan, constraints).
3. **Initiative doc:** Create an Initiative doc in this directory capturing the synthesized position.
4. **Execution:** Implement as a sequence of PRs, each referencing the Initiative doc.
5. **Completion:** Update the Initiative doc status to "Completed" when the success criterion is met.

# Design specifications

> **Audience:** Paxman contributors and developers who need to understand
> the *internal* implementation contracts that govern how the library
> works. These specs are the developer-reference companion to the
> [ADRs](../adr/index.md): the ADRs say *why* a decision was made; the
> specs say *exactly what* the decision means in code.

These are **implementation specifications** — they describe how Paxman's
internals are shaped, in enough detail that the corresponding code can be
written or audited against them. They are *not* user-facing documentation
(see the [Concepts](../concepts/contracts.md) for that).

## Specs in this directory

| Spec | Scope |
|---|---|
| [Dict DSL](./dict-dsl-spec.md) | The grammar and semantics of Paxman's built-in Dict DSL for declaring contracts without Pydantic. Implementation reference for `paxman.contract.adapters.dict_dsl`. |
| [Input profile](./input-profile-spec.md) | The shape and invariants of an `InputProfile` (V1's 8 input types, validity rules, evaluator semantics). Implementation reference for `paxman.planner.input_profile`. |
| [Capability cost model](./capability-cost-model.md) | The cost/scoring model used by the planner to rank `FieldPlan` candidates (V1 weight table, scoring formula, EC invariants). Implementation reference for `paxman.planner.scoring` and `paxman.planner.policies`. |

## How specs relate to ADRs

Each spec supports one or more ADRs. The mapping:

| ADR | Specs |
|---|---|
| [ADR-0009 (Dict DSL for V1)](../adr/0009-dict-dsl-v1.md) | [Dict DSL spec](./dict-dsl-spec.md) |
| [ADR-0001 (Field-Centric Planning)](../adr/0001-field-centric-planning.md) | [Input profile spec](./input-profile-spec.md) |
| [ADR-0002 (Rule-Based Planner for V1)](../adr/0002-rule-based-planner-v1.md) | [Input profile spec](./input-profile-spec.md), [Capability cost model](./capability-cost-model.md) |

Specs may be edited freely; ADRs are immutable once Accepted. To supersede
a spec, write a new ADR that changes the policy and update the spec to
match.

## When to add a new spec

Add a spec when:

- An ADR defines a *policy* and the policy needs a *concrete* implementation contract that contributors must follow.
- A subsystem has a non-obvious internal data model (e.g., `InputProfile`'s 8 input types) that benefits from a single source of truth.
- A change to the spec would be **breaking** to contributors reading the code or extending the library (vs. additive, which goes in a how-to).

Do **not** add a spec for:

- User-facing behavior. That belongs in the [Concepts](../concepts/contracts.md).
- Anything that fits in a docstring. Specs are for cross-module contracts that don't fit in one file.
- Anything that changes every release. Specs are stable; volatile docs go in [How-to guides](../howto/add_adapter.md).

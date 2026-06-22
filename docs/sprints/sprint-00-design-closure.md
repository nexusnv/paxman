# Sprint 0 — Design Closure

> **Duration:** 1 week
> **Goal:** Close the **3 design gaps** that block Sprint 1, plus resolve the **license decision** (currently TBD).
> **Status:** This sprint produces **specification documents only** — no code, no CI yet.

## Why this sprint exists

Three concrete gaps were identified by auditing the existing documentation (see `CHANGES_LOG.md` and the audit summary at the end of this document). These gaps block the implementation of the first sprint:

1. **Dict DSL syntax is unspecified** — referenced ~20 times in the docs as the "escape hatch" and "test source of truth" (per `EXTENDING.md` §1 and `PRD.md` §5.1), but the concrete syntax of the DSL is not defined anywhere.
2. **`InputProfile` has no module spec** — `planner/input_profile.py` is listed in `PACKAGE_STRUCTURE.md` §4.2 with the description "lightweight input classifier (no capability invocation)" but the data model and the construction logic are not described.
3. **`CostHint` values are undefined** — `CapabilitySpec.cost_estimate` per `ARCHITECTURE.md` §4.3 takes a `CostHint(tokens, ms, usd)` but the docs do not specify the cost model that the planner's `scoring.py` will use to compare capabilities.

Plus:

4. **License decision is TBD** — `README.md` §License says "MIT (or Apache-2.0 — final TBD by the team)." This blocks `LICENSE` file creation in Sprint 1.

## Scope (in)

- 4 specification documents created in `docs/sprints/v0-specs/`:
  - `dict-dsl-spec.md`
  - `input-profile-spec.md`
  - `capability-cost-model.md`
  - `license-decision.md`
- An ADR (`docs/adr/0008-license-decision.md`) recording the license choice.
- A new ADR template if Dict DSL or `InputProfile` are deemed ADR-worthy by the team (the project owner decides).

## Scope (out)

- **No source code.** No `src/paxman/` yet. No `pyproject.toml` yet. This sprint is design-closure only.
- **No GitHub Actions setup yet.** Sprint 1 introduces CI.
- **No fixture contracts yet.** Sprint 2 introduces Pydantic + Dict DSL fixture contracts.

## Deliverables

| ID | Deliverable | Location | Format |
|---|---|---|---|
| D0.1 | Dict DSL syntax specification | `docs/sprints/v0-specs/dict-dsl-spec.md` | Markdown; BNF-like grammar + 3 worked examples + 5 edge cases |
| D0.2 | Input Profile module spec | `docs/sprints/v0-specs/input-profile-spec.md` | Markdown; `InputProfile` data model + `make_profile(input) -> InputProfile` algorithm |
| D0.3 | Capability cost model | `docs/sprints/v0-specs/capability-cost-model.md` | Markdown; `CostHint` values for all 5 V1 capabilities + scoring rubric |
| D0.4 | License decision document | `docs/sprints/v0-specs/license-decision.md` | Markdown; MIT vs Apache-2.0 trade-off analysis + recommendation |
| D0.5 | License ADR | `docs/adr/0008-license-decision.md` | MADR 4.0 template |
| D0.6 | (Optional) ADR for Dict DSL if deemed architectural | `docs/adr/0009-dict-dsl-v1.md` | MADR 4.0 (optional; project owner decides) |

## Prerequisites (must be ready before Sprint 0 starts)

| Type | Item | Notes |
|---|---|---|
| **People** | 1 senior engineer (or 1 lead + 1 reviewer) | 1 week, full-time |
| **Decisions** | Project owner available for license decision | Cannot be deferred |
| **Docs** | `GLOSSARY.md`, `EXTENDING.md`, `PACKAGE_STRUCTURE.md` | Already in repo |
| **Tools** | None (this sprint produces only Markdown) | Markdown editor |

## Tooling / applications / libraries

None required. This sprint is documentation only. No Python environment, no CI, no editor beyond Markdown.

## API keys / secrets

None.

## Exit criteria

1. `docs/sprints/v0-specs/dict-dsl-spec.md` exists, has BNF grammar + ≥3 worked examples, and is reviewed by ≥1 other engineer.
2. `docs/sprints/v0-specs/input-profile-spec.md` exists, has the `InputProfile` data model and `make_profile()` algorithm, and is reviewed.
3. `docs/sprints/v0-specs/capability-cost-model.md` exists with explicit `CostHint(tokens, ms, usd)` for all 5 V1 capabilities (`text_extraction`, `regex_extraction`, `lookup`, `inference`, `validation`), reviewed.
4. `docs/adr/0008-license-decision.md` is in the MADR format and has Status: Accepted.
5. `docs/sprints/v0-specs/license-decision.md` records the rationale.
6. (Optional, if project owner decides) Dict DSL ADR exists.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| License decision takes longer than 1 week | Low | High | Pre-brief the project owner on the trade-off; have a recommended default in the decision document. |
| Dict DSL spec becomes too complex (second-system effect) | Medium | High | Keep V1 Dict DSL ≤ 5 concepts; reject `references` and `inheritance` (YAGNI). |
| `InputProfile` spec becomes a research project | Medium | Medium | Cap at 5 fields. Defer content classification (e.g., "is this a financial document?") to V2. |
| `CostHint` values become arbitrary | High | Medium | Cost model is for planner **scoring**, not accounting. Round numbers are fine. Document that the values are heuristics, not measurements. |
| Spec reviews cause scope creep | Medium | Medium | Reviewers can suggest, not require. Spec is owned by the author; changes go through an ADR. |

## Audit summary (the 3 gaps)

The full audit is recorded in `CHANGES_LOG.md` §"Documentation gaps identified". Briefly:

1. **Dict DSL syntax** — `EXTENDING.md` §1.3 example uses a generic `to_canonical_field()` placeholder, not real Dict DSL syntax. The Dict DSL is the **only** internal escape hatch and the test source of truth; Sprint 2 cannot write fixture contracts without it.
2. **Input Profile** — `PACKAGE_STRUCTURE.md` §4.2 lists `planner/input_profile.py` with one-line description; no data model. The planner depends on it.
3. **`CostHint` values** — `ARCHITECTURE.md` §4.3 defines the type but no values. The planner's heuristic ordering needs to compare `regex_extraction` (fast, free) vs `inference` (slow, expensive) — without numbers, the planner cannot rank them.

## See also

- `CHANGES_LOG.md` — full record of documentation changes from this planning exercise.
- `../docs/adr/README.md` — MADR 4.0 template for new ADRs.
- `../EXTENDING.md` §1 — adapter SPI, which Dict DSL implements.
- `../ARCHITECTURE.md` §4.3 — `CapabilitySpec` with `CostHint`.
- `../PACKAGE_STRUCTURE.md` §4.2 — `planner/input_profile.py` mention.

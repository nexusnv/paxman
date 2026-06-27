# docs/adr/

## OVERVIEW
9 Architecture Decision Records (MADR 4.0) + index. The **architectural source of truth** for V1. All Accepted, all dated 2026-06-22. ADRs are immutable once Accepted — to reverse a decision, write a new ADR and mark the old one Superseded.

## INDEX (V1 PILLARS)

| # | Title | Status | Decision |
|---|---|---|---|
| 0001 | Field-Centric Planning | Accepted | Each required field gets its own `FieldPlan`. Executor walks plans in deterministic order. Rejected document-centric and hybrid approaches. |
| 0002 | Rule-Based Planner for V1 | Accepted | V1 Planner is a **pure function** (no LLM in critical path). Fixed heuristic chain: explicit evidence → local deterministic → … → UNRESOLVED. LLM planning deferred to V2. |
| 0003 | Separate Reconciler Subsystem | Accepted | Reconciler = own `paxman.reconciler` module. **Never executes capabilities, never reads raw input, never sees external schemas.** Takes `CandidateResult[]` → `ResolvedResult[]`. |
| 0004 | MONEY as First-Class Type | Accepted | `MONEY` = Decimal amount + ISO-4217 currency + optional precision. One of 9 V1 field types. `reconciler/money.py` for currency matching, `CurrencyPolicy` (STRICT_MATCH / ALLOW_FX / REJECT_WITHOUT_RATE), Decimal arithmetic. |
| 0005 | Confidence Ownership | Accepted | **Reconciler is the sole confidence assigner.** Planner emits `target_confidence` (read-only threshold from contract) but never scores. **`CapabilityResult` has no `confidence` field.** Rejected "capabilities self-assess" and "planner assigns initial." |
| 0006 | Sequential Execution in V1 | Accepted | V1 Executor runs field plans **sequentially in plan order**. Rejected parallel (non-deterministic, races). Parallelism is V2, opt-in for Planner-proven independent fields. Async API is V2. |
| 0007 | V1 Contract Adapter Set | Accepted | **Required:** Pydantic, JSON Schema, Dict DSL. **Optional (best-effort):** OpenAPI. **Not in V1:** ERP, agent tool, wrapper. Dict DSL = internal escape hatch + test source of truth. |
| 0008 | License Decision | Accepted | MIT chosen for V1. Apache-2.0 is the documented alternative if patent concerns emerge. See `docs/specs/license-decision.md` for the full trade-off analysis. |
| 0009 | Dict DSL V1 Surface | Accepted | Pure-Python `dict` DSL with 5 concepts (FieldSpec, Constraint, Tag, Policy, Contract). Rejected custom grammar and JSON Schema subset. See `docs/specs/dict-dsl-spec.md` for the BNF grammar, examples, and error model. |

## WHERE TO LOOK

| Question | Read |
|---|---|
| "Why is the Planner a pure function?" | `0002-rule-based-planner-v1.md` |
| "What subsystems can import from what?" | Cross-reference `0003-separate-reconciler.md` + `PACKAGE_STRUCTURE.md §2` |
| "Why is MONEY not a tagged DECIMAL?" | `0004-money-first-class-type.md` |
| "Who assigns confidence?" | `0005-confidence-ownership.md` — Reconciler only |
| "Why is V1 sequential, not parallel?" | `0006-sequential-execution-v1.md` |
| "Which contract adapters are required vs optional?" | `0007-contract-adapter-set-v1.md` |
| "Why MIT and not Apache-2.0?" | `0008-license-decision.md` + `docs/specs/license-decision.md` |
| "What is the Dict DSL syntax?" | `0009-dict-dsl-v1.md` + `docs/specs/dict-dsl-spec.md` |
| "When do I write a new ADR?" | `README.md` "When to write an ADR" |

## CONVENTIONS

- **Numbering:** four-digit, monotonically increasing (`0001`, `0002`, …)
- **Filename:** `<number>-<kebab-case-title>.md`
- **Format:** MADR 4.0 (Context, Drivers, Options, Outcome, Consequences, Validation, References)
- **No "light" ADRs** — significant decisions get an ADR; minor tweaks do not.
- **Once Accepted, never modified.** Status transitions only to Deprecated or Superseded with link.

## ANTI-PATTERNS

- **NEVER modify an Accepted ADR** in place. Write a new ADR and mark the old one Superseded.
- **NEVER write an ADR for:** bug fixes, behavior-preserving refactors, doc updates, internal renaming.
- **DO NOT skip the "Considered Options" section** — rejected options are part of the record.

## NOTES

- ADRs are the **architectural source of truth**. When code and ADR conflict, the ADR wins; fix the code.
- All 9 ADRs are Accepted as of `main`. None are Deprecated or Superseded.
- Significant public API / SPI / boundary changes require a new ADR before implementation (per `docs/adr/index.md` "When to write an ADR").

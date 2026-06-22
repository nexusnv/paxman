# ADR-0009: Dict DSL V1 Surface

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Per ADR-0007, the Dict DSL is one of three required V1 contract adapters and serves as Paxman's **internal escape hatch and test source of truth**. The DSL is referenced in ~20 places across the documentation (PRD.md §5.2, EXTENDING.md §1, PACKAGE_STRUCTURE.md §3.2) but its concrete surface was not specified. EXTENDING.md §1.3 uses a placeholder `to_canonical_field()`. Sprint 0 closes this gap by defining the exact concepts, format, and constraints of the V1 Dict DSL.

The full specification — including BNF grammar, worked examples, and edge cases — is in the sibling document at `../specs/dict-dsl-spec.md`.

## Decision Drivers

- **Test source of truth** — fixture contracts must be copy-paste-able inline Python literals, not external files.
- **YAGNI per the Sprint 0 risk register** — the second-system effect is the primary V1 risk; reject references, inheritance, and macros.
- **Must express all 9 V1 field types** — `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`.
- **Pure adapter** (EXTENDING.md §1.4) — same input dict always produces the same `CanonicalContract`.
- **Public SPI compliance** (EXTENDING.md §1.2) — the adapter implements `ContractAdapter.format_id`, `adapt`, and `export`.
- **No new dependencies** — the 3-package core policy (DEPENDENCIES.md §2) forbids adding a parser generator.

## Considered Options

### Option A — Pure-Python dict DSL with 5 concepts (chosen)

A literal Python `dict` structure parsed by a ~200-line dict-walk. No new grammar, no parser generator, no custom syntax. The surface is five concepts: `FieldSpec`, `Constraint`, `Tag`, `Policy`, `Contract`.

**Pros:**

- Zero parser complexity — the parser is a recursive dict-walk, not a grammar.
- Inline copy-paste in tests — fixture contracts are Python literals.
- Direct correspondence to `CanonicalContract` field shapes — no impedance mismatch.
- Pure-Python literals are deterministic by definition.
- No new dependencies.

**Cons:**

- No compile-time validation — errors are caught at `adapt()` time, not at parse time.
- Limited expressiveness — no references, no inheritance, no macros.
- Repeated field shapes in large contracts (no `$ref`).

### Option B — Custom syntax with grammar

A new file format (e.g., `.pax` or `.pax.yaml`) with a full BNF grammar and a parser generator (lark, pyparsing, or hand-written recursive descent).

**Pros:**

- More expressive — can support references (`$ref`), inheritance, macros, and conditional defaults.
- Better error messages with line and column numbers.
- Standalone files decoupled from Python source.

**Cons:**

- ~2,000 lines of parser code for a V1 surface.
- New dependency (lark or pyparsing) — pushes core past the 3-package policy.
- Drift risk between DSL syntax and `CanonicalContract` shape.
- Higher risk for V1: parser bugs, grammar design mistakes, maintenance burden.
- Violates YAGNI — V1 does not need references or inheritance.

### Option C — JSON Schema subset (no V1-only DSL)

Reuse JSON Schema with a curated subset. No new format; the Dict DSL is just JSON Schema with Paxman-specific extensions.

**Pros:**

- No new code — delegates entirely to the JSON Schema adapter.
- Familiar to API developers.

**Cons:**

- Loses the "internal escape hatch" property — the Dict DSL and JSON Schema adapter would share the same code path, defeating the purpose of having a separate adapter.
- No leverage on the test-source-of-truth property — JSON Schema is verbose and not copy-paste-friendly for inline tests.
- Loses the explicit `Policy` and `Tag` surface that the Dict DSL provides.
- Cannot express Paxman-specific concepts (confidence targets, fallback policies) without extensions that are effectively a new DSL anyway.

## Decision Outcome

**Chosen option: A (Pure-Python dict DSL, 5 concepts).**

The Dict DSL is a 5-concept surface — `FieldSpec`, `Constraint`, `Tag`, `Policy`, `Contract` — expressed as pure-Python `dict` literals and parsed by a ~200-line dict-walk. No references, no inheritance, no macros, no custom syntax, no new dependencies.

Rationale:

1. **YAGNI** — the Sprint 0 risk register names the second-system effect as the primary V1 risk. References, inheritance, and macros are V2 features.
2. **Zero parser code** — the parser is a recursive dict-walk, not a grammar. This is the smallest possible implementation.
3. **Inline test contracts** — fixture contracts are Python literals, copy-paste-friendly, version-control-friendly.
4. **No impedance mismatch** — the same dict shape appears in fixtures, tests, and `CanonicalContract` construction.
5. **Determinism** — pure-Python literals are deterministic by definition; no parser ambiguity.
6. **3-package policy preserved** — no lark, no pyparsing, no new dependency.

If V2 needs references or inheritance, the DSL can be extended (or a new format introduced) without breaking V1 contracts.

## Consequences

### Positive

- Smallest possible parser (≤ 200 lines).
- Fixture contracts read like Python — no context-switching to a custom syntax.
- No new dependencies.
- Trivially pure: same input dict always produces the same `CanonicalContract`.
- Error model is well-defined (13 documented `error_code` values; see sibling spec §7).

### Negative

- Compile-time validation deferred to `adapt()` time — typos in dict keys are runtime errors.
- No references — repeated field shapes in large contracts must be manually duplicated.
- No polymorphism — `oneOf` / `anyOf` / `allOf` users must use Pydantic or JSON Schema instead.

### Neutral

- Documentation: ~400 lines (spec + grammar + examples) in `docs/specs/dict-dsl-spec.md`.
- Parser lives in `paxman.contract.adapters.dict_dsl` (Sprint 2, per `sprint-02-contract-subsystem.md`).

## Validation

- `docs/specs/dict-dsl-spec.md` exists with BNF grammar, ≥3 worked examples, and ≥5 edge cases (Sprint 0 D0.1).
- All 9 V1 field types are expressible in the dict format.
- Pure-Python dict format verified by Sprint 2 unit tests.
- Round-trip property test: `adapt(export(adapt(d))) == adapt(d)` for all V1 field types (Sprint 7).
- `InvalidContractError` raised for all 13 documented `error_code` values (Sprint 2).
- The Dict DSL adapter is used as the lingua franca for all internal test fixtures.

## References

- Sibling document: `../specs/dict-dsl-spec.md`
- `0007-contract-adapter-set-v1.md` — V1 adapter set requirement
- `../../EXTENDING.md` §1 — adapter SPI
- `../../ARCHITECTURE.md` §4.1 — `CanonicalContract`
- `../../GLOSSARY.md` — V1 field types
- `../../PACKAGE_STRUCTURE.md` §3.2 — planned `adapters/dict_dsl.py`
- `../../DEPENDENCIES.md` §2 — core dependency policy
- Sprint 0 D0.1: `../../sprints/sprint-00-design-closure.md`

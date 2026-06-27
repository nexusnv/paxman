# ADR-0004: MONEY as a First-Class Type

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Paxman normalizes data that frequently includes monetary values (invoices, quotations, procurement). Two options for representing money:

1. **`MONEY` as a first-class field type** — distinct from `STRING`, `DECIMAL`, etc. Carries amount, ISO-4217 currency code, and precision.
2. **`MONEY` as a `DECIMAL` with metadata** — money is just a decimal with a `currency` semantic tag.

How should Paxman represent monetary values?

## Decision Drivers

- **First-class support for finance** — Paxman's primary use cases are invoice/quotation/procurement normalization (PRD §6).
- **Currency arithmetic** — cross-currency operations require an explicit currency, not a tag.
- **Precision** — money must not lose precision through float conversion.
- **FX handling** — explicit `CurrencyPolicy` for cross-currency resolution.
- **Auditability** — finance requires clear, unambiguous representation.

## Considered Options

### Option A — `MONEY` as a first-class type (chosen)

`MONEY` is one of the nine V1 field types. It is a structured type: `Decimal amount + ISO-4217 currency code + optional precision`. The Reconciler has a `MONEY` arithmetic module that enforces currency policy.

**Pros:**

- Strong type safety at the canonical contract level.
- Currency mismatches are caught at the contract level, not at runtime.
- `MONEY` arithmetic is a Reconciler primitive, not a capability.
- Audit trail is unambiguous.

**Cons:**

- More adapter work: each adapter (Pydantic, JSON Schema, OpenAPI) must handle `MONEY` distinctly.
- Cross-adapter round-trips must preserve `MONEY` semantics.

### Option B — `MONEY` as a `DECIMAL` with a `currency` semantic tag

Money is a `DECIMAL` field with `semantic_tags = ["currency", "iso4217"]`. The currency is a separate field in the same object.

**Pros:**

- Easier adapter work: existing types cover money.
- The semantic tag system already exists.

**Cons:**

- Currency is not structurally tied to the value, leading to mis-pairing.
- The Reconciler must do a lookup for every money-typed field to find its currency.
- FX and precision handling are scattered.

## Decision Outcome

**Chosen option: A (first-class).** `MONEY` is a first-class field type in the canonical contract. The V1 set of field types is `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY` (see [ARCHITECTURE.md §4.1](../reference/architecture.md)).

The `MONEY` type is modeled as:

```python
MoneyValue(
    amount: Decimal,           # exact precision
    currency: str,             # ISO-4217 code
    precision: int | None,     # decimal places; None = inferred
)
```

Adapters are responsible for mapping external representations to `MoneyValue` (e.g., JSON Schema `type: "string", pattern: "^\\d+\\.\\d{2} [A-Z]{3}$"`).

The Reconciler has a `money.py` module that implements:

- Currency matching
- Cross-currency resolution via `CurrencyPolicy` (STRICT_MATCH, ALLOW_FX, REJECT_WITHOUT_RATE)
- Decimal arithmetic (no float)

## Consequences

### Positive

- Finance use cases are first-class.
- Cross-currency mismatches are caught at the contract level.
- Audit trail is unambiguous.

### Negative

- Adapter work is more complex.
- Adapter tests must cover `MONEY` round-trips.

### Neutral

- `MONEY` joins the nine V1 types and inherits the same canonicalization, validation, and evidence rules.

## Validation

- The contract adapter tests round-trip `MONEY` for every adapter.
- The Reconciler tests cover `STRICT_MATCH`, `ALLOW_FX`, and `REJECT_WITHOUT_RATE` policies.
- The `MONEY` arithmetic tests assert no precision loss for representative decimal operations.

## References

- PRD.md §6 (use cases), §7.2
- ARCHITECTURE.md §4.1 (canonical contract types)
- PACKAGE_STRUCTURE.md §7 (reconciler/money.py)

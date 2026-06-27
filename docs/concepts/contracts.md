# Contracts

> **Status:** V1
> **Audience:** Paxman users authoring or consuming contracts; Paxman
> contributors extending the contract subsystem.
> **Related docs:** [GLOSSARY.md](../reference/glossary.md) §Contract,
> [EXTENDING.md §1](../reference/extending.md) (adding a new adapter),
> [ARCHITECTURE.md §3 Contract Subsystem](../reference/architecture.md),
> [ADR-0007](../adr/0007-contract-adapter-set-v1.md) (V1 adapter set),
> [ADR-0009](../adr/0009-dict-dsl-v1.md) (Dict DSL),
> [docs/specs/dict-dsl-spec.md](../specs/dict-dsl-spec.md).

A **contract** is the caller-supplied description of what a normalized
artifact should look like. Paxman never owns your schema — you bring
the contract, and Paxman translates it into its internal
**CanonicalContract** before planning, executing, or reconciling.

This document explains what a contract is in Paxman, the four formats
Paxman accepts natively, how the adapter layer translates between
them, and how validation guarantees the CanonicalContract is well-formed
before the pipeline runs.

---

## 1. The contract-driven design

Paxman is **contract-driven** end-to-end:

1. You supply a contract in a format you already use (Pydantic, JSON
   Schema, OpenAPI, or the built-in Dict DSL).
2. Paxman translates it to a `CanonicalContract` (the internal model).
3. The planner synthesizes a per-field execution plan from the
   canonical contract.
4. The executor runs the plan, the reconciler merges candidates, and
   the artifact carries the resolved values back in a contract-shaped
   `normalized_data` dict.

Paxman never *modifies* your contract. It never imports it into a
registry, never persists it, never wraps it in a different schema
language. The contract you pass to `paxman.normalize()` is the same
contract you pass to `paxman.replay()`.

This means:

- **You stay in control of your domain model.** Paxman is a library, not
  a service.
- **Paxman does not own your schema.** The `CanonicalContract` is an
  internal data structure; it is **not** a public API surface.
- **Replay is contract-bound.** Replay requires the same contract you
  used originally, which guarantees that the artifact's
  `normalized_data` still matches your domain model.

---

## 2. The CanonicalContract (internal model)

Every contract format flows into the same internal model:
`paxman.contract.canonical.CanonicalContract`. The CanonicalContract is
**not** a public type — it is an internal data structure that the
planner, executor, reconciler, and artifact subsystems all read from.

A `CanonicalContract` consists of:

| Field | Type | Purpose |
|---|---|---|
| `id` | `str` | Stable identifier (used in artifacts, hashes, and logs). |
| `version` | `str` | The contract's version (caller-supplied; surfaces in replay). |
| `fields` | `tuple[CanonicalField, ...]` | One entry per field, in declaration order. |
| `constraints` | `tuple[Constraint, ...]` | Cross-field validation rules (V1: contract-level). |
| `policies` | `ContractPolicy` | Per-contract overrides (e.g. `confidence_floor`). |

A `CanonicalField` carries:

- `path` — dotted path used in the artifact's `normalized_data` keys.
- `type` — one of the 9 V1 `FieldType` literals (`STRING`, `INTEGER`,
  `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`).
- `required` — `True` means unresolved status prevents `SUCCESS`.
- `description` — human-readable description (carried into the artifact).
- `tags` — semantic tags for planner heuristic hints.
- `default` — fallback value if the field cannot be resolved.
- `constraints` — field-level `Constraint` entries (length, range,
  regex, enum, ISO-4217, …).
- `confidence_threshold` — read-only threshold used by the planner to
  set `target_confidence` on the `FieldPlan`.

> **The MONEY type is first-class** ([ADR-0004](../adr/0004-money-first-class-type.md)):
> it is a structured type with currency + precision, **not** a
> `DECIMAL` with a tag. See [§6](#6-the-money-type) below.

---

## 3. The four V1 formats

Per [ADR-0007](../adr/0007-contract-adapter-set-v1.md), Paxman V1 ships
**three required** adapters and **one optional** adapter.

| Format | `format_id` | Required? | Best for |
|---|---|---|---|
| **Pydantic v2** | `pydantic` | Required | Python apps that already use Pydantic. |
| **JSON Schema** | `json_schema:draft-2020-12` | Required | API specs, cross-language systems. |
| **Dict DSL** | `dict_dsl` | Required | Internal tests, escape hatch, no external dependency. |
| **OpenAPI 3.x** | `openapi:3.0` / `openapi:3.1` | Best-effort | OpenAPI service specs (V1 subset only). |

### 3.1 Pydantic v2

You pass the `BaseModel` class itself. The adapter walks
`model_fields` and `field_info.metadata` to extract type, constraints,
and defaults. `Annotated[T, Field(...)]` and the legacy
`_PydanticGeneralMetadata` are both supported.

```python
from pydantic import BaseModel, Field


class Invoice(BaseModel):
    supplier_name: str = Field(..., description="The supplier's name.")
    total_amount: float = Field(..., description="Total invoice amount.")
    currency_code: str = Field(..., description="ISO-4217 currency code.")
```

For `MONEY`, define a field whose annotation inherits from
`paxman.contract.adapters.pydantic.Money` (the MONEY base class
shipped with the Pydantic adapter) — see [§6](#6-the-money-type).

### 3.2 JSON Schema (draft 2020-12)

You pass a `dict` (or a `str` containing JSON) that follows draft
2020-12. The adapter supports `type`, `properties`, `required`,
`enum`, `pattern`, `minLength`/`maxLength`, `minimum`/`maximum`, and
`items`. MONEY is encoded as an `object` with the `x-paxman-type`
extension (see [§6](#6-the-money-type)).

```python
import paxman

contract = {
    "type": "object",
    "properties": {
        "supplier_name": {"type": "string"},
        "total_amount": {"type": "number"},
        "currency_code": {"type": "string", "pattern": "^[A-Z]{3}$"},
    },
    "required": ["supplier_name", "total_amount", "currency_code"],
}
```

A `str` input is also accepted; the adapter parses it as JSON at adapt
time.

### 3.3 Dict DSL

You pass a plain `dict` following the Paxman Dict DSL grammar
([docs/specs/dict-dsl-spec.md](../specs/dict-dsl-spec.md)). The DSL
defines exactly **five concepts** ([ADR-0009](../adr/0009-dict-dsl-v1.md)):
`FieldSpec`, `Constraint`, `Tag`, `Policy`, `Contract`. No custom
syntax, no parser, no new dependency.

```python
import paxman

contract = {
    "id": "invoice_v1",
    "version": "1.0",
    "fields": (
        {"name": "supplier_name", "type": "STRING", "required": True},
        {"name": "total_amount", "type": "DECIMAL", "required": True},
        {"name": "currency_code", "type": "STRING", "required": True},
    ),
}
```

The Dict DSL is Paxman's **lingua franca** for internal tests. It is
deliberately minimal — the grammar is documented in
[docs/specs/dict-dsl-spec.md](../specs/dict-dsl-spec.md).

### 3.4 OpenAPI 3.x (best-effort)

You pass a `dict` (or a `str`) representing an OpenAPI 3.x document.
The adapter delegates per-property parsing to the JSON Schema adapter
and supports the V1 subset only:

- `3.0.x` and `3.1.x` documents.
- `components/schemas/*` (top-level `schema` is also supported).
- Recursive `$ref` inlining (with cycle detection).
- V1-supported `type`, `properties`, `enum`, `pattern`, `format`,
  `minLength`/`maxLength`, `minimum`/`maximum`, `items`.

**Rejected** in V1 (with `UNSUPPORTED_OPENAPI_FEATURE`): `oneOf`,
`anyOf`, `allOf`, `discriminator`. See the OpenAPI adapter tests for
the full reject list.

---

## 4. Format auto-detection

`paxman.normalize()` and `paxman.replay()` auto-detect the contract
format. The detection order is:

1. **Pydantic** — duck-typed via `hasattr(contract, "model_fields")`.
2. **Dict DSL** — `isinstance(contract, dict)`.
3. **String** — try `json_schema:draft-2020-12`, then `openapi:3.0`.

If detection fails, the call returns an artifact with
`status=Status.INVALID_CONTRACT` and an `ADAPTER_NOT_FOUND` error in
the diagnostics.

You can also register additional adapters via
`paxman.register_adapter(...)` and call `paxman.normalize()` with the
same `format_id` (e.g. an Avro or Protobuf adapter you ship
externally).

---

## 5. The adapter layer

A **contract adapter** is a class that implements the
`ContractAdapter` Protocol (the SPI; see [EXTENDING.md §1](../reference/extending.md)):

```python
class ContractAdapter(Protocol):
    @property
    def format_id(self) -> str: ...
    def adapt(self, external: object) -> CanonicalContract: ...
    def export(self, canonical: CanonicalContract) -> object: ...
```

The adapter's job is **only translation** — format-in, CanonicalContract
out (and back). Adapters:

- **May not** read raw input.
- **May not** invoke capabilities or plan/execute.
- **May not** mutate global state.
- **May not** embed provider secrets.
- **Must** be pure: the same input → the same `CanonicalContract`
  byte-for-byte. No randomness, no clock, no I/O.

Adapters self-register on import. The process-local registry
(`paxman.contract.registry`) is queried by
`_detect_and_adapt(contract)` in `paxman.api.normalize`.

### 5.1 The validation step

After `adapt()`, the contract is validated by
`paxman.contract.validator`. The validator enforces:

- All fields have one of the 9 V1 types.
- All constraints reference valid kinds and types.
- All paths are dotted paths with no `..` or empty segments.
- All semantic tags are in the known-tag list
  (`paxman.contract.semantics.KNOWN_SEMANTIC_TAGS`).

Invalid contracts raise `UnsupportedFieldTypeError`,
`InvalidConstraintError`, `InvalidPathError`, or
`InvalidSemanticTagError`. The Executor never sees an invalid
contract.

---

## 6. The MONEY type

`MONEY` is a **first-class field type** ([ADR-0004](../adr/0004-money-first-class-type.md)),
not a `DECIMAL` with a tag. Every `MONEY` field carries:

- `amount` — a `decimal.Decimal` (never `float`; per ADR-0004 the
  internal representation is `Decimal`).
- `currency` — a 3-letter ISO-4217 code (e.g. `"USD"`, `"EUR"`).
- `precision` — optional scale hint (digits after the decimal point).

```python
from decimal import Decimal
from pydantic import BaseModel
from paxman.contract.adapters.pydantic import Money


class MoneyAmount(Money):
    amount: Decimal
    currency: str  # ISO-4217


class Invoice(BaseModel):
    total: MoneyAmount
```

In the Dict DSL:

```python
{"name": "total", "type": "MONEY", "required": True}
```

In JSON Schema:

```json
{
  "type": "object",
  "x-paxman-type": "MONEY",
  "properties": {
    "amount": {"type": "string", "pattern": "^[0-9]+(\\.[0-9]+)?$"},
    "currency": {"type": "string", "pattern": "^[A-Z]{3}$"}
  },
  "required": ["amount", "currency"]
}
```

The Reconciler enforces **currency matching** by default
(`CurrencyPolicy.STRICT_MATCH`). `ALLOW_FX` requires an explicit
`fx_rate` field on the contract. `REJECT_WITHOUT_RATE` rejects
cross-currency candidates outright. See
[GLOSSARY.md §CurrencyPolicy](../reference/glossary.md) for the full
behaviour matrix.

Decimal precision is preserved end-to-end. The internal pipeline
(`Budget`, `CostHint`, `BudgetTracker`, `ExecutionState`,
`Statistics`) switched from `float` to `Decimal` per
[ADR-0010](../adr/0010-budget-money-decimal.md). `MONEY` arithmetic
never loses precision.

---

## 7. Contract policies (per-contract overrides)

A contract can carry a `ContractPolicy` that **overrides** the
call-site `Policy` for specific fields:

- `confidence_floor` — overrides `Policy.confidence_floor` for fields
  in this contract.
- `unresolved_acceptable` — overrides the call-site
  `Policy.unresolved_acceptable` flag.
- `currency_policy` — overrides `Policy.currency_policy` for
  `MONEY` fields.

The planner and reconciler compute an **effective policy** =
`derive_effective_policy(call_site_policy, contract_policy)` and
apply it to the relevant subsystems.

> **Policies are not contracts.** The contract is a static description
> of the domain. Policies are runtime knobs. Keep them separate.

---

## 8. Adapters and the public API

Adapters are an **SPI** (`paxman.protocols.ContractAdapter`); you can
register your own with `paxman.register_adapter(...)`. See
[EXTENDING.md §1](../reference/extending.md) for the full step-by-step.

The four V1 adapters are **always present** (Pydantic, JSON Schema,
Dict DSL are required; OpenAPI is best-effort). The first three are
guaranteed to handle every V1 contract. The OpenAPI adapter is
guaranteed to handle a useful subset of 3.0/3.1 documents; documents
outside that subset raise `UNSUPPORTED_OPENAPI_FEATURE`.

---

## 9. Common pitfalls

| Pitfall | Why it bites | Fix |
|---|---|---|
| Passing an `instance` of a Pydantic model instead of the class | The adapter needs the class, not an instance. | Pass `Invoice` (the class), not `Invoice(...)`. |
| Pydantic `Optional[X]` with no default | The adapter sees a non-required field with no default. | Either add `= None` or `= Field(default=None)`. |
| Pydantic `bool` field used as a flag (e.g. `is_paid: bool`) | V1 rejects `bool`-as-int coercion. | Use the `BOOLEAN` type explicitly. |
| JSON Schema `string` with `format: "date"` | The adapter only reads `type` and `properties`, not `format`. | Add a `pattern` constraint for the date format you need. |
| Dict DSL `MONEY` field as `{"amount": "100.00", "currency": "USD"}` | The Decimal string is parsed at adapt time. | Pass a string; the adapter converts to `Decimal` for you. |
| OpenAPI document with `oneOf` | V1 rejects `oneOf`/`anyOf`/`allOf`/`discriminator`. | Flatten the schema to a single `type` with optional `nullable`. |
| Mixing `MONEY` types in one contract with different currencies | The Reconciler rejects by default. | Set `CurrencyPolicy.ALLOW_FX` and add an `fx_rate` field. |

---

## 10. See also

- [GLOSSARY.md §Contract](../reference/glossary.md) — the single source of
  truth for the term.
- [EXTENDING.md §1](../reference/extending.md) — adding a new contract
  adapter (full walkthrough).
- [ARCHITECTURE.md §3 Contract Subsystem](../reference/architecture.md) —
  internal architecture of the contract subsystem.
- [docs/specs/dict-dsl-spec.md](../specs/dict-dsl-spec.md) — the
  Dict DSL grammar, examples, and error model.
- [docs/adr/0007-contract-adapter-set-v1.md](../adr/0007-contract-adapter-set-v1.md) —
  why these four formats and no others in V1.
- [docs/adr/0009-dict-dsl-v1.md](../adr/0009-dict-dsl-v1.md) — the
  Dict DSL rationale.
- [docs/adr/0004-money-first-class-type.md](../adr/0004-money-first-class-type.md) —
  MONEY as a first-class type.
- [docs/adr/0010-budget-money-decimal.md](../adr/0010-budget-money-decimal.md) —
  the cost-pipeline Decimal switch (extends ADR-0004).

# Dict DSL Specification

> **Status:** Draft v1.
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Related docs:** [EXTENDING.md](../../EXTENDING.md) (ContractAdapter SPI), [ARCHITECTURE.md](../../ARCHITECTURE.md) (subsystem spec), [GLOSSARY.md](../../GLOSSARY.md) (vocabulary), [ADR-0007](../adr/0007-contract-adapter-set-v1.md) (V1 adapter set)

---

## 1. Overview

The Dict DSL is Paxman's **native contract format** — a pure-Python `dict` that maps directly to `CanonicalContract` with no external parser, no custom syntax, and no new dependency. It exists for three reasons:

1. **Internal escape hatch.** When a caller does not use Pydantic and does not want to author JSON Schema, the Dict DSL provides a zero-dependency way to define contracts.
2. **Test source of truth.** All internal contract fixtures are written as Dict DSL dicts. This makes tests readable, copy-pasteable, and free of third-party schema libraries. Per [ADR-0007](../adr/0007-contract-adapter-set-v1.md), "the Dict DSL is used by all internal tests as the lingua franca."
3. **Adapter reference implementation.** The Dict DSL adapter is the simplest possible `ContractAdapter` implementation. It serves as the template for third-party adapter authors (see [EXTENDING.md §1](../../EXTENDING.md)).

### When to use which adapter

| Scenario | Recommended adapter |
|---|---|
| Python app already uses Pydantic models | Pydantic Adapter |
| Contract comes from an API spec or cross-language system | JSON Schema Adapter |
| Writing tests, quick prototypes, or no external schema library | **Dict DSL** |
| Contract is an OpenAPI 3.x document | OpenAPI Adapter (best-effort) |

The Dict DSL is **not** a replacement for Pydantic or JSON Schema in production use. It is deliberately minimal.

---

## 2. Design Goals

1. **Round-trippable.** The same Dict DSL input always produces the same `CanonicalContract` byte-for-byte. No ambiguity, no heuristic interpretation.

2. **Pure.** The adapter performs no I/O, reads no clock, generates no random values. It is a function `dict -> CanonicalContract`. See [EXTENDING.md §1.4](../../EXTENDING.md).

3. **Five-concept V1 surface.** The DSL defines exactly five concepts: `FieldSpec`, `Constraint`, `Tag`, `Policy`, `Contract`. References, inheritance, macros, and conditional defaults are explicitly rejected (YAGNI). See §8.

4. **Expresses all 9 V1 field types.** `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY` — every type in [GLOSSARY.md](../../GLOSSARY.md) is representable.

5. **Test-source-of-truth.** A valid contract is a Python literal. No file I/O, no loader, no YAML parser. Copy a dict into a test and it runs.

6. **Fail-fast validation.** Invalid input raises `InvalidContractError` with a structured `error_code` and `context` dict. The Executor never sees an invalid contract. See [EXTENDING.md §1.2](../../EXTENDING.md).

7. **Small parser.** The entire adapter is a dict-walk plus validation — approximately 200 lines. No grammar, no tokenizer, no AST.

---

## 3. The 5 Concepts

### 3.1 FieldSpec

A single field in the contract. Every field has a name, a type, and a required flag.

| Key | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | `str` | yes | — | Field identifier. Must be unique within the contract. Used as the key in `normalized_data`. |
| `type` | `str` | yes | — | One of the 9 V1 type literals (see table below). |
| `required` | `bool` | yes | — | If `True`, unresolved status prevents `SUCCESS`. |
| `description` | `str` | no | `None` | Human-readable description. Carried into the `CanonicalField`. |
| `tags` | `list[str]` | no | `[]` | Semantic tags for planner heuristic hints (see §3.3). |
| `default` | typed value | no | `None` | Fallback value when the field is unresolved. Type must match `type`. |
| `constraints` | `list[Constraint]` | no | `[]` | Field-level constraints (see §3.2). |

**V1 type literals:**

| Literal | Canonical type | Default value example |
|---|---|---|
| `"STRING"` | `FieldType.STRING` | `"hello"` |
| `"INTEGER"` | `FieldType.INTEGER` | `42` |
| `"DECIMAL"` | `FieldType.DECIMAL` | `Decimal("3.14")` |
| `"BOOLEAN"` | `FieldType.BOOLEAN` | `True` |
| `"DATE"` | `FieldType.DATE` | `"2026-01-15"` (ISO 8601 string) |
| `"ENUM"` | `FieldType.ENUM` | `"active"` |
| `"OBJECT"` | `FieldType.OBJECT` | `{}` |
| `"ARRAY"` | `FieldType.ARRAY` | `[]` |
| `"MONEY"` | `FieldType.MONEY` | `{"amount": "100.00", "currency": "USD"}` |

### 3.2 Constraint

A validation rule attached to a field or to the contract as a whole.

| Key | Type | Required | Description |
|---|---|---|---|
| `kind` | `str` | yes | Constraint identifier (see table below). |
| `params` | `dict` | yes | Kind-specific parameters. May be `{}` for parameterless constraints. |

**V1 constraint kinds:**

| Kind | Applies to | Params | Description |
|---|---|---|---|
| `min_length` | `STRING`, `ARRAY` | `{"min": int}` | Minimum length (characters or elements). |
| `max_length` | `STRING`, `ARRAY` | `{"max": int}` | Maximum length. |
| `pattern` | `STRING` | `{"regex": str}` | Regex match. Must be a valid Python `re` pattern. |
| `min_value` | `INTEGER`, `DECIMAL`, `MONEY` | `{"min": number}` | Minimum numeric value. |
| `max_value` | `INTEGER`, `DECIMAL`, `MONEY` | `{"max": int}` | Maximum numeric value. |
| `enum` | `STRING`, `INTEGER` | `{"values": list}` | Allowed values (closed set). |
| `iso_4217` | `STRING`, `MONEY` | `{}` | Value must be a valid ISO-4217 currency code (3-letter uppercase). |

Constraints at the **contract level** apply to the entire contract (e.g., cross-field validation, post-V1). Constraints at the **field level** apply to that field only.

### 3.3 Tag

A string label attached to a field via the `tags` key. Tags are semantic hints consumed by the Planner's heuristic chain. They are **not** validated by the adapter — unknown tags are silently accepted.

**Common tags (conventional, not enforced):**

| Tag | Planner effect |
|---|---|
| `"pii"` | Prefer local extraction; avoid remote inference unless `policy.allow_remote_inference=True`. |
| `"currency-sensitive"` | Trigger `iso_4217` validation; prefer `MONEY`-aware capabilities. |
| `"high-stakes"` | Emit diagnostic on low-confidence resolution; may raise `target_confidence`. |

Tags are free-form strings. The Dict DSL does not enforce a vocabulary.

### 3.4 Policy

A per-contract set of operational knobs. All keys are optional; omitted keys use defaults.

| Key | Type | Default | Description |
|---|---|---|---|
| `confidence_floor` | `float` | `0.80` | Minimum confidence to accept a resolved value. Range: `[0.0, 1.0]`. |
| `unresolved_acceptable` | `bool` | `False` | If `True`, unresolved required fields yield `PARTIAL_SUCCESS` instead of `UNRESOLVED`. |
| `stop_on_first_unresolved` | `bool` | `False` | If `True`, halt execution on the first unresolved required field. |

The policy maps to `CanonicalContract.policies` (a `ContractPolicy` object). It does **not** replace the call-site `Policy` passed to `paxman.normalize()` — contract-level policy is merged with call-site policy at runtime.

### 3.5 Contract

The top-level dict. Represents a complete, self-contained contract.

| Key | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `str` | yes | — | Unique contract identifier. Carried into `CanonicalContract.id`. |
| `version` | `str` | no | `"1"` | Contract schema version. V1 uses the literal `"1"`. |
| `fields` | `list[FieldSpec]` | yes | — | One or more field specs. Must not be empty. |
| `constraints` | `list[Constraint]` | no | `[]` | Contract-level constraints. |
| `policy` | `Policy` | no | `None` | Per-contract operational policy. |

A valid contract is a single `dict` that satisfies the grammar in §4.

---

## 4. BNF Grammar

The grammar describes the **structure** of a valid Dict DSL contract. Angle brackets denote non-terminals. `?` marks optional keys. `"..."` denotes string literals.

```text
<contract>       ::= { "id": <string>,
                       "version"?: <string>,
                       "fields": [<field_spec>, ...],
                       "constraints"?: [<constraint>, ...],
                       "policy"?: <policy> }

<field_spec>     ::= { "name": <string>,
                       "type": <v1_type>,
                       "required": <bool>,
                       "description"?: <string>,
                       "tags"?: [<string>, ...],
                       "default"?: <default_value>,
                       "constraints"?: [<constraint>, ...] }

<v1_type>        ::= "STRING"
                   | "INTEGER"
                   | "DECIMAL"
                   | "BOOLEAN"
                   | "DATE"
                   | "ENUM"
                   | "OBJECT"
                   | "ARRAY"
                   | "MONEY"

<default_value>  ::= <string>           ; for STRING, DATE, ENUM
                   | <integer>          ; for INTEGER
                   | <decimal_string>   ; for DECIMAL (e.g., Decimal("3.14"))
                   | <bool>             ; for BOOLEAN
                   | {}                 ; for OBJECT
                   | []                 ; for ARRAY
                   | <money_value>      ; for MONEY

<money_value>    ::= { "amount": <decimal_string>, "currency": <iso_4217_code> }

<iso_4217_code>  ::= <uppercase_3_letter_string>   ; e.g., "USD", "EUR", "JPY"

<constraint>     ::= { "kind": <constraint_kind>, "params": <params> }

<constraint_kind>::= "min_length"
                   | "max_length"
                   | "pattern"
                   | "min_value"
                   | "max_value"
                   | "enum"
                   | "iso_4217"

<params>         ::= { ... }   ; kind-specific; see §3.2

<policy>         ::= { "confidence_floor"?: <float>,
                       "unresolved_acceptable"?: <bool>,
                       "stop_on_first_unresolved"?: <bool> }

<string>         ::= <python str literal>
<integer>        ::= <python int literal>
<decimal_string> ::= <python str representing a decimal number>
<bool>           ::= True | False
```

**Parsing rules:**

- The adapter walks the dict depth-first. Unknown top-level or field-level keys are ignored (forward-compatible).
- `constraints` and `policy` keys that are present but empty (`[]` or `{}`) are treated as absent.
- `default` values are validated against `type` at parse time. A mismatch raises `DEFAULT_TYPE_MISMATCH`.

---

## 5. Worked Examples

### Example 1: Minimal contract

Two fields, no constraints, no policy.

```python
{
    "id": "user-profile",
    "fields": [
        {
            "name": "full_name",
            "type": "STRING",
            "required": True,
            "description": "The user's display name.",
        },
        {
            "name": "age",
            "type": "INTEGER",
            "required": False,
            "default": 0,
        },
    ],
}
```

### Example 2: Invoice with MONEY, ARRAY, and ENUM

A realistic invoice contract using monetary values, line items, and a currency code enum.

```python
{
    "id": "invoice-v1",
    "version": "1",
    "fields": [
        {
            "name": "supplier_name",
            "type": "STRING",
            "required": True,
            "description": "Legal name of the supplier.",
            "tags": ["pii"],
            "constraints": [
                {"kind": "min_length", "params": {"min": 1}},
                {"kind": "max_length", "params": {"max": 500}},
            ],
        },
        {
            "name": "currency_code",
            "type": "ENUM",
            "required": True,
            "description": "ISO-4217 currency code for the invoice.",
            "tags": ["currency-sensitive"],
            "constraints": [
                {"kind": "iso_4217", "params": {}},
            ],
        },
        {
            "name": "total_amount",
            "type": "MONEY",
            "required": True,
            "description": "Total invoice amount.",
            "tags": ["currency-sensitive", "high-stakes"],
            "constraints": [
                {"kind": "min_value", "params": {"min": 0}},
            ],
        },
        {
            "name": "invoice_date",
            "type": "DATE",
            "required": True,
        },
        {
            "name": "line_items",
            "type": "ARRAY",
            "required": False,
            "default": [],
            "description": "Individual line items on the invoice.",
        },
        {
            "name": "paid",
            "type": "BOOLEAN",
            "required": False,
            "default": False,
        },
    ],
    "policy": {
        "confidence_floor": 0.85,
        "unresolved_acceptable": False,
    },
}
```

### Example 3: Adversarial test fixture

High-confidence policy, strict stopping, designed for testing edge-case behavior.

```python
{
    "id": "adversarial-fixture-001",
    "version": "1",
    "fields": [
        {
            "name": "transaction_id",
            "type": "STRING",
            "required": True,
            "description": "Must be extracted with near-certainty.",
            "constraints": [
                {"kind": "pattern", "params": {"regex": "^TXN-[A-Z0-9]{8,16}$"}},
            ],
        },
        {
            "name": "amount",
            "type": "MONEY",
            "required": True,
            "default": {"amount": "0.00", "currency": "USD"},
            "constraints": [
                {"kind": "min_value", "params": {"min": 0}},
                {"kind": "iso_4217", "params": {}},
            ],
        },
        {
            "name": "category",
            "type": "ENUM",
            "required": True,
            "constraints": [
                {"kind": "enum", "params": {"values": ["food", "transport", "utilities", "other"]}},
            ],
        },
        {
            "name": "notes",
            "type": "STRING",
            "required": False,
            "default": "",
            "constraints": [
                {"kind": "max_length", "params": {"max": 1000}},
            ],
        },
    ],
    "constraints": [],
    "policy": {
        "confidence_floor": 0.95,
        "unresolved_acceptable": False,
        "stop_on_first_unresolved": True,
    },
}
```

---

## 6. Edge Cases

### EC1: Missing required field `name`

A `FieldSpec` dict without a `"name"` key, or with `"name": None`, or with `"name": ""`.

**Behavior:** Raise `InvalidContractError` with `error_code="MISSING_FIELD_NAME"`. Context: `{"field_index": <int>}`.

### EC2: Unknown type value

A field with `"type": "STRINGY"` or any value not in the 9 V1 type literals.

**Behavior:** Raise `InvalidContractError` with `error_code="UNKNOWN_FIELD_TYPE"`. Context: `{"field_name": <str>, "type": <str>}`.

### EC3: `default` value type mismatch

A field with `"type": "INTEGER"` but `"default": "five"`, or `"type": "MONEY"` but `"default": 100`.

**Behavior:** Raise `InvalidContractError` with `error_code="DEFAULT_TYPE_MISMATCH"`. Context: `{"field_name": <str>, "expected_type": <str>, "actual_value": <repr>}`.

### EC4: Duplicate field name

Two fields in `fields` share the same `name`.

**Behavior:** Raise `InvalidContractError` with `error_code="DUPLICATE_FIELD"`. Context: `{"field_name": <str>, "first_index": <int>, "second_index": <int>}`.

### EC5: MONEY without `currency` in default

A field with `"type": "MONEY"` and `"default": {"amount": "10.00"}` (missing `"currency"`).

**Behavior:** Raise `InvalidContractError` with `error_code="MONEY_REQUIRES_CURRENCY"`. Context: `{"field_name": <str>}`.

### EC6: MONEY with non-ISO-4217 currency

A field with `"type": "MONEY"` and `"default": {"amount": "10.00", "currency": "BTC"}` where `"BTC"` is not in the ISO-4217 registry.

**Behavior:** Raise `InvalidContractError` with `error_code="INVALID_ISO_4217"`. Context: `{"field_name": <str>, "currency": <str>}`.

---

## 7. Error Model

All errors raised by the Dict DSL adapter are `InvalidContractError` instances. Each carries an `error_code` (string) and a `context` (dict) for programmatic handling.

| Error code | When | Context keys |
|---|---|---|
| `MISSING_CONTRACT_ID` | Contract has no `id`/`name` key, or it is empty/None | `contract` |
| `EMPTY_FIELDS` | `fields` is an empty list | `contract_id` |
| `MISSING_FIELDS` | Contract has no `fields` key, or `fields` is not a list | `contract_id` |
| `DUPLICATE_FIELD` | Two fields share the same `name` | `field_name`, `first_index`, `second_index` |
| `INVALID_CONTRACT` | Top-level contract shape is wrong (not a dict, wrong outer keys) | `contract` |
| `INVALID_VERSION` | `version` key is present but not a non-empty string | `version` |
| `MISSING_FIELD_NAME` | Field dict has no `name` key, or `name` is empty/None | `field_index` |
| `INVALID_FIELD` | Field dict shape is wrong (not a dict, wrong keys) | `field_index` |
| `MISSING_TYPE` | Field dict has no `type` key | `field_name` |
| `UNKNOWN_FIELD_TYPE` | `type` value is not one of the 9 V1 literals | `field_name`, `type` |
| `MISSING_REQUIRED_FLAG` | Field dict has no `required` key | `field_name` |
| `INVALID_SEMANTIC_TAG` | A `tags` entry is not a non-empty string, or a known tag is misspelled | `field_name`, `tag`, `known_tags` |
| `MISSING_ENUM_VALUES` | `ENUM` field has no `enum_values` key, or the list is empty | `field_name` |
| `UNKNOWN_CONSTRAINT_KIND` | `kind` is not one of the 7 V1 constraint kinds | `kind`, `field_name` (or `None` for contract-level) |
| `CONSTRAINT_PARAM_MISSING` | A required param key is missing from `params` | `kind`, `param`, `field_name` |
| `INVALID_CONSTRAINT` | A constraint is malformed (wrong param type, value out of range) | `kind`, `field_name`, `details` |
| `INVALID_REGEX_PATTERN` | `pattern` constraint has an invalid regex | `field_name`, `regex`, `parse_error` |
| `MONEY_REQUIRES_CURRENCY` | MONEY default is missing `currency` key | `field_name` |
| `INVALID_ISO_4217` | Currency code is not a valid ISO-4217 code | `field_name`, `currency` |
| `DEFAULT_TYPE_MISMATCH` | `default` value does not match `type` | `field_name`, `expected_type`, `actual_value` |
| `INVALID_POLICY_KEY` | `policy` dict contains an unknown key | `key`, `valid_keys` |
| `INVALID_CONFIDENCE_FLOOR` | `confidence_floor` is outside `[0.0, 1.0]` | `value` |

---

## 8. Out of Scope (V1)

The following features are explicitly **not** part of the V1 Dict DSL. They are rejected on YAGNI grounds. If a future version needs any of these, it requires an ADR.

| Rejected feature | Rationale |
|---|---|
| `$ref` / JSON references | Adds resolution complexity. Use the JSON Schema adapter for shared definitions. |
| Inheritance / base contracts | The 5-concept surface is flat. Composition is a post-V1 concern. |
| Macros / aliases | No template expansion. The DSL is a Python dict, not a language. |
| Conditional defaults (`if/then/else`) | Defaults are static typed values. Conditional logic belongs in caller code. |
| Polymorphic types (`oneOf`, `anyOf`, `allOf`) | V1 fields have exactly one type. Use the JSON Schema adapter for polymorphism. |
| Cross-field constraints (`total = sum(items[].price)`) | Contract-level constraints are a post-V1 extension point. |
| Computed / derived fields | Fields are resolved by capabilities, not computed from other fields. |
| Derived defaults (e.g., `default: <expr>`) | Defaults are literal values, not expressions. |
| Version negotiation | V1 uses `version: "1"` as a literal. No semver range, no migration. |
| JSON Schema import | Use the JSON Schema Adapter instead. |
| TOML / YAML variants | V1 is Python `dict` only. Other serialization formats are post-V1. |

---

## 9. See also

- [EXTENDING.md §1](../../EXTENDING.md) — The `ContractAdapter` SPI and how to implement a new adapter.
- [ARCHITECTURE.md §4.1](../../ARCHITECTURE.md) — The `contract/` subsystem: translation + validation boundary.
- [GLOSSARY.md](../../GLOSSARY.md) — Canonical definitions for all Paxman vocabulary.
- [ADR-0007](../adr/0007-contract-adapter-set-v1.md) — Decision to ship Dict DSL as a required V1 adapter.
- [PACKAGE_STRUCTURE.md §3](../../PACKAGE_STRUCTURE.md) — Planned module layout for `adapters/dict_dsl.py`.

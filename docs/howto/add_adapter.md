# How to Add a New Contract Adapter

> **Status:** V1
> **Audience:** Paxman users who want to add support for a new
> contract format (Avro, Protobuf, GraphQL, a vendor-specific
> schema, …).
> **Related docs:** [EXTENDING.md §1](../../EXTENDING.md) (the full
> SPI walkthrough), [docs/concepts/contracts.md](../concepts/contracts.md)
> (what a contract is), [ADR-0007](../adr/0007-contract-adapter-set-v1.md)
> (V1 adapter set).

This guide is a **focused quick-start** for adding a new contract
adapter to Paxman. The full SPI walkthrough is in
[EXTENDING.md §1](../../EXTENDING.md); this document is a 5-minute
checklist.

---

## 1. When to add a new adapter

Add a new adapter when:

- You want Paxman to accept a new schema language as input
  (Avro, Protobuf, GraphQL, …).
- You want to convert a non-supported contract origin to
  `CanonicalContract` (ERP object model → `CanonicalContract`).

Do **not** add a new adapter when:

- The format is already supported (Pydantic, JSON Schema, Dict DSL,
  OpenAPI).
- You can convert your input to a supported format with a small
  wrapper (e.g. convert ERP → JSON Schema once, then use the JSON
  Schema adapter).

If the format is brand new, you will need to **ship the adapter as
a separate PyPI package** (`paxman-<your-format>`) — the Paxman
core team only accepts adapters into the main package by ADR. See
[EXTENDING.md §6](../../EXTENDING.md).

---

## 2. The ContractAdapter SPI

```python
from typing import Protocol, Any
from paxman import CanonicalContract


class ContractAdapter(Protocol):
    """SPI: translate an external contract format to/from CanonicalContract."""

    @property
    def format_id(self) -> str:
        """Stable identifier (e.g. 'pydantic', 'json_schema:draft-2020-12')."""
        ...

    def adapt(self, external: Any) -> CanonicalContract:
        """Translate an external contract into a CanonicalContract.

        Raises:
            InvalidContractError: if the external contract is invalid.
        """
        ...

    def export(self, canonical: CanonicalContract) -> Any:
        """Translate a CanonicalContract back into the external format.

        Raises:
            InvalidContractError: if the canonical contract cannot be exported.
        """
        ...
```

The `format_id` must be **stable** — it identifies the adapter
across Paxman versions. Use a namespaced string
(`"<format>:<version>"` if the format has versions, e.g.
`"json_schema:draft-2020-12"`).

---

## 3. Step-by-step

### 3.1 Pick a `format_id`

Choose a stable identifier. Examples:

- `"avro:1.0"`
- `"protobuf:3.21"`
- `"graphql:2021"`
- `"my_erp_object"`

Do **not** include the package name in the `format_id` — it should
describe the format, not the implementation.

### 3.2 Create the adapter file

Create a new file, e.g. `paxman_myformat/adapter.py`:

```python
import attrs
from paxman import CanonicalContract, ContractPolicy, InvalidContractError
from paxman.contract._types import Constraint
from paxman.contract.canonical import CanonicalField, MoneyValue
from paxman.protocols import ContractAdapter
from paxman.types import FieldType


@attrs.frozen(slots=True)
class MyFormatAdapter:
    """Adapter for my_format contracts."""

    @property
    def format_id(self) -> str:
        return "my_format"

    def adapt(self, external: object) -> CanonicalContract:
        try:
            fields_data = parse_my_format(external)
        except ParseError as e:
            raise InvalidContractError(
                f"Failed to parse my_format: {e}",
                error_code="INVALID_MY_FORMAT",
                context={"line": e.line, "column": e.column},
            ) from e

        canonical_fields = tuple(to_canonical_field(f) for f in fields_data)
        return CanonicalContract(
            id="my_format_contract",
            version="1",
            fields=canonical_fields,
            constraints=(),
            policies=ContractPolicy(),
        )

    def export(self, canonical: CanonicalContract) -> object:
        return serialize_my_format(canonical.fields)
```

### 3.3 Be pure

The adapter **must** be a pure function of its input. No randomness,
no clock, no I/O. Same input → same `CanonicalContract` byte-for-byte.

Tests:

```python
def test_my_format_adapter_is_pure():
    adapter = MyFormatAdapter()
    external = load_fixture("my_format/simple.myf")
    a = adapter.adapt(external)
    b = adapter.adapt(external)
    assert serialize(a) == serialize(b)
```

### 3.4 Handle errors

Raise `InvalidContractError` on invalid input, with a structured
`error_code` and a `context` dict. The Executor never sees an
invalid contract.

```python
raise InvalidContractError(
    "Field 'price' has unsupported type 'currency_code'",
    error_code="UNSUPPORTED_FIELD_TYPE",
    context={"field": "price", "type": "currency_code"},
)
```

Document the error codes your adapter raises in the adapter's
docstring.

### 3.5 Register the adapter

```python
import paxman

paxman.register_adapter(MyFormatAdapter())
```

Registering with an already-registered `format_id` raises
`InvalidContractError` (the registry uses the same error type for
all registration conflicts).

### 3.6 Write tests

At minimum:

- **Adaptation tests** — one per V1 `FieldType` you support.
- **Export round-trip** — `export(adapt(X))` is the same as `X`
  (within the expressible subset).
- **Invalid input** — one test per `error_code` you raise.
- **Property test** — `adapt(export(adapt(X))) == adapt(X)` for
  random valid `X`.

```python
def test_my_format_adapter_handles_simple_contract():
    adapter = MyFormatAdapter()
    external = load_fixture("my_format/simple.myf")
    canonical = adapter.adapt(external)
    # CanonicalContract.fields is a tuple of CanonicalField; walk it
    # by .path (the dotted field path) to find a specific field.
    name_field = next(f for f in canonical.fields if f.path == "name")
    assert name_field.type == FieldType.STRING
    assert name_field.required is True
```

Use `paxman.testing.contracts()` for property tests (it generates
random `CanonicalContract` instances).

### 3.7 Distribute

Publish the adapter as a separate PyPI package
(`paxman-myformat`) with a README that documents:

- The `format_id`.
- The supported V1 `FieldType` set.
- The error codes raised.
- An end-to-end example.

Use the `paxman-` prefix to make your package discoverable. Link
to Paxman's [EXTENDING.md](../../EXTENDING.md) for the SPI reference.

---

## 4. What adapters MUST do

- **Be pure** — same input → same `CanonicalContract`. No I/O, no
  clock, no random.
- **Raise `InvalidContractError`** on invalid input.
- **Preserve `MONEY` semantics** if the format supports monetary
  values (per [ADR-0004](../adr/0004-money-first-class-type.md)).
- **Map semantic tags** if the format supports metadata.
- **Validate before returning** — the adapter's output must be a
  valid `CanonicalContract` (use the standard validator).

## 5. What adapters MUST NOT do

- **Read raw input** — adapters only see contracts, not the data
  being normalized.
- **Invoke capabilities** — adapters only translate, never plan or
  execute.
- **Mutate global state** — adapters must be safe to use
  concurrently.
- **Embed provider secrets** — adapters don't talk to providers.

---

## 6. The full SPI walkthrough

For the full SPI walkthrough (including a longer example, the
`export()` semantics, and a worked Pydantic-style adapter), see
[EXTENDING.md §1](../../EXTENDING.md).

---

## 7. See also

- [EXTENDING.md §1](../../EXTENDING.md) — full SPI walkthrough.
- [docs/concepts/contracts.md](../concepts/contracts.md) — what
  a contract is in Paxman.
- [ADR-0007](../adr/0007-contract-adapter-set-v1.md) — V1 adapter
  set rationale.
- [paxman.protocols](../../EXTENDING.md) — the `ContractAdapter`
  Protocol (the SPI).
- [paxman.contract.canonical](../../EXTENDING.md) — the
  `CanonicalContract` data model.
- [paxman.contract.validator](../../EXTENDING.md) — the standard
  validator.

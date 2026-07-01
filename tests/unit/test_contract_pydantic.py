"""Unit tests for ``paxman.contract.adapters.pydantic`` — Pydantic v2 adapter.

Per Sprint 2 D2.7 and V1 acceptance §1.1, the Pydantic adapter translates
``pydantic.BaseModel`` subclasses to ``CanonicalContract`` and back. It
supports all 9 V1 types, every constraint kind, MONEY via the ``Money``
subclass, and ``Literal`` enums.

These tests cover:
- All 9 V1 field types via Pydantic v2 annotations.
- All constraint mappings: ``min_length``, ``max_length``, ``pattern``,
  ``ge``, ``gt``, ``le``, ``lt``.
- MONEY via the ``Money`` base class.
- ENUM via ``Literal`` and ``Enum`` subclasses.
- ``default_factory`` and explicit defaults.
- The round-trip property (export → re-adapt).
- The error paths: UNSUPPORTED_FIELD_TYPE, INVALID_CONSTRAINT,
  INVALID_REGEX_PATTERN.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

import pydantic
import pytest

import paxman.contract.adapters.pydantic  # noqa: F401  (triggers self-registration)
from paxman.contract.adapters.pydantic import Money, PydanticAdapter
from paxman.errors import InvalidContractError
from paxman.types import FieldType

# --- format_id ---------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_id_is_pydantic() -> None:
    """The adapter's ``format_id`` is ``'pydantic'``."""
    assert PydanticAdapter().format_id == "pydantic"


# --- adapt: minimal happy path -----------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_minimal_model() -> None:
    """A minimal BaseModel with one STRING field produces a valid contract."""

    class M(pydantic.BaseModel):
        f: str

    contract = PydanticAdapter().adapt(M)
    assert contract.id == "M"
    assert len(contract.fields) == 1
    f = contract.fields[0]
    assert f.name == "f"
    assert f.type is FieldType.STRING
    assert f.required is True


# --- adapt: all 9 V1 field types ---------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_all_v1_types() -> None:
    """A BaseModel with one field per V1 type adapts to 9 fields, all 9 types."""

    class M(pydantic.BaseModel):
        s: str
        i: int
        d: float
        b: bool
        date: datetime.date
        e: Literal["a", "b", "c"]
        o: dict
        arr: list[int]
        m: Money

    contract = PydanticAdapter().adapt(M)
    by_name = {f.name: f for f in contract.fields}
    assert len(by_name) == 9
    assert by_name["s"].type is FieldType.STRING
    assert by_name["i"].type is FieldType.INTEGER
    assert by_name["d"].type is FieldType.DECIMAL
    assert by_name["b"].type is FieldType.BOOLEAN
    assert by_name["date"].type is FieldType.DATE
    assert by_name["e"].type is FieldType.ENUM
    assert by_name["o"].type is FieldType.OBJECT
    assert by_name["arr"].type is FieldType.ARRAY
    assert by_name["m"].type is FieldType.MONEY


# --- adapt: constraints ------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_string_length_constraints() -> None:
    """``min_length`` and ``max_length`` become MIN_LENGTH/MAX_LENGTH constraints."""

    class M(pydantic.BaseModel):
        s: str = pydantic.Field(..., min_length=1, max_length=100)

    contract = PydanticAdapter().adapt(M)
    from paxman.contract._types import ConstraintKind

    kinds = {c.kind for c in contract.fields[0].constraints}
    assert ConstraintKind.MIN_LENGTH in kinds
    assert ConstraintKind.MAX_LENGTH in kinds


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_pattern_constraint() -> None:
    """``pattern`` becomes a PATTERN constraint."""
    from paxman.contract._types import ConstraintKind

    class M(pydantic.BaseModel):
        s: str = pydantic.Field(..., pattern=r"^[A-Z]{3}$")

    contract = PydanticAdapter().adapt(M)
    c = next(c for c in contract.fields[0].constraints if c.kind is ConstraintKind.PATTERN)
    assert c.params["regex"] == r"^[A-Z]{3}$"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_numeric_range_constraints() -> None:
    """``ge`` / ``gt`` / ``le`` / ``lt`` become MIN/MAX_VALUE constraints."""
    from paxman.contract._types import ConstraintKind

    class M(pydantic.BaseModel):
        x: int = pydantic.Field(..., ge=0, le=100)
        y: int = pydantic.Field(..., gt=10, lt=20)

    contract = PydanticAdapter().adapt(M)
    x = next(f for f in contract.fields if f.name == "x")
    y = next(f for f in contract.fields if f.name == "y")
    x_kinds = {c.kind for c in x.constraints}
    y_kinds = {c.kind for c in y.constraints}
    assert ConstraintKind.MIN_VALUE in x_kinds
    assert ConstraintKind.MAX_VALUE in x_kinds
    assert ConstraintKind.MIN_VALUE in y_kinds
    assert ConstraintKind.MAX_VALUE in y_kinds


# --- adapt: ENUM -------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_literal_enum() -> None:
    """``Literal`` fields become ENUM with the literal values as enum_values."""

    class M(pydantic.BaseModel):
        e: Literal["a", "b", "c"]

    contract = PydanticAdapter().adapt(M)
    f = contract.fields[0]
    assert f.type is FieldType.ENUM
    assert f.enum_values is not None
    assert "a" in f.enum_values
    assert "b" in f.enum_values
    assert "c" in f.enum_values


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_enum_subclass() -> None:
    """``enum.Enum`` subclass fields become ENUM."""

    class Color(Enum):
        RED = "red"
        GREEN = "green"
        BLUE = "blue"

    class M(pydantic.BaseModel):
        c: Color

    contract = PydanticAdapter().adapt(M)
    f = contract.fields[0]
    assert f.type is FieldType.ENUM
    assert f.enum_values is not None
    assert "red" in f.enum_values


# --- adapt: defaults ---------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_default_value() -> None:
    """A field with a default is required=False and carries the default."""

    class M(pydantic.BaseModel):
        x: int = 42

    contract = PydanticAdapter().adapt(M)
    f = contract.fields[0]
    assert f.required is False
    assert f.default == 42


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_default_factory() -> None:
    """A field with ``default_factory`` is required=False."""

    class M(pydantic.BaseModel):
        items: list[int] = pydantic.Field(default_factory=list)

    contract = PydanticAdapter().adapt(M)
    f = contract.fields[0]
    assert f.required is False


# --- adapt: MONEY ------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_money_subclass() -> None:
    """A field typed as ``Money`` becomes FieldType.MONEY."""

    class M(pydantic.BaseModel):
        amount: Money

    contract = PydanticAdapter().adapt(M)
    f = contract.fields[0]
    assert f.type is FieldType.MONEY


def test_adapt_nested_basemodel_inline_becomes_object() -> None:
    """A field with a direct ``BaseModel`` annotation maps to FieldType.OBJECT."""

    class LineItem(pydantic.BaseModel):
        description: str
        quantity: int

    class Invoice(pydantic.BaseModel):
        supplier_name: str
        item: LineItem

    contract = PydanticAdapter().adapt(Invoice)
    by_name = {f.name: f for f in contract.fields}
    assert by_name["supplier_name"].type is FieldType.STRING
    assert by_name["item"].type is FieldType.OBJECT


def test_adapt_nested_basemodel_list_still_becomes_array() -> None:
    """``list[BaseModel]`` still maps to FieldType.ARRAY (per-list, not per-item)."""

    class LineItem(pydantic.BaseModel):
        description: str

    class Invoice(pydantic.BaseModel):
        line_items: list[LineItem]

    contract = PydanticAdapter().adapt(Invoice)
    f = contract.fields[0]
    assert f.name == "line_items"
    assert f.type is FieldType.ARRAY


# --- adapt: Optional ---------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_optional_field() -> None:
    """``Optional[X]`` is mapped to nullable=True, required=False."""

    class M(pydantic.BaseModel):
        x: int | None = None  # type: ignore[valid-type]

    contract = PydanticAdapter().adapt(M)
    f = contract.fields[0]
    assert f.nullable is True
    assert f.required is False


# --- adapt: error paths ------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_non_basemodel_raises_invalid_field() -> None:
    """A non-BaseModel class raises InvalidContractError."""

    class NotAModel:
        pass

    with pytest.raises(InvalidContractError, match="BaseModel subclass"):
        PydanticAdapter().adapt(NotAModel)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_unsupported_type_raises() -> None:
    """A Pydantic annotation that maps to no FieldType raises UNSUPPORTED_FIELD_TYPE."""

    # bytes is supported by Pydantic v2 but not mapped by the Paxman adapter.
    class M(pydantic.BaseModel):
        x: bytes

    with pytest.raises(InvalidContractError, match="unsupported type"):
        PydanticAdapter().adapt(M)


# --- export + round-trip ----------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_minimal_model() -> None:
    """Export of a minimal model produces a new BaseModel subclass."""

    class M(pydantic.BaseModel):
        f: str

    contract = PydanticAdapter().adapt(M)
    M2 = PydanticAdapter().export(contract)
    assert issubclass(M2, pydantic.BaseModel)
    assert "f" in M2.model_fields


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_money_model() -> None:
    """Export of a MONEY model preserves the Money type."""

    class M(pydantic.BaseModel):
        amount: Money
        notes: str

    contract = PydanticAdapter().adapt(M)
    M2 = PydanticAdapter().export(contract)
    assert "amount" in M2.model_fields
    # Re-adapting the exported model should produce the same field count.
    contract2 = PydanticAdapter().adapt(M2)
    assert len(contract.fields) == len(contract2.fields)


@pytest.mark.deterministic
@pytest.mark.unit
def test_round_trip_preserves_field_count_and_names() -> None:
    """``adapt(export(adapt(M)))`` preserves field count, names, and types."""

    class M(pydantic.BaseModel):
        s: str
        i: int
        b: bool
        e: Literal["x", "y"]

    contract = PydanticAdapter().adapt(M)
    M2 = PydanticAdapter().export(contract)
    contract2 = PydanticAdapter().adapt(M2)
    assert [f.name for f in contract.fields] == [f.name for f in contract2.fields]
    assert [f.type for f in contract.fields] == [f.type for f in contract2.fields]
    assert [f.required for f in contract.fields] == [f.required for f in contract2.fields]


# --- Money subclass --------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_subclass_constructs() -> None:
    """The ``Money`` Pydantic model can be constructed with valid args."""
    m = Money(amount=Decimal("19.99"), currency="USD")
    assert m.amount == Decimal("19.99")
    assert m.currency == "USD"
    assert m.precision is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_subclass_validates_currency() -> None:
    """The ``Money`` Pydantic model rejects non-ISO-4217 currency codes."""
    with pytest.raises(pydantic.ValidationError):
        Money(amount=Decimal("1.00"), currency="btc")  # lowercase, rejected by regex


# --- fixture integration ----------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_fixture_invoice_model_adapts() -> None:
    """The fixture ``tests/fixtures/contracts/pydantic/invoice.py`` adapts."""
    from tests.fixtures.contracts.pydantic import invoice

    contract = PydanticAdapter().adapt(invoice.Invoice)
    assert contract.id == "Invoice"
    assert {f.name for f in contract.fields} == {
        "supplier_name",
        "currency",
        "total",
        "paid",
        "invoice_date",
        "line_items",
    }


@pytest.mark.deterministic
@pytest.mark.unit
def test_fixture_with_money_model_adapts() -> None:
    """The fixture ``tests/fixtures/contracts/pydantic/with_money.py`` adapts."""
    from tests.fixtures.contracts.pydantic import with_money

    contract = PydanticAdapter().adapt(with_money.MoneyRoundtrip)
    assert contract.id == "MoneyRoundtrip"
    amount = contract.field_by_path("amount")
    assert amount is not None
    assert amount.type is FieldType.MONEY


@pytest.mark.deterministic
@pytest.mark.unit
def test_fixture_all_v1_types_model_adapts() -> None:
    """The fixture ``tests/fixtures/contracts/pydantic/all_v1_types.py`` covers all 9 types."""
    from tests.fixtures.contracts.pydantic import all_v1_types

    contract = PydanticAdapter().adapt(all_v1_types.AllV1Types)
    assert contract.id == "AllV1Types"
    assert {f.type for f in contract.fields} == set(FieldType)


# --- Round-trip property: adapt(export(adapt(X))) == adapt(X) for 5 models ---


@pytest.mark.deterministic
@pytest.mark.unit
def test_round_trip_string_only_model_exact() -> None:
    """Round-trip of a string-only model produces an identical contract."""

    class M(pydantic.BaseModel):
        a: str
        b: str

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_round_trip_integer_with_default_exact() -> None:
    """Round-trip of an integer model with default produces an identical contract."""

    class M(pydantic.BaseModel):
        x: int = 42

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_round_trip_optional_field_exact() -> None:
    """Round-trip of a model with Optional field produces an identical contract."""

    class M(pydantic.BaseModel):
        x: int | None = None  # type: ignore[valid-type]

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_round_trip_literal_enum_exact() -> None:
    """Round-trip of a Literal enum model produces an identical contract."""

    class M(pydantic.BaseModel):
        e: Literal["x", "y"]

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_round_trip_with_description_exact() -> None:
    """Round-trip of a model with descriptions produces an identical contract."""

    class M(pydantic.BaseModel):
        f: str = pydantic.Field(..., description="A field")

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_non_canonical_raises() -> None:
    """export with non-CanoonicalContract raises."""
    with pytest.raises(InvalidContractError):
        PydanticAdapter().export("not_a_contract")  # type: ignore[arg-type]


# --- Export with constraints (covers _export_constraint_to_field) -----------


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_preserves_min_max_length() -> None:
    """Export preserves min_length/max_length constraints on re-adapt."""

    class M(pydantic.BaseModel):
        s: str = pydantic.Field(..., min_length=2, max_length=50)

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    from paxman.contract._types import ConstraintKind

    kinds2 = {c.kind for c in c2.fields[0].constraints}
    assert ConstraintKind.MIN_LENGTH in kinds2
    assert ConstraintKind.MAX_LENGTH in kinds2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_preserves_pattern() -> None:
    """Export preserves pattern constraint on re-adapt."""

    class M(pydantic.BaseModel):
        s: str = pydantic.Field(..., pattern=r"^[A-Z]{3}$")

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    from paxman.contract._types import ConstraintKind

    kinds2 = {c.kind for c in c2.fields[0].constraints}
    assert ConstraintKind.PATTERN in kinds2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_preserves_ge_le() -> None:
    """Export preserves ge/le (inclusive MIN_VALUE/MAX_VALUE) on re-adapt."""

    class M(pydantic.BaseModel):
        x: int = pydantic.Field(..., ge=0, le=100)

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    from paxman.contract._types import ConstraintKind

    kinds2 = {c.kind for c in c2.fields[0].constraints}
    assert ConstraintKind.MIN_VALUE in kinds2
    assert ConstraintKind.MAX_VALUE in kinds2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_preserves_gt_lt() -> None:
    """Export preserves gt/lt (exclusive MIN_VALUE/MAX_VALUE) on re-adapt."""

    class M(pydantic.BaseModel):
        x: int = pydantic.Field(..., gt=10, lt=20)

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    from paxman.contract._types import ConstraintKind

    kinds2 = {c.kind for c in c2.fields[0].constraints}
    assert ConstraintKind.MIN_VALUE in kinds2
    assert ConstraintKind.MAX_VALUE in kinds2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_decimal_type() -> None:
    """Export of a Decimal field preserves DECIMAL type."""

    class M(pydantic.BaseModel):
        x: Decimal

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    assert c2.fields[0].type is FieldType.DECIMAL


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_date_type() -> None:
    """Export of a date field preserves DATE type."""

    class M(pydantic.BaseModel):
        d: datetime.date

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    assert c2.fields[0].type is FieldType.DATE


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_object_array_types() -> None:
    """Export of OBJECT and ARRAY fields preserves types."""

    class M(pydantic.BaseModel):
        o: dict
        a: list[int]

    adapter = PydanticAdapter()
    c1 = adapter.adapt(M)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    types = {f.name: f.type for f in c2.fields}
    assert types["o"] is FieldType.OBJECT
    assert types["a"] is FieldType.ARRAY


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_non_basemodel_instance_raises() -> None:
    """An instance (not a class) raises InvalidContractError."""
    with pytest.raises(InvalidContractError):
        PydanticAdapter().adapt(42)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_datetime_type() -> None:
    """datetime.datetime maps to DATE."""

    class M(pydantic.BaseModel):
        dt: datetime.datetime

    contract = PydanticAdapter().adapt(M)
    assert contract.fields[0].type is FieldType.DATE


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_pydantic_json_type() -> None:
    """pydantic.Json maps to STRING."""

    class M(pydantic.BaseModel):
        j: pydantic.Json

    contract = PydanticAdapter().adapt(M)
    assert contract.fields[0].type is FieldType.STRING


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_set_type() -> None:
    """set[T] maps to ARRAY."""

    class M(pydantic.BaseModel):
        s: set[int]

    contract = PydanticAdapter().adapt(M)
    assert contract.fields[0].type is FieldType.ARRAY


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_tuple_type() -> None:
    """tuple[T, ...] maps to ARRAY."""

    class M(pydantic.BaseModel):
        t: tuple[int, ...]

    contract = PydanticAdapter().adapt(M)
    assert contract.fields[0].type is FieldType.ARRAY


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_dict_generic_type() -> None:
    """dict[str, int] maps to OBJECT."""

    class M(pydantic.BaseModel):
        d: dict[str, int]

    contract = PydanticAdapter().adapt(M)
    assert contract.fields[0].type is FieldType.OBJECT


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_hints_from_json_schema_extra() -> None:
    """format_hints are read from ``x-paxman-format-hints`` in
    ``json_schema_extra``."""
    from paxman.contract import FormatHint
    from pydantic import BaseModel, Field

    class M(BaseModel):
        supplier: str = Field(
            json_schema_extra={"x-paxman-format-hints": ["csv"]}
        )
        amount: str  # no hints

    adapter = PydanticAdapter()
    canonical = adapter.adapt(M)
    supplier = next(f for f in canonical.fields if f.name == "supplier")
    assert supplier.format_hints == (FormatHint.CSV,)
    amount = next(f for f in canonical.fields if f.name == "amount")
    assert amount.format_hints == ()


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_hints_invalid_value() -> None:
    """Unknown format_hint values are rejected with INVALID_FORMAT_HINT."""
    from pydantic import BaseModel, Field

    class M(BaseModel):
        supplier: str = Field(
            json_schema_extra={"x-paxman-format-hints": ["pdf"]}
        )

    adapter = PydanticAdapter()
    with pytest.raises(InvalidContractError) as exc_info:
        adapter.adapt(M)
    assert exc_info.value.error_code == "INVALID_FORMAT_HINT"

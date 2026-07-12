"""Unit tests for explicit contract parse metadata."""

from __future__ import annotations

import attrs
import pytest

from paxman.contract._parse import ParseValidationError, parse_spec
from paxman.types import FieldType

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Happy-path: each supported kind for its matching field type
# ---------------------------------------------------------------------------


def test_parse_spec_returns_none_when_raw_is_none() -> None:
    """An absent parse declaration is represented as None."""
    assert parse_spec(None, field_name="total", field_type=FieldType.DECIMAL) is None


def test_parse_spec_accepts_decimal_for_decimal_field() -> None:
    """A declared decimal parser retains its kind."""
    spec = parse_spec({"kind": "decimal"}, field_name="total", field_type=FieldType.DECIMAL)
    assert spec is not None
    assert spec.kind == "decimal"
    assert spec.config == {}


def test_parse_spec_accepts_integer_for_integer_field() -> None:
    """A declared integer parser retains its kind."""
    spec = parse_spec({"kind": "integer"}, field_name="count", field_type=FieldType.INTEGER)
    assert spec is not None
    assert spec.kind == "integer"
    assert spec.config == {}


def test_parse_spec_accepts_boolean_with_explicit_token_sets() -> None:
    """Boolean parsing requires closed true/false token mappings."""
    spec = parse_spec(
        {"kind": "boolean", "true_values": ["yes", "y"], "false_values": ["no", "n"]},
        field_name="active",
        field_type=FieldType.BOOLEAN,
    )
    assert spec is not None
    assert spec.kind == "boolean"
    assert spec.config["true_values"] == ["yes", "y"]
    assert spec.config["false_values"] == ["no", "n"]


def test_parse_spec_accepts_date_with_strptime_format() -> None:
    """Date parsing requires an explicit strptime format string."""
    spec = parse_spec(
        {"kind": "date", "format": "%Y-%m-%d"},
        field_name="created_at",
        field_type=FieldType.DATE,
    )
    assert spec is not None
    assert spec.kind == "date"
    assert spec.config["format"] == "%Y-%m-%d"


# ---------------------------------------------------------------------------
# Negative: type/kind mismatches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        {"kind": "date"},
        {"kind": "integer"},
        {"kind": "boolean", "true_values": ["t"], "false_values": ["f"]},
    ],
)
def test_parse_spec_rejects_kind_for_wrong_field_type(raw: object) -> None:
    """A parser kind that doesn't match the field type is rejected."""
    with pytest.raises(ParseValidationError):
        parse_spec(raw, field_name="total", field_type=FieldType.DECIMAL)


@pytest.mark.parametrize(
    ("raw", "field_type"),
    [
        ({"kind": "decimal"}, FieldType.INTEGER),
        ({"kind": "decimal"}, FieldType.BOOLEAN),
        ({"kind": "decimal"}, FieldType.DATE),
        ({"kind": "decimal"}, FieldType.STRING),
    ],
)
def test_parse_spec_rejects_decimal_kind_for_non_decimal_types(
    raw: object, field_type: FieldType
) -> None:
    """Decimal kind is only valid for DECIMAL fields."""
    with pytest.raises(ParseValidationError):
        parse_spec(raw, field_name="x", field_type=field_type)


@pytest.mark.parametrize(
    ("raw", "field_type"),
    [
        ({"kind": "integer"}, FieldType.DECIMAL),
        ({"kind": "integer"}, FieldType.STRING),
        ({"kind": "integer"}, FieldType.BOOLEAN),
        ({"kind": "integer"}, FieldType.DATE),
    ],
)
def test_parse_spec_rejects_integer_kind_for_non_integer_types(
    raw: object, field_type: FieldType
) -> None:
    """Integer kind is only valid for INTEGER fields."""
    with pytest.raises(ParseValidationError):
        parse_spec(raw, field_name="x", field_type=field_type)


# ---------------------------------------------------------------------------
# Negative: missing required config keys
# ---------------------------------------------------------------------------


def test_parse_spec_rejects_boolean_without_true_values() -> None:
    """Boolean parse requires true_values."""
    with pytest.raises(ParseValidationError):
        parse_spec(
            {"kind": "boolean", "false_values": ["no"]},
            field_name="active",
            field_type=FieldType.BOOLEAN,
        )


def test_parse_spec_rejects_boolean_without_false_values() -> None:
    """Boolean parse requires false_values."""
    with pytest.raises(ParseValidationError):
        parse_spec(
            {"kind": "boolean", "true_values": ["yes"]},
            field_name="active",
            field_type=FieldType.BOOLEAN,
        )


def test_parse_spec_rejects_boolean_with_overlapping_tokens() -> None:
    """true_values and false_values must be disjoint."""
    with pytest.raises(ParseValidationError):
        parse_spec(
            {"kind": "boolean", "true_values": ["yes", "no"], "false_values": ["no", "yes"]},
            field_name="active",
            field_type=FieldType.BOOLEAN,
        )


def test_parse_spec_rejects_date_without_format() -> None:
    """Date parse requires a format string."""
    with pytest.raises(ParseValidationError):
        parse_spec({"kind": "date"}, field_name="created_at", field_type=FieldType.DATE)


def test_parse_spec_rejects_unknown_kind() -> None:
    """An unknown kind string is rejected."""
    with pytest.raises(ParseValidationError):
        parse_spec({"kind": "money"}, field_name="total", field_type=FieldType.DECIMAL)


def test_parse_spec_rejects_non_mapping_input() -> None:
    """A non-dict raw value is rejected."""
    with pytest.raises(ParseValidationError):
        parse_spec("decimal", field_name="total", field_type=FieldType.DECIMAL)


# ---------------------------------------------------------------------------
# Negative: extraction_step is required when parse is present
# ---------------------------------------------------------------------------


def test_canonical_field_requires_extraction_when_parse_present() -> None:
    """A field with parse_spec but no extraction_step is invalid."""
    spec = parse_spec({"kind": "decimal"}, field_name="total", field_type=FieldType.DECIMAL)
    assert spec is not None
    with pytest.raises(ValueError, match="extraction_step"):
        from paxman.contract.canonical import CanonicalField

        CanonicalField(
            id="field_total",
            path="total",
            name="total",
            type=FieldType.DECIMAL,
            required=True,
            parse_spec=spec,
            # extraction_step is intentionally omitted
        )


# ---------------------------------------------------------------------------
# ParseSpec immutability
# ---------------------------------------------------------------------------


def test_parse_spec_is_frozen() -> None:
    """ParseSpec is an immutable frozen attrs instance."""
    spec = parse_spec({"kind": "integer"}, field_name="count", field_type=FieldType.INTEGER)
    assert spec is not None
    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        spec.kind = "decimal"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ParseSpec to_wire round-trip
# ---------------------------------------------------------------------------


def test_parse_spec_to_wire_decimal() -> None:
    """to_wire returns the stable contract wire form."""
    spec = parse_spec({"kind": "decimal"}, field_name="total", field_type=FieldType.DECIMAL)
    assert spec is not None
    assert spec.to_wire() == {"kind": "decimal"}


def test_parse_spec_to_wire_boolean() -> None:
    """to_wire includes config for boolean."""
    spec = parse_spec(
        {"kind": "boolean", "true_values": ["yes"], "false_values": ["no"]},
        field_name="active",
        field_type=FieldType.BOOLEAN,
    )
    assert spec is not None
    wire = spec.to_wire()
    assert wire["kind"] == "boolean"
    assert wire["true_values"] == ["yes"]
    assert wire["false_values"] == ["no"]

"""Unit tests for ``paxman.contract.adapters.json_schema`` — JSON Schema adapter.

Per Sprint 2 D2.8 and V1 acceptance §1.1, the JSON Schema adapter
translates JSON Schema (draft 2020-12, with earlier-draft best-effort)
to ``CanonicalContract`` and back. It handles all 9 V1 types, every
constraint mapping (``minLength``/``maxLength``, ``pattern``,
``minimum``/``maximum``/``exclusiveMinimum``/``exclusiveMaximum``,
``minItems``/``maxItems``, ``enum``), and the MONEY representation
via the ``x-paxman-type`` extension.

These tests cover all 9 V1 types, all constraint keywords from the
sprint's exit-criteria list, and the round-trip property.
"""

from __future__ import annotations

import json

import pytest

import paxman.contract.adapters.json_schema  # noqa: F401  (triggers self-registration)
from paxman.contract.adapters.json_schema import JsonSchemaAdapter
from paxman.errors import InvalidContractError
from paxman.types import FieldType

# --- format_id ---------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_id_is_json_schema_draft_2020_12() -> None:
    """The adapter's ``format_id`` is ``'json_schema:draft-2020-12'``."""
    assert JsonSchemaAdapter().format_id == "json_schema:draft-2020-12"


# --- adapt: all 9 V1 types ---------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_all_v1_types() -> None:
    """A schema with one property per V1 type adapts to 9 fields covering all types."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "AllTypes",
        "type": "object",
        "properties": {
            "s": {"type": "string"},
            "i": {"type": "integer"},
            "d": {"type": "number"},
            "b": {"type": "boolean"},
            "date": {"type": "string", "format": "date"},
            "e": {"type": "string", "enum": ["a", "b", "c"]},
            "o": {"type": "object"},
            "arr": {"type": "array", "items": {"type": "integer"}},
            "m": {
                "x-paxman-type": "MONEY",
                "type": "object",
                "properties": {
                    "amount": {"type": "string"},
                    "currency": {"type": "string"},
                },
                "required": ["amount", "currency"],
            },
        },
        "required": ["s", "i", "d", "b", "date", "e", "o", "arr", "m"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
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


# --- adapt: constraints -----------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_string_length_constraints() -> None:
    """``minLength`` and ``maxLength`` map to MIN_LENGTH/MAX_LENGTH constraints."""
    from paxman.contract._types import ConstraintKind

    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "s": {"type": "string", "minLength": 1, "maxLength": 100},
        },
        "required": ["s"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    f = contract.fields[0]
    kinds = {c.kind for c in f.constraints}
    assert ConstraintKind.MIN_LENGTH in kinds
    assert ConstraintKind.MAX_LENGTH in kinds


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_pattern_constraint() -> None:
    """``pattern`` maps to a PATTERN constraint."""
    from paxman.contract._types import ConstraintKind

    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "s": {"type": "string", "pattern": r"^[A-Z]{3}$"},
        },
        "required": ["s"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    c = next(c for c in contract.fields[0].constraints if c.kind is ConstraintKind.PATTERN)
    assert c.params["regex"] == r"^[A-Z]{3}$"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_numeric_range_constraints() -> None:
    """``minimum``/``maximum`` and ``exclusiveMinimum``/``exclusiveMaximum`` map to MIN/MAX_VALUE."""
    from paxman.contract._types import ConstraintKind

    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "i": {"type": "integer", "minimum": 0, "maximum": 100},
            "j": {"type": "integer", "exclusiveMinimum": 0, "exclusiveMaximum": 100},
        },
        "required": ["i", "j"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    by_name = {f.name: f for f in contract.fields}
    i_kinds = {c.kind for c in by_name["i"].constraints}
    j_kinds = {c.kind for c in by_name["j"].constraints}
    assert ConstraintKind.MIN_VALUE in i_kinds
    assert ConstraintKind.MAX_VALUE in i_kinds
    assert ConstraintKind.MIN_VALUE in j_kinds
    assert ConstraintKind.MAX_VALUE in j_kinds


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_array_items_constraints() -> None:
    """``minItems`` / ``maxItems`` map to MIN_LENGTH/MAX_LENGTH on ARRAY."""
    from paxman.contract._types import ConstraintKind

    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "arr": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 1,
                "maxItems": 10,
            },
        },
        "required": ["arr"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    f = contract.fields[0]
    kinds = {c.kind for c in f.constraints}
    assert ConstraintKind.MIN_LENGTH in kinds
    assert ConstraintKind.MAX_LENGTH in kinds


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_required_list() -> None:
    """Properties in the ``required`` list are marked required=True."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "string"},
        },
        "required": ["a"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    by_name = {f.name: f for f in contract.fields}
    assert by_name["a"].required is True
    assert by_name["b"].required is False


# --- adapt: MONEY ------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_money_via_x_paxman_type() -> None:
    """A property with ``x-paxman-type: MONEY`` becomes FieldType.MONEY."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "amount": {
                "x-paxman-type": "MONEY",
                "type": "object",
                "properties": {
                    "amount": {"type": "string"},
                    "currency": {"type": "string"},
                },
                "required": ["amount", "currency"],
            },
        },
        "required": ["amount"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    assert contract.fields[0].type is FieldType.MONEY


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_money_with_default() -> None:
    """A MONEY property with a default produces a MoneyValue default."""
    from decimal import Decimal

    from paxman.contract.canonical import MoneyValue

    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "amount": {
                "x-paxman-type": "MONEY",
                "type": "object",
                "properties": {
                    "amount": {"type": "string"},
                    "currency": {"type": "string"},
                },
                "required": ["amount", "currency"],
                "default": {"amount": "19.99", "currency": "USD"},
            },
        },
        "required": ["amount"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    assert contract.fields[0].default == MoneyValue(amount=Decimal("19.99"), currency="USD")


# --- adapt: error paths -----------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_non_dict_raises_invalid_field() -> None:
    """A non-dict input raises InvalidContractError.

    Strings that are not valid JSON raise ``INVALID_JSON``; a
    non-dict/non-str input raises ``INVALID_FIELD`` with a message
    containing ``"requires a dict or str"``.
    """
    with pytest.raises(InvalidContractError, match="requires a dict or str"):
        JsonSchemaAdapter().adapt(123)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_string_schema_parses_json() -> None:
    """A JSON-encoded string schema is parsed and adapted.

    Per the API design, ``paxman.normalize()`` may receive a string
    contract (e.g., the contents of a JSON Schema file). The
    adapter parses the string as JSON before translation.
    """
    schema = {
        "title": "StringSchema",
        "type": "object",
        "properties": {"s": {"type": "string"}},
        "required": ["s"],
    }
    canonical = JsonSchemaAdapter().adapt(json.dumps(schema))
    assert canonical.id == "StringSchema"
    assert len(canonical.fields) == 1
    assert canonical.fields[0].path == "s"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_invalid_json_string_raises_invalid_json() -> None:
    """A string that is not valid JSON raises ``INVALID_JSON``."""
    with pytest.raises(InvalidContractError, match="not valid JSON"):
        JsonSchemaAdapter().adapt("not a schema")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_unsupported_type_raises() -> None:
    """A property with an unsupported type raises UNSUPPORTED_FIELD_TYPE."""
    # "null" is supported as nullable; let's try a truly unsupported type.
    schema2 = {
        "title": "x",
        "type": "object",
        "properties": {
            "f": {"type": "not_a_real_type"},
        },
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError, match="unsupported type"):
        JsonSchemaAdapter().adapt(schema2)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_top_level_not_object_raises() -> None:
    """A top-level schema that is not ``object`` raises UNSUPPORTED_FIELD_TYPE."""
    schema = {
        "title": "x",
        "type": "string",
    }
    with pytest.raises(InvalidContractError, match="must be 'object'"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_invalid_version_raises() -> None:
    """An unrecognized ``$schema`` raises InvalidContractError."""
    schema = {
        "$schema": "https://json-schema.org/draft/9999-99/schema",
        "title": "x",
        "type": "object",
        "properties": {"f": {"type": "string"}},
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError, match="unsupported JSON Schema version"):
        JsonSchemaAdapter().adapt(schema)


# --- export + round-trip ---------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_minimal_schema() -> None:
    """Export of a minimal contract produces a valid JSON Schema dict."""
    from paxman.contract.canonical import CanonicalContract, CanonicalField
    from paxman.types import FieldType

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.STRING,
        required=True,
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert out["title"] == "x"
    assert out["type"] == "object"
    assert "f" in out["properties"]


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_money_field() -> None:
    """A MONEY field is exported with ``x-paxman-type: MONEY``."""
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="amount",
        name="amount",
        type=FieldType.MONEY,
        required=True,
    )
    contract = CanonicalContract(id="money", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["amount"]["x-paxman-type"] == "MONEY"


@pytest.mark.deterministic
@pytest.mark.unit
def test_round_trip_preserves_structure() -> None:
    """``adapt(export(adapt(schema)))`` preserves field count, names, types."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "rt",
        "type": "object",
        "properties": {
            "s": {"type": "string", "minLength": 1, "maxLength": 10},
            "i": {"type": "integer", "minimum": 0},
            "b": {"type": "boolean"},
        },
        "required": ["s", "i", "b"],
    }
    adapter = JsonSchemaAdapter()
    c1 = adapter.adapt(schema)
    out = adapter.export(c1)
    c2 = adapter.adapt(out)
    assert [f.name for f in c1.fields] == [f.name for f in c2.fields]
    assert [f.type for f in c1.fields] == [f.type for f in c2.fields]


# --- fixture integration ---------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_fixture_invoice_json_adapts() -> None:
    """The fixture ``tests/fixtures/contracts/json_schema/invoice.json`` adapts."""
    import json
    import pathlib

    schema = json.loads(
        pathlib.Path("tests/fixtures/contracts/json_schema/invoice.json").read_text()
    )
    contract = JsonSchemaAdapter().adapt(schema)
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
def test_fixture_with_money_json_adapts() -> None:
    """The fixture ``tests/fixtures/contracts/json_schema/with_money.json`` adapts."""
    import json
    import pathlib

    schema = json.loads(
        pathlib.Path("tests/fixtures/contracts/json_schema/with_money.json").read_text()
    )
    contract = JsonSchemaAdapter().adapt(schema)
    assert contract.id == "MoneyRoundtrip"
    assert contract.fields[0].type is FieldType.MONEY


@pytest.mark.deterministic
@pytest.mark.unit
def test_fixture_all_v1_types_json_adapts() -> None:
    """The fixture ``tests/fixtures/contracts/json_schema/all_v1_types.json`` covers all 9 types."""
    import json
    import pathlib

    schema = json.loads(
        pathlib.Path("tests/fixtures/contracts/json_schema/all_v1_types.json").read_text()
    )
    contract = JsonSchemaAdapter().adapt(schema)
    assert contract.id == "AllV1Types"
    assert {f.type for f in contract.fields} == set(FieldType)


# --- Additional constraint and error tests ----------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_invalid_minlength_raises() -> None:
    """A non-int minLength raises INVALID_CONSTRAINT."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"s": {"type": "string", "minLength": "not_int"}},
        "required": ["s"],
    }
    with pytest.raises(InvalidContractError, match=r"minLength.*non-negative int"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_invalid_maxlength_raises() -> None:
    """A negative maxLength raises INVALID_CONSTRAINT."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"s": {"type": "string", "maxLength": -1}},
        "required": ["s"],
    }
    with pytest.raises(InvalidContractError, match=r"maxLength.*non-negative int"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_invalid_pattern_raises() -> None:
    """An invalid regex pattern raises INVALID_CONSTRAINT."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"s": {"type": "string", "pattern": "[unclosed"}},
        "required": ["s"],
    }
    with pytest.raises(InvalidContractError, match=r"pattern.*invalid"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_non_dict_pattern_raises() -> None:
    """A non-string pattern raises INVALID_CONSTRAINT."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"s": {"type": "string", "pattern": 123}},
        "required": ["s"],
    }
    with pytest.raises(InvalidContractError, match=r"pattern.*must be a string"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_enum_detection() -> None:
    """A property with 'enum' keyword is detected as ENUM type."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"e": {"type": "string", "enum": ["a", "b", "c"]}},
        "required": ["e"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    f = contract.fields[0]
    assert f.type is FieldType.ENUM
    assert f.enum_values is not None
    assert "a" in f.enum_values
    assert "b" in f.enum_values


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_null_type_is_nullable_string() -> None:
    """A 'null' type property is mapped to nullable STRING."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"n": {"type": "null"}},
    }
    contract = JsonSchemaAdapter().adapt(schema)
    f = contract.fields[0]
    assert f.nullable is True
    assert f.required is False


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_date_time_format() -> None:
    """A string with format='date-time' maps to DATE."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"dt": {"type": "string", "format": "date-time"}},
        "required": ["dt"],
    }
    contract = JsonSchemaAdapter().adapt(schema)
    assert contract.fields[0].type is FieldType.DATE


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_no_properties_raises() -> None:
    """A schema with no properties raises INVALID_FIELD."""
    schema = {"title": "x", "type": "object", "properties": {}}
    with pytest.raises(InvalidContractError, match="no properties"):
        JsonSchemaAdapter().adapt(schema)


# --- export: ENUM, DATE, round-trip -----------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_enum_field() -> None:
    """An ENUM field is exported with 'enum' keyword."""
    from paxman.contract._types import EnumValueSet
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="status",
        name="status",
        type=FieldType.ENUM,
        required=True,
        enum_values=EnumValueSet(("active", "inactive")),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    prop = out["properties"]["status"]
    assert "enum" in prop
    assert "active" in prop["enum"]


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_date_field() -> None:
    """A DATE field is exported with format='date'."""
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="dt",
        name="dt",
        type=FieldType.DATE,
        required=True,
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    prop = out["properties"]["dt"]
    assert prop["type"] == "string"
    assert prop["format"] == "date"


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_round_trip_exact_string_integer() -> None:
    """Round-trip of string+integer schema produces identical contract."""
    schema = {
        "title": "rt1",
        "type": "object",
        "properties": {
            "s": {"type": "string"},
            "i": {"type": "integer"},
        },
        "required": ["s", "i"],
    }
    adapter = JsonSchemaAdapter()
    c1 = adapter.adapt(schema)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_round_trip_exact_with_constraints() -> None:
    """Round-trip with constraints produces identical contract."""
    schema = {
        "title": "rt2",
        "type": "object",
        "properties": {
            "s": {"type": "string", "minLength": 1, "maxLength": 100, "pattern": "^[A-Z]+$"},
            "i": {"type": "integer", "minimum": 0, "maximum": 99},
        },
        "required": ["s", "i"],
    }
    adapter = JsonSchemaAdapter()
    c1 = adapter.adapt(schema)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_round_trip_exact_boolean() -> None:
    """Round-trip of boolean-only schema produces identical contract."""
    schema = {
        "title": "rt3",
        "type": "object",
        "properties": {"b": {"type": "boolean"}},
        "required": ["b"],
    }
    adapter = JsonSchemaAdapter()
    c1 = adapter.adapt(schema)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_round_trip_exact_enum() -> None:
    """Round-trip of ENUM schema produces identical contract."""
    schema = {
        "title": "rt4",
        "type": "object",
        "properties": {"e": {"type": "string", "enum": ["a", "b"]}},
        "required": ["e"],
    }
    adapter = JsonSchemaAdapter()
    c1 = adapter.adapt(schema)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_round_trip_exact_date() -> None:
    """Round-trip of DATE schema produces identical contract."""
    schema = {
        "title": "rt5",
        "type": "object",
        "properties": {"d": {"type": "string", "format": "date"}},
        "required": ["d"],
    }
    adapter = JsonSchemaAdapter()
    c1 = adapter.adapt(schema)
    c2 = adapter.adapt(adapter.export(c1))
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_non_canonical_raises() -> None:
    """export with non-CanoonicalContract raises."""
    with pytest.raises(InvalidContractError):
        JsonSchemaAdapter().export("not_a_contract")  # type: ignore[arg-type]


# --- Additional coverage tests ----------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_non_dict_properties_raises() -> None:
    """Non-dict 'properties' raises INVALID_FIELD."""
    schema = {"title": "x", "type": "object", "properties": "not_a_dict"}
    with pytest.raises(InvalidContractError, match=r"properties.*must be a dict"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_non_list_required_raises() -> None:
    """Non-list 'required' raises INVALID_FIELD."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"f": {"type": "string"}},
        "required": "not_a_list",
    }
    with pytest.raises(InvalidContractError, match=r"required.*must be a list"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_non_dict_property_raises() -> None:
    """A non-dict property value raises INVALID_FIELD."""
    schema = {"title": "x", "type": "object", "properties": {"f": "not_a_dict"}}
    with pytest.raises(InvalidContractError, match="is not a dict"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_money_missing_amount_raises() -> None:
    """MONEY property missing 'amount' subfield raises INVALID_FIELD."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "m": {
                "x-paxman-type": "MONEY",
                "type": "object",
                "properties": {"currency": {"type": "string"}},
                "required": ["currency"],
            },
        },
    }
    with pytest.raises(InvalidContractError, match=r"amount.*currency"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_money_non_object_raises() -> None:
    """MONEY property that is not 'object' type raises UNSUPPORTED_FIELD_TYPE."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "m": {"x-paxman-type": "MONEY", "type": "string"},
        },
    }
    with pytest.raises(InvalidContractError, match="must be an object"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_enum_non_list_raises() -> None:
    """ENUM property with non-list 'enum' raises INVALID_FIELD."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"e": {"enum": "not_a_list"}},
    }
    with pytest.raises(InvalidContractError, match=r"enum.*must be a list"):
        JsonSchemaAdapter().adapt(schema)


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_title_used_as_contract_id() -> None:
    """The 'title' key is used as contract id."""
    schema = {"title": "MyTitle", "type": "object", "properties": {"f": {"type": "string"}}}
    c = JsonSchemaAdapter().adapt(schema)
    assert c.id == "MyTitle"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_id_used_as_contract_id() -> None:
    """The '$id' key is used as contract id when title is missing."""
    schema = {
        "$id": "https://example.com/schemas/test.json",
        "type": "object",
        "properties": {"f": {"type": "string"}},
    }
    c = JsonSchemaAdapter().adapt(schema)
    assert c.id == "test.json"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_untitled_when_no_title_or_id() -> None:
    """Contract id falls back to 'untitled' when no title or $id."""
    schema = {"type": "object", "properties": {"f": {"type": "string"}}}
    c = JsonSchemaAdapter().adapt(schema)
    assert c.id == "untitled"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_description_from_title() -> None:
    """Property description falls back to 'title' when no 'description'."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"f": {"type": "string", "title": "My Field"}},
    }
    c = JsonSchemaAdapter().adapt(schema)
    assert c.fields[0].description == "My Field"


# --- Export coverage: nullable, default, constraints ------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_nullable_field() -> None:
    """A nullable field is exported with type array including 'null'."""
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.STRING,
        required=False,
        nullable=True,
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    prop = out["properties"]["f"]
    assert "null" in prop["type"]


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_default_value() -> None:
    """A field with a default value is exported with 'default' key."""
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.STRING,
        required=False,
        default="hello",
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["default"] == "hello"


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_min_length() -> None:
    """MIN_LENGTH constraint is exported as minLength."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.STRING,
        required=True,
        constraints=(Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 2}),),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["minLength"] == 2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_max_length() -> None:
    """MAX_LENGTH constraint is exported as maxLength."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.STRING,
        required=True,
        constraints=(Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 100}),),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["maxLength"] == 100


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_pattern() -> None:
    """PATTERN constraint is exported as pattern."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.STRING,
        required=True,
        constraints=(Constraint(kind=ConstraintKind.PATTERN, params={"regex": "^[A-Z]+$"}),),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["pattern"] == "^[A-Z]+$"


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_min_value_inclusive() -> None:
    """MIN_VALUE inclusive is exported as minimum."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.INTEGER,
        required=True,
        constraints=(
            Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0, "inclusive": True}),
        ),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["minimum"] == 0


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_min_value_exclusive() -> None:
    """MIN_VALUE exclusive is exported as exclusiveMinimum."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.INTEGER,
        required=True,
        constraints=(
            Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0, "inclusive": False}),
        ),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["exclusiveMinimum"] == 0


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_max_value_inclusive() -> None:
    """MAX_VALUE inclusive is exported as maximum."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.INTEGER,
        required=True,
        constraints=(
            Constraint(kind=ConstraintKind.MAX_VALUE, params={"max": 100, "inclusive": True}),
        ),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["maximum"] == 100


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_max_value_exclusive() -> None:
    """MAX_VALUE exclusive is exported as exclusiveMaximum."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.INTEGER,
        required=True,
        constraints=(
            Constraint(kind=ConstraintKind.MAX_VALUE, params={"max": 100, "inclusive": False}),
        ),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["exclusiveMaximum"] == 100


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_array_min_items() -> None:
    """MIN_LENGTH on ARRAY is exported as minItems."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.ARRAY,
        required=True,
        constraints=(Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["minItems"] == 1


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_constraint_array_max_items() -> None:
    """MAX_LENGTH on ARRAY is exported as maxItems."""
    from paxman.contract._types import Constraint, ConstraintKind
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.ARRAY,
        required=True,
        constraints=(Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 10}),),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    assert out["properties"]["f"]["maxItems"] == 10


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_money_with_default() -> None:
    """MONEY field with MoneyValue default is exported with default."""
    from decimal import Decimal

    from paxman.contract.canonical import CanonicalContract, CanonicalField, MoneyValue

    f = CanonicalField(
        id="f1",
        path="amount",
        name="amount",
        type=FieldType.MONEY,
        required=False,
        default=MoneyValue(amount=Decimal("19.99"), currency="USD"),
    )
    contract = CanonicalContract(id="x", fields=(f,))
    out = JsonSchemaAdapter().export(contract)
    prop = out["properties"]["amount"]
    assert prop["default"]["amount"] == "19.99"
    assert prop["default"]["currency"] == "USD"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_supported_draft_07() -> None:
    """Draft-07 $schema is accepted (best-effort)."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "x",
        "type": "object",
        "properties": {"f": {"type": "string"}},
        "required": ["f"],
    }
    c = JsonSchemaAdapter().adapt(schema)
    assert c.id == "x"


# --- V2-only keyword rejection (Oracle review F3/F8) ------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_rejects_const_keyword() -> None:
    """``const`` is V2-only; rejected with UNSUPPORTED_JSON_SCHEMA_FEATURE.

    Oracle review F8: the docstring previously claimed `const` mapped to
    STRING (literal), but no code handled it. The fix is to reject it
    explicitly so the caller knows the schema is not fully representable.
    """
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"f": {"const": "hello"}},
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "UNSUPPORTED_JSON_SCHEMA_FEATURE"
    assert excinfo.value.context["keyword"] == "const"
    assert excinfo.value.context["property"] == "f"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_rejects_oneof_keyword() -> None:
    """``oneOf`` is V2-only; rejected with UNSUPPORTED_JSON_SCHEMA_FEATURE."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "f": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
        },
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "UNSUPPORTED_JSON_SCHEMA_FEATURE"
    assert excinfo.value.context["keyword"] == "oneOf"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_rejects_anyof_keyword() -> None:
    """``anyOf`` is V2-only; rejected with UNSUPPORTED_JSON_SCHEMA_FEATURE."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "f": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        },
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "UNSUPPORTED_JSON_SCHEMA_FEATURE"
    assert excinfo.value.context["keyword"] == "anyOf"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_rejects_allof_keyword() -> None:
    """``allOf`` is V2-only; rejected with UNSUPPORTED_JSON_SCHEMA_FEATURE."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "f": {"allOf": [{"type": "string"}, {"minLength": 1}]},
        },
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "UNSUPPORTED_JSON_SCHEMA_FEATURE"
    assert excinfo.value.context["keyword"] == "allOf"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_rejects_ref_keyword() -> None:
    """``$ref`` is V2-only; rejected with UNSUPPORTED_JSON_SCHEMA_FEATURE."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"f": {"$ref": "#/$defs/Other"}},
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "UNSUPPORTED_JSON_SCHEMA_FEATURE"
    assert excinfo.value.context["keyword"] == "$ref"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_rejects_additional_properties_false() -> None:
    """``additionalProperties: false`` is a constraint we cannot represent.

    Accepted but not enforced in V1, so the conservative choice is to
    reject rather than silently drop the constraint.
    """
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"f": {"type": "string", "additionalProperties": False}},
        "required": ["f"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "UNSUPPORTED_JSON_SCHEMA_FEATURE"
    assert excinfo.value.context["keyword"] == "additionalProperties"


# --- Oracle review F9: list-type handling for nullable round-trip ---------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_nullable_round_trips_via_type_array() -> None:
    """A nullable field exported as ``type: ["string", "null"]`` re-adapts.

    Oracle review F9: the previous code crashed on list types when calling
    ``_JSON_TYPE_TO_FIELD_TYPE.get(["string", "null"])``. The fix extracts
    the non-null type and sets ``nullable=True``.
    """
    from paxman.contract.canonical import CanonicalContract, CanonicalField

    f = CanonicalField(
        id="f1",
        path="f",
        name="f",
        type=FieldType.STRING,
        required=False,
        nullable=True,
    )
    contract = CanonicalContract(id="x", fields=(f,))
    exported = JsonSchemaAdapter().export(contract)
    # Now re-adapt the exported schema. This used to crash.
    c2 = JsonSchemaAdapter().adapt(exported)
    assert c2.fields[0].nullable is True
    assert c2.fields[0].type is FieldType.STRING


# --- Oracle review F8: minItems / maxItems validation ---------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_min_items_string_raises() -> None:
    """``minItems`` provided as a string raises InvalidContractError (not raw ValueError)."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "string"}, "minItems": "3"},
        },
        "required": ["items"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "INVALID_CONSTRAINT"
    assert excinfo.value.context["value"] == "'3'"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_max_items_negative_raises() -> None:
    """Negative ``maxItems`` is rejected with INVALID_CONSTRAINT."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "string"}, "maxItems": -1},
        },
        "required": ["items"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "INVALID_CONSTRAINT"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_min_items_float_truncation_rejected() -> None:
    """Float ``minItems`` (which int() would silently truncate) is rejected."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "string"}, "minItems": 1.5},
        },
        "required": ["items"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "INVALID_CONSTRAINT"


# --- Oracle review F6: required list validation ---------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_required_non_string_raises() -> None:
    """Non-string entries in the ``required`` list are rejected, not silently dropped."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {"f": {"type": "string"}},
        "required": ["f", 42],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "INVALID_FIELD"
    assert excinfo.value.context["index"] == 1


# --- Oracle review F7: MoneyValue decimal conversion error handling -------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_money_default_non_numeric_amount_raises() -> None:
    """Non-numeric ``amount`` in MONEY default raises InvalidContractError, not raw InvalidOperation."""
    schema = {
        "title": "x",
        "type": "object",
        "properties": {
            "amount": {
                "x-paxman-type": "MONEY",
                "type": "object",
                "properties": {
                    "amount": {"type": "string", "pattern": r"^-?\d+(\.\d+)?$"},
                    "currency": {"type": "string", "pattern": r"^[A-Z]{3}$"},
                },
                "required": ["amount", "currency"],
                "default": {"amount": "not-a-number", "currency": "USD"},
            },
        },
        "required": ["amount"],
    }
    with pytest.raises(InvalidContractError) as excinfo:
        JsonSchemaAdapter().adapt(schema)
    assert excinfo.value.error_code == "INVALID_FIELD"
    assert "not-a-number" in excinfo.value.context["amount"]

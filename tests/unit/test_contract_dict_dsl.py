"""Unit tests for ``paxman.contract.adapters.dict_dsl`` — Dict DSL adapter.

Covers the 3 worked examples from dict-dsl-spec.md, all 9 V1 field types,
all 7 constraint kinds, all 15 documented error_codes, and the export
round-trip. Per Sprint 2 exit criteria #6 and #11.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.contract._types import ConstraintKind
from paxman.contract.adapters.dict_dsl import DictDSLAdapter
from paxman.contract.canonical import CanonicalContract, MoneyValue
from paxman.errors import InvalidContractError
from paxman.types import FieldType

# --- helpers ----------------------------------------------------------------


def _adapter() -> DictDSLAdapter:
    """Return a fresh DictDSLAdapter instance."""
    return DictDSLAdapter()


def _adapt(raw: dict) -> CanonicalContract:
    """Adapt a dict via the Dict DSL adapter."""
    return _adapter().adapt(raw)


# --- format_id --------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_id_is_dict_dsl() -> None:
    """The adapter's format_id is 'dict_dsl'."""
    assert DictDSLAdapter().format_id == "dict_dsl"


# --- Example 1: Minimal contract (from spec §5) -----------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_example_1_minimal_contract() -> None:
    """Example 1 from dict-dsl-spec.md: minimal 2-field contract."""
    raw = {
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
    c = _adapt(raw)
    assert c.id == "user-profile"
    assert c.version == "1"
    assert len(c.fields) == 2
    assert c.fields[0].name == "full_name"
    assert c.fields[0].type is FieldType.STRING
    assert c.fields[0].required is True
    assert c.fields[0].description == "The user's display name."
    assert c.fields[1].name == "age"
    assert c.fields[1].type is FieldType.INTEGER
    assert c.fields[1].required is False
    assert c.fields[1].default == 0


# --- Example 2: Invoice with MONEY, ARRAY, and ENUM (from spec §5) ----------


@pytest.mark.deterministic
@pytest.mark.unit
def test_example_2_invoice() -> None:
    """Example 2 from dict-dsl-spec.md: realistic invoice contract."""
    raw = {
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
                "enum_values": ["USD", "EUR", "JPY"],
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
    c = _adapt(raw)
    assert c.id == "invoice-v1"
    assert len(c.fields) == 6
    f0 = c.fields[0]
    assert f0.name == "supplier_name"
    assert f0.type is FieldType.STRING
    assert f0.semantic_tags == ("pii",)
    assert len(f0.constraints) == 2
    assert f0.constraints[0].kind is ConstraintKind.MIN_LENGTH
    assert f0.constraints[1].kind is ConstraintKind.MAX_LENGTH
    f1 = c.fields[1]
    assert f1.type is FieldType.ENUM
    assert f1.enum_values is not None
    assert "USD" in f1.enum_values
    f2 = c.fields[2]
    assert f2.type is FieldType.MONEY
    assert c.policies is not None
    assert c.policies.confidence_floor == 0.85
    assert c.policies.unresolved_acceptable is False


# --- Example 3: Adversarial fixture (from spec §5) --------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_example_3_adversarial() -> None:
    """Example 3 from dict-dsl-spec.md: adversarial test fixture."""
    raw = {
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
                    {
                        "kind": "enum",
                        "params": {"values": ["food", "transport", "utilities", "other"]},
                    },
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
    c = _adapt(raw)
    assert c.id == "adversarial-fixture-001"
    assert len(c.fields) == 4
    f0 = c.fields[0]
    assert f0.constraints[0].kind is ConstraintKind.PATTERN
    assert f0.constraints[0].params["regex"] == "^TXN-[A-Z0-9]{8,16}$"
    f1 = c.fields[1]
    assert f1.type is FieldType.MONEY
    assert isinstance(f1.default, MoneyValue)
    assert f1.default.currency == "USD"
    f2 = c.fields[2]
    assert f2.type is FieldType.ENUM
    assert f2.enum_values is not None
    assert "food" in f2.enum_values
    assert c.policies is not None
    assert c.policies.confidence_floor == 0.95
    assert c.policies.stop_on_first_unresolved is True


# --- All 9 V1 field types ---------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
@pytest.mark.parametrize(
    "type_literal,field_type",
    [
        ("STRING", FieldType.STRING),
        ("INTEGER", FieldType.INTEGER),
        ("DECIMAL", FieldType.DECIMAL),
        ("BOOLEAN", FieldType.BOOLEAN),
        ("DATE", FieldType.DATE),
        ("ENUM", FieldType.ENUM),
        ("OBJECT", FieldType.OBJECT),
        ("ARRAY", FieldType.ARRAY),
        ("MONEY", FieldType.MONEY),
    ],
)
def test_all_nine_field_types(type_literal: str, field_type: FieldType) -> None:
    """Each of the 9 V1 type literals maps to the correct FieldType."""
    raw: dict = {
        "id": "types-test",
        "fields": [{"name": "f", "type": type_literal, "required": True}],
    }
    if type_literal == "ENUM":
        raw["fields"][0]["enum_values"] = ["a", "b"]
    c = _adapt(raw)
    assert c.fields[0].type is field_type


# --- All 7 constraint kinds -------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_min_length() -> None:
    """min_length constraint maps to ConstraintKind.MIN_LENGTH."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "STRING",
                    "required": True,
                    "constraints": [{"kind": "min_length", "params": {"min": 1}}],
                }
            ],
        }
    )
    assert c.fields[0].constraints[0].kind is ConstraintKind.MIN_LENGTH
    assert c.fields[0].constraints[0].params == {"min": 1}


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_max_length() -> None:
    """max_length constraint maps to ConstraintKind.MAX_LENGTH."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "STRING",
                    "required": True,
                    "constraints": [{"kind": "max_length", "params": {"max": 100}}],
                }
            ],
        }
    )
    assert c.fields[0].constraints[0].kind is ConstraintKind.MAX_LENGTH


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_pattern() -> None:
    """pattern constraint maps to ConstraintKind.PATTERN."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "STRING",
                    "required": True,
                    "constraints": [{"kind": "pattern", "params": {"regex": "^[A-Z]+$"}}],
                }
            ],
        }
    )
    assert c.fields[0].constraints[0].kind is ConstraintKind.PATTERN


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_min_value() -> None:
    """min_value constraint maps to ConstraintKind.MIN_VALUE."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "INTEGER",
                    "required": True,
                    "constraints": [{"kind": "min_value", "params": {"min": 0}}],
                }
            ],
        }
    )
    assert c.fields[0].constraints[0].kind is ConstraintKind.MIN_VALUE


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_max_value() -> None:
    """max_value constraint maps to ConstraintKind.MAX_VALUE."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "INTEGER",
                    "required": True,
                    "constraints": [{"kind": "max_value", "params": {"max": 100}}],
                }
            ],
        }
    )
    assert c.fields[0].constraints[0].kind is ConstraintKind.MAX_VALUE


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_enum() -> None:
    """enum constraint maps to ConstraintKind.ENUM."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "STRING",
                    "required": True,
                    "constraints": [{"kind": "enum", "params": {"values": ["a", "b"]}}],
                }
            ],
        }
    )
    assert c.fields[0].constraints[0].kind is ConstraintKind.ENUM


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_iso_4217() -> None:
    """iso_4217 constraint maps to ConstraintKind.ISO_4217 with empty params."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "STRING",
                    "required": True,
                    "constraints": [{"kind": "iso_4217", "params": {}}],
                }
            ],
        }
    )
    assert c.fields[0].constraints[0].kind is ConstraintKind.ISO_4217
    assert c.fields[0].constraints[0].params == {}


# --- Error codes: 15 documented values --------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_contract_id() -> None:
    """Missing 'id' key raises MISSING_CONTRACT_ID."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"fields": [{"name": "f", "type": "STRING", "required": True}]})
    assert exc_info.value.error_code == "MISSING_CONTRACT_ID"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_contract_id_empty_string() -> None:
    """Empty 'id' raises MISSING_CONTRACT_ID."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "", "fields": [{"name": "f", "type": "STRING", "required": True}]})
    assert exc_info.value.error_code == "MISSING_CONTRACT_ID"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_fields() -> None:
    """Missing 'fields' key raises MISSING_FIELDS."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c"})
    assert exc_info.value.error_code == "MISSING_FIELDS"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_fields_non_list() -> None:
    """Non-list 'fields' raises MISSING_FIELDS."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": "not_a_list"})
    assert exc_info.value.error_code == "MISSING_FIELDS"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_empty_fields() -> None:
    """Empty fields list raises EMPTY_FIELDS."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": []})
    assert exc_info.value.error_code == "EMPTY_FIELDS"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_field_name() -> None:
    """Field without 'name' raises MISSING_FIELD_NAME."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"type": "STRING", "required": True}]})
    assert exc_info.value.error_code == "MISSING_FIELD_NAME"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_field_name_empty() -> None:
    """Field with empty 'name' raises MISSING_FIELD_NAME."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"name": "", "type": "STRING", "required": True}]})
    assert exc_info.value.error_code == "MISSING_FIELD_NAME"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_type() -> None:
    """Field without 'type' raises MISSING_TYPE."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"name": "f", "required": True}]})
    assert exc_info.value.error_code == "MISSING_TYPE"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_missing_required_flag() -> None:
    """Field without 'required' raises MISSING_REQUIRED_FLAG."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"name": "f", "type": "STRING"}]})
    assert exc_info.value.error_code == "MISSING_REQUIRED_FLAG"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_unknown_field_type() -> None:
    """Unknown type value raises UNKNOWN_FIELD_TYPE."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"name": "f", "type": "STRINGY", "required": True}]})
    assert exc_info.value.error_code == "UNKNOWN_FIELD_TYPE"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_default_type_mismatch_string() -> None:
    """STRING default that is not a str raises DEFAULT_TYPE_MISMATCH."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True, "default": 42}],
            }
        )
    assert exc_info.value.error_code == "DEFAULT_TYPE_MISMATCH"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_default_type_mismatch_integer() -> None:
    """INTEGER default that is not an int raises DEFAULT_TYPE_MISMATCH."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "INTEGER", "required": True, "default": "five"}],
            }
        )
    assert exc_info.value.error_code == "DEFAULT_TYPE_MISMATCH"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_default_type_mismatch_boolean() -> None:
    """BOOLEAN default that is not a bool raises DEFAULT_TYPE_MISMATCH."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "BOOLEAN", "required": True, "default": 1}],
            }
        )
    assert exc_info.value.error_code == "DEFAULT_TYPE_MISMATCH"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_default_type_mismatch_object() -> None:
    """OBJECT default that is not a dict raises DEFAULT_TYPE_MISMATCH."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {"name": "f", "type": "OBJECT", "required": True, "default": "not_dict"}
                ],
            }
        )
    assert exc_info.value.error_code == "DEFAULT_TYPE_MISMATCH"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_default_type_mismatch_array() -> None:
    """ARRAY default that is not a list raises DEFAULT_TYPE_MISMATCH."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "ARRAY", "required": True, "default": "not_list"}],
            }
        )
    assert exc_info.value.error_code == "DEFAULT_TYPE_MISMATCH"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_default_type_mismatch_decimal() -> None:
    """DECIMAL default that is not numeric raises DEFAULT_TYPE_MISMATCH."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "DECIMAL", "required": True, "default": True}],
            }
        )
    assert exc_info.value.error_code == "DEFAULT_TYPE_MISMATCH"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_duplicate_field() -> None:
    """Two fields with the same name raises DUPLICATE_FIELD."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {"name": "dup", "type": "STRING", "required": True},
                    {"name": "dup", "type": "INTEGER", "required": True},
                ],
            }
        )
    assert exc_info.value.error_code == "DUPLICATE_FIELD"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_unknown_constraint_kind() -> None:
    """Unknown constraint kind raises UNKNOWN_CONSTRAINT_KIND."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "STRING",
                        "required": True,
                        "constraints": [{"kind": "weird_kind", "params": {}}],
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "UNKNOWN_CONSTRAINT_KIND"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_constraint_param_missing() -> None:
    """Missing required param key raises CONSTRAINT_PARAM_MISSING."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "STRING",
                        "required": True,
                        "constraints": [{"kind": "min_length", "params": {}}],
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "CONSTRAINT_PARAM_MISSING"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_money_requires_currency() -> None:
    """MONEY default missing 'currency' raises MONEY_REQUIRES_CURRENCY."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {"name": "f", "type": "MONEY", "required": True, "default": {"amount": "10.00"}}
                ],
            }
        )
    assert exc_info.value.error_code == "MONEY_REQUIRES_CURRENCY"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_invalid_iso_4217() -> None:
    """MONEY default with non-ISO-4217 currency raises INVALID_ISO_4217."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "MONEY",
                        "required": True,
                        "default": {"amount": "10.00", "currency": "btc"},
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_ISO_4217"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_invalid_regex_pattern() -> None:
    """Invalid regex in pattern constraint raises INVALID_REGEX_PATTERN."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "STRING",
                        "required": True,
                        "constraints": [{"kind": "pattern", "params": {"regex": "[unclosed"}}],
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_REGEX_PATTERN"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_invalid_confidence_floor() -> None:
    """confidence_floor outside [0,1] raises INVALID_CONFIDENCE_FLOOR."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True}],
                "policy": {"confidence_floor": 1.5},
            }
        )
    assert exc_info.value.error_code == "INVALID_CONFIDENCE_FLOOR"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_invalid_policy_key() -> None:
    """Unknown policy key raises INVALID_POLICY_KEY."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True}],
                "policy": {"unknown_key": True},
            }
        )
    assert exc_info.value.error_code == "INVALID_POLICY_KEY"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_dict_input_raises() -> None:
    """Non-dict input raises InvalidContractError."""
    with pytest.raises(InvalidContractError):
        _adapter().adapt("not_a_dict")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_list_constraints_raises() -> None:
    """Non-list 'constraints' raises INVALID_CONSTRAINT."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True}],
                "constraints": "not_a_list",
            }
        )
    assert exc_info.value.error_code == "INVALID_CONSTRAINT"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_dict_field_raises() -> None:
    """Non-dict field raises INVALID_FIELD."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": ["not_a_dict"]})
    assert exc_info.value.error_code == "INVALID_FIELD"


# --- export: round-trip -----------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_minimal_contract_round_trips() -> None:
    """export(adapt(d)) → re-adapt produces the same contract."""
    adapter = _adapter()
    raw = {"id": "rt-min", "fields": [{"name": "f", "type": "STRING", "required": True}]}
    c1 = adapter.adapt(raw)
    exported = adapter.export(c1)
    c2 = adapter.adapt(exported)
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_with_policy_round_trips() -> None:
    """A contract with policy round-trips through export."""
    adapter = _adapter()
    raw = {
        "id": "rt-pol",
        "fields": [{"name": "f", "type": "STRING", "required": True}],
        "policy": {"confidence_floor": 0.90, "stop_on_first_unresolved": True},
    }
    c1 = adapter.adapt(raw)
    exported = adapter.export(c1)
    c2 = adapter.adapt(exported)
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_money_default_round_trips() -> None:
    """A contract with MONEY default round-trips through export."""
    adapter = _adapter()
    raw = {
        "id": "rt-money",
        "fields": [
            {
                "name": "amount",
                "type": "MONEY",
                "required": False,
                "default": {"amount": "0.00", "currency": "USD"},
            }
        ],
    }
    c1 = adapter.adapt(raw)
    exported = adapter.export(c1)
    c2 = adapter.adapt(exported)
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_with_tags_and_constraints_round_trips() -> None:
    """A contract with tags and constraints round-trips."""
    adapter = _adapter()
    raw = {
        "id": "rt-tags",
        "fields": [
            {
                "name": "f",
                "type": "STRING",
                "required": True,
                "tags": ["pii"],
                "constraints": [
                    {"kind": "min_length", "params": {"min": 1}},
                    {"kind": "max_length", "params": {"max": 100}},
                ],
            }
        ],
    }
    c1 = adapter.adapt(raw)
    exported = adapter.export(c1)
    c2 = adapter.adapt(exported)
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_enum_field_round_trips() -> None:
    """A contract with an ENUM field round-trips."""
    adapter = _adapter()
    raw = {
        "id": "rt-enum",
        "fields": [
            {
                "name": "status",
                "type": "ENUM",
                "required": True,
                "enum_values": ["active", "inactive"],
            }
        ],
    }
    c1 = adapter.adapt(raw)
    exported = adapter.export(c1)
    c2 = adapter.adapt(exported)
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_decimal_default_round_trips() -> None:
    """A contract with DECIMAL default round-trips."""
    adapter = _adapter()
    raw = {
        "id": "rt-dec",
        "fields": [{"name": "price", "type": "DECIMAL", "required": False, "default": "3.14"}],
    }
    c1 = adapter.adapt(raw)
    exported = adapter.export(c1)
    c2 = adapter.adapt(exported)
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_non_canonical_raises() -> None:
    """export with non-CanoonicalContract raises."""
    with pytest.raises(InvalidContractError):
        _adapter().export("not_a_contract")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_includes_version() -> None:
    """export includes the 'version' key."""
    adapter = _adapter()
    c = adapter.adapt(
        {"id": "c", "version": "2", "fields": [{"name": "f", "type": "STRING", "required": True}]}
    )
    exported = adapter.export(c)
    assert exported["version"] == "2"


# --- additional adapt tests -------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_with_description() -> None:
    """Description is carried into CanonicalField."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {"name": "f", "type": "STRING", "required": True, "description": "A field."}
            ],
        }
    )
    assert c.fields[0].description == "A field."


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_with_tags() -> None:
    """Tags are carried into CanonicalField.semantic_tags."""
    c = _adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "STRING", "required": True, "tags": ["pii", "email"]}],
        }
    )
    assert c.fields[0].semantic_tags == ("pii", "email")


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_with_invalid_tags_raises() -> None:
    """Non-string tag raises INVALID_SEMANTIC_TAG."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {"id": "c", "fields": [{"name": "f", "type": "STRING", "required": True, "tags": [42]}]}
        )
    assert exc_info.value.error_code == "INVALID_SEMANTIC_TAG"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_with_malformed_tag_raises() -> None:
    """Malformed (uppercase) tag raises INVALID_SEMANTIC_TAG."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True, "tags": ["PII"]}],
            }
        )
    assert exc_info.value.error_code == "INVALID_SEMANTIC_TAG"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_decimal_default_from_string() -> None:
    """DECIMAL default from string is coerced to Decimal."""
    c = _adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "DECIMAL", "required": False, "default": "3.14"}],
        }
    )
    assert c.fields[0].default == Decimal("3.14")


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_decimal_default_from_int() -> None:
    """DECIMAL default from int is coerced to Decimal."""
    c = _adapt(
        {"id": "c", "fields": [{"name": "f", "type": "DECIMAL", "required": False, "default": 42}]}
    )
    assert c.fields[0].default == Decimal("42")


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_enum_with_enum_values_key() -> None:
    """ENUM field with 'enum_values' key populates EnumValueSet."""
    c = _adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "ENUM", "required": True, "enum_values": ["a", "b"]}],
        }
    )
    assert c.fields[0].enum_values is not None
    assert len(c.fields[0].enum_values) == 2


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_enum_without_values_or_constraint_raises() -> None:
    """ENUM field without enum_values or enum constraint raises."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"name": "f", "type": "ENUM", "required": True}]})
    assert exc_info.value.error_code == "MISSING_ENUM_VALUES"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_enum_constraint_provides_values() -> None:
    """ENUM field with 'enum' constraint (no enum_values) uses constraint values."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "ENUM",
                    "required": True,
                    "constraints": [{"kind": "enum", "params": {"values": ["x", "y"]}}],
                }
            ],
        }
    )
    assert c.fields[0].enum_values is not None
    assert "x" in c.fields[0].enum_values


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_field_id_is_derived_from_contract_and_name() -> None:
    """Field id follows the pattern 'field_{contract_id}_{name}'."""
    c = _adapt(
        {"id": "my_contract", "fields": [{"name": "my_field", "type": "STRING", "required": True}]}
    )
    assert c.fields[0].id == "field_my_contract_my_field"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_version_default_is_one() -> None:
    """Omitted version defaults to '1'."""
    c = _adapt({"id": "c", "fields": [{"name": "f", "type": "STRING", "required": True}]})
    assert c.version == "1"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_invalid_version_raises() -> None:
    """Empty version raises INVALID_VERSION."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "version": "",
                "fields": [{"name": "f", "type": "STRING", "required": True}],
            }
        )
    assert exc_info.value.error_code == "INVALID_VERSION"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_boolean_default_false() -> None:
    """BOOLEAN default=False is accepted."""
    c = _adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "BOOLEAN", "required": False, "default": False}],
        }
    )
    assert c.fields[0].default is False


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_object_default_empty_dict() -> None:
    """OBJECT default={} is accepted."""
    c = _adapt(
        {"id": "c", "fields": [{"name": "f", "type": "OBJECT", "required": False, "default": {}}]}
    )
    assert c.fields[0].default == {}


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_array_default_empty_list() -> None:
    """ARRAY default=[] is accepted."""
    c = _adapt(
        {"id": "c", "fields": [{"name": "f", "type": "ARRAY", "required": False, "default": []}]}
    )
    assert c.fields[0].default == []


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_date_default_string() -> None:
    """DATE default as string is accepted."""
    c = _adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "DATE", "required": False, "default": "2026-01-01"}],
        }
    )
    assert c.fields[0].default == "2026-01-01"


# --- Additional coverage: contract-level constraints, edge cases ------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_level_constraints_are_parsed() -> None:
    """Contract-level constraints are parsed and carried."""
    c = _adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "STRING", "required": True}],
            "constraints": [{"kind": "iso_4217", "params": {}}],
        }
    )
    assert len(c.constraints) == 1
    assert c.constraints[0].kind is ConstraintKind.ISO_4217


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_contract_level_constraints() -> None:
    """Contract-level constraints are exported."""
    adapter = _adapter()
    c = adapter.adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "STRING", "required": True}],
            "constraints": [{"kind": "iso_4217", "params": {}}],
        }
    )
    exported = adapter.export(c)
    assert "constraints" in exported
    assert len(exported["constraints"]) == 1


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_string_type_raises() -> None:
    """Non-string 'type' raises MISSING_TYPE."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"name": "f", "type": 42, "required": True}]})
    assert exc_info.value.error_code == "MISSING_TYPE"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_bool_required_raises() -> None:
    """Non-bool 'required' raises MISSING_REQUIRED_FLAG."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt({"id": "c", "fields": [{"name": "f", "type": "STRING", "required": "yes"}]})
    assert exc_info.value.error_code == "MISSING_REQUIRED_FLAG"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_string_description_raises() -> None:
    """Non-string 'description' raises INVALID_FIELD."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True, "description": 42}],
            }
        )
    assert exc_info.value.error_code == "INVALID_FIELD"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_list_tags_raises() -> None:
    """Non-list 'tags' raises INVALID_SEMANTIC_TAG."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True, "tags": "pii"}],
            }
        )
    assert exc_info.value.error_code == "INVALID_SEMANTIC_TAG"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_list_field_constraints_raises() -> None:
    """Non-list field 'constraints' raises INVALID_CONSTRAINT."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {"name": "f", "type": "STRING", "required": True, "constraints": "not_list"}
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_CONSTRAINT"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_constraint_missing_kind_raises() -> None:
    """Constraint without 'kind' raises UNKNOWN_CONSTRAINT_KIND."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "STRING",
                        "required": True,
                        "constraints": [{"params": {}}],
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "UNKNOWN_CONSTRAINT_KIND"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_constraint_non_dict_params_raises() -> None:
    """Non-dict constraint 'params' raises INVALID_CONSTRAINT."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "STRING",
                        "required": True,
                        "constraints": [{"kind": "min_length", "params": "not_dict"}],
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_CONSTRAINT"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_constraint_non_dict_raises() -> None:
    """Non-dict constraint raises INVALID_CONSTRAINT."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {"name": "f", "type": "STRING", "required": True, "constraints": ["not_a_dict"]}
                ],
            }
        )  # type: ignore[list-item]
    assert exc_info.value.error_code == "INVALID_CONSTRAINT"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_pattern_non_string_regex_raises() -> None:
    """Non-string regex in pattern constraint raises INVALID_REGEX_PATTERN."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "STRING",
                        "required": True,
                        "constraints": [{"kind": "pattern", "params": {"regex": 42}}],
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_REGEX_PATTERN"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_enum_constraint_non_list_values() -> None:
    """Non-list 'values' in enum constraint raises INVALID_CONSTRAINT."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {
                        "name": "f",
                        "type": "STRING",
                        "required": True,
                        "constraints": [{"kind": "enum", "params": {"values": "not_list"}}],
                    }
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_CONSTRAINT"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_non_dict_policy_raises() -> None:
    """Non-dict 'policy' raises INVALID_POLICY_KEY."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "STRING", "required": True}],
                "policy": "not_a_dict",
            }
        )
    assert exc_info.value.error_code == "INVALID_POLICY_KEY"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_enum_values_non_list_raises() -> None:
    """Non-list 'enum_values' raises INVALID_FIELD."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [
                    {"name": "f", "type": "ENUM", "required": True, "enum_values": "not_a_list"}
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_FIELD"


@pytest.mark.deterministic
@pytest.mark.unit
def test_error_empty_enum_values_raises() -> None:
    """Empty 'enum_values' raises MISSING_ENUM_VALUES."""
    with pytest.raises(InvalidContractError) as exc_info:
        _adapt(
            {
                "id": "c",
                "fields": [{"name": "f", "type": "ENUM", "required": True, "enum_values": []}],
            }
        )
    assert exc_info.value.error_code == "MISSING_ENUM_VALUES"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_decimal_default_from_decimal() -> None:
    """DECIMAL default from a Decimal instance is accepted."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {"name": "f", "type": "DECIMAL", "required": False, "default": Decimal("3.14")}
            ],
        }
    )
    assert c.fields[0].default == Decimal("3.14")


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_enum_default_value() -> None:
    """ENUM default value is accepted as-is."""
    c = _adapt(
        {
            "id": "c",
            "fields": [
                {
                    "name": "f",
                    "type": "ENUM",
                    "required": False,
                    "default": "active",
                    "enum_values": ["active", "inactive"],
                }
            ],
        }
    )
    assert c.fields[0].default == "active"


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_includes_enum_values() -> None:
    """export includes 'enum_values' for ENUM fields."""
    adapter = _adapter()
    c = adapter.adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "ENUM", "required": True, "enum_values": ["a", "b"]}],
        }
    )
    exported = adapter.export(c)
    assert "enum_values" in exported["fields"][0]
    assert exported["fields"][0]["enum_values"] == ["a", "b"]


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_includes_tags() -> None:
    """export includes 'tags' for fields with semantic tags."""
    adapter = _adapter()
    c = adapter.adapt(
        {"id": "c", "fields": [{"name": "f", "type": "STRING", "required": True, "tags": ["pii"]}]}
    )
    exported = adapter.export(c)
    assert "tags" in exported["fields"][0]
    assert exported["fields"][0]["tags"] == ["pii"]


@pytest.mark.deterministic
@pytest.mark.unit
def test_export_includes_description() -> None:
    """export includes 'description' for fields with descriptions."""
    adapter = _adapter()
    c = adapter.adapt(
        {
            "id": "c",
            "fields": [{"name": "f", "type": "STRING", "required": True, "description": "A field"}],
        }
    )
    exported = adapter.export(c)
    assert exported["fields"][0]["description"] == "A field"


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_hints_round_trip() -> None:
    """format_hints are parsed, stored on the field, and re-exported."""
    from paxman.contract import FormatHint

    adapter = _adapter()
    canonical = adapter.adapt(
        {
            "id": "c1",
            "version": "1.0",
            "fields": [
                {
                    "name": "supplier",
                    "type": "STRING",
                    "required": True,
                    "format_hints": ["csv", "JSON"],
                },
                {"name": "amount", "type": "DECIMAL", "required": True},
            ],
        }
    )
    supplier = next(f for f in canonical.fields if f.name == "supplier")
    assert supplier.format_hints == (FormatHint.CSV, FormatHint.JSON)
    amount = next(f for f in canonical.fields if f.name == "amount")
    assert amount.format_hints == ()

    exported = adapter.export(canonical)
    supplier_out = next(f for f in exported["fields"] if f["name"] == "supplier")
    assert supplier_out["format_hints"] == ["csv", "json"]
    amount_out = next(f for f in exported["fields"] if f["name"] == "amount")
    assert "format_hints" not in amount_out


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_hints_invalid_string() -> None:
    """Unknown format_hint values are rejected with INVALID_FORMAT_HINT."""
    adapter = _adapter()
    with pytest.raises(InvalidContractError) as exc_info:
        adapter.adapt(
            {
                "id": "c1",
                "version": "1.0",
                "fields": [
                    {
                        "name": "supplier",
                        "type": "STRING",
                        "required": True,
                        "format_hints": ["pdf"],
                    },
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_FORMAT_HINT"


@pytest.mark.deterministic
@pytest.mark.unit
def test_format_hints_must_be_list() -> None:
    """format_hints must be a list; non-list values are rejected."""
    adapter = _adapter()
    with pytest.raises(InvalidContractError) as exc_info:
        adapter.adapt(
            {
                "id": "c1",
                "version": "1.0",
                "fields": [
                    {
                        "name": "supplier",
                        "type": "STRING",
                        "required": True,
                        "format_hints": "csv",
                    },
                ],
            }
        )
    assert exc_info.value.error_code == "INVALID_FORMAT_HINT"

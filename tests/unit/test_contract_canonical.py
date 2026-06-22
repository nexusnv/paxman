"""Unit tests for ``paxman.contract.canonical`` — MoneyValue, CanonicalField, CanonicalContract.

Exercises every constructor invariant: MONEY precision/currency/float
rejection, all 9 FieldType values, default-value type coupling, ENUM
enum_values coupling, confidence_threshold bounds, contract-level
uniqueness of ids/paths, and the convenience helpers (field_by_path,
field_by_id, required_fields).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.contract._types import EnumValueSet, ResolutionPolicy
from paxman.contract.canonical import CanonicalContract, CanonicalField, MoneyValue
from paxman.types import FieldType

# --- helpers ----------------------------------------------------------------


def _field(
    name: str = "f",
    *,
    type_: FieldType = FieldType.STRING,
    required: bool = True,
    **kwargs: object,
) -> CanonicalField:
    """Build a minimal CanonicalField with sensible defaults."""
    return CanonicalField(
        id=f"field_test_{name}",
        path=name,
        name=name,
        type=type_,
        required=required,
        **kwargs,
    )


# --- MoneyValue -------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_valid_usd() -> None:
    """MoneyValue with USD and default precision=2."""
    m = MoneyValue(amount=Decimal("19.99"), currency="USD")
    assert m.amount == Decimal("19.99")
    assert m.currency == "USD"
    assert m.precision == 2


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_valid_jpy_precision_zero() -> None:
    """MoneyValue with JPY and precision=0 (no minor unit)."""
    m = MoneyValue(amount=Decimal("1000"), currency="JPY", precision=0)
    assert m.currency == "JPY"
    assert m.precision == 0


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_negative_amount_allowed() -> None:
    """Negative amounts are allowed (refunds, credits)."""
    m = MoneyValue(amount=Decimal("-10.00"), currency="USD")
    assert m.amount == Decimal("-10.00")


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_explicit_precision_none() -> None:
    """precision=None means 'inferred from amount'."""
    m = MoneyValue(amount=Decimal("19.99"), currency="EUR", precision=None)
    assert m.precision is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_float_amount_rejected() -> None:
    """Float amount raises TypeError (no float for monetary math)."""
    with pytest.raises(TypeError, match="amount must be a Decimal"):
        MoneyValue(amount=19.99, currency="USD")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_int_amount_rejected() -> None:
    """Int amount raises TypeError (must be Decimal, not int)."""
    with pytest.raises(TypeError, match="amount must be a Decimal"):
        MoneyValue(amount=100, currency="USD")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_lowercase_currency_rejected() -> None:
    """Lowercase currency code raises ValueError."""
    with pytest.raises(ValueError, match="currency must be a 3-letter"):
        MoneyValue(amount=Decimal("1"), currency="usd")


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_two_letter_currency_rejected() -> None:
    """Two-letter currency code raises ValueError."""
    with pytest.raises(ValueError, match="currency must be a 3-letter"):
        MoneyValue(amount=Decimal("1"), currency="US")


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_four_letter_currency_rejected() -> None:
    """Four-letter currency code raises ValueError."""
    with pytest.raises(ValueError, match="currency must be a 3-letter"):
        MoneyValue(amount=Decimal("1"), currency="USDD")


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_non_string_currency_rejected() -> None:
    """Non-string currency raises ValueError."""
    with pytest.raises(ValueError, match="currency must be a 3-letter"):
        MoneyValue(amount=Decimal("1"), currency=123)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_negative_precision_rejected() -> None:
    """Negative precision raises ValueError."""
    with pytest.raises(ValueError, match="precision must be non-negative"):
        MoneyValue(amount=Decimal("1"), currency="USD", precision=-1)


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_bool_precision_rejected() -> None:
    """Boolean precision raises TypeError (bool is not int)."""
    with pytest.raises(TypeError, match="precision must be an int"):
        MoneyValue(amount=Decimal("1"), currency="USD", precision=True)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_money_value_is_frozen() -> None:
    """MoneyValue is frozen."""
    m = MoneyValue(amount=Decimal("1"), currency="USD")
    with pytest.raises(BaseException):  # noqa: B017  (FrozenInstanceError)
        m.currency = "EUR"  # type: ignore[misc]


# --- CanonicalField: basic construction -------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_minimal_valid() -> None:
    """Minimal CanonicalField with only required attributes."""
    f = CanonicalField(
        id="field_1",
        path="supplier_name",
        name="supplier_name",
        type=FieldType.STRING,
        required=True,
    )
    assert f.id == "field_1"
    assert f.path == "supplier_name"
    assert f.name == "supplier_name"
    assert f.type is FieldType.STRING
    assert f.required is True
    assert f.critical is False
    assert f.nullable is False
    assert f.description is None
    assert f.confidence_threshold == 0.80
    assert f.evidence_required is False
    assert f.semantic_tags == ()
    assert f.enum_values is None
    assert f.default is None
    assert f.constraints == ()


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_all_optional_attributes() -> None:
    """CanonicalField with every optional attribute set."""
    f = CanonicalField(
        id="field_1",
        path="name",
        name="name",
        type=FieldType.STRING,
        required=True,
        critical=True,
        nullable=True,
        description="A field",
        confidence_threshold=0.95,
        evidence_required=True,
        semantic_tags=("pii",),
        fallback_policy=ResolutionPolicy(),
        default="hello",
        constraints=(),
    )
    assert f.critical is True
    assert f.nullable is True
    assert f.description == "A field"
    assert f.confidence_threshold == 0.95
    assert f.evidence_required is True
    assert f.semantic_tags == ("pii",)
    assert f.default == "hello"


@pytest.mark.deterministic
@pytest.mark.unit
@pytest.mark.parametrize(
    "field_type",
    [
        FieldType.STRING,
        FieldType.INTEGER,
        FieldType.DECIMAL,
        FieldType.BOOLEAN,
        FieldType.DATE,
        FieldType.OBJECT,
        FieldType.ARRAY,
    ],
)
def test_canonical_field_accepts_all_non_enum_types(field_type: FieldType) -> None:
    """All non-ENUM FieldType values are accepted (ENUM needs enum_values)."""
    f = CanonicalField(
        id="field_1",
        path="x",
        name="x",
        type=field_type,
        required=True,
    )
    assert f.type is field_type


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_enum_with_enum_values() -> None:
    """ENUM field with EnumValueSet is valid."""
    f = CanonicalField(
        id="field_1",
        path="status",
        name="status",
        type=FieldType.ENUM,
        required=True,
        enum_values=EnumValueSet(("active", "inactive")),
    )
    assert f.type is FieldType.ENUM
    assert f.enum_values is not None
    assert "active" in f.enum_values


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_enum_without_enum_values_raises() -> None:
    """ENUM field with enum_values=None raises ValueError."""
    with pytest.raises(ValueError, match=r"ENUM field.*must have non-None"):
        CanonicalField(
            id="field_1",
            path="status",
            name="status",
            type=FieldType.ENUM,
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_enum_with_non_enumvalue_set_raises() -> None:
    """ENUM field with non-EnumValueSet enum_values raises TypeError."""
    with pytest.raises(TypeError, match="enum_values must be an EnumValueSet"):
        CanonicalField(
            id="field_1",
            path="status",
            name="status",
            type=FieldType.ENUM,
            required=True,
            enum_values=("a", "b"),  # type: ignore[arg-type]
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_enum_values_on_non_enum_raises() -> None:
    """enum_values on a non-ENUM field raises ValueError."""
    with pytest.raises(ValueError, match="enum_values is only allowed for ENUM"):
        CanonicalField(
            id="field_1",
            path="name",
            name="name",
            type=FieldType.STRING,
            required=True,
            enum_values=EnumValueSet(("a",)),  # type: ignore[call-arg]
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_money_type_accepts_money_default() -> None:
    """MONEY field with MoneyValue default is valid."""
    f = CanonicalField(
        id="field_1",
        path="amount",
        name="amount",
        type=FieldType.MONEY,
        required=False,
        default=MoneyValue(amount=Decimal("0"), currency="USD"),
    )
    assert f.type is FieldType.MONEY
    assert isinstance(f.default, MoneyValue)


# --- CanonicalField: default validation -------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_string_default_wrong_type_raises() -> None:
    """STRING field with non-str default raises ValueError."""
    with pytest.raises(ValueError, match=r"STRING field.*default must be str"):
        _field("x", type_=FieldType.STRING, default=42)


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_integer_default_wrong_type_raises() -> None:
    """INTEGER field with non-int default raises ValueError."""
    with pytest.raises(ValueError, match=r"INTEGER field.*default must be int"):
        _field("x", type_=FieldType.INTEGER, default="five")


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_boolean_default_wrong_type_raises() -> None:
    """BOOLEAN field with non-bool default raises ValueError."""
    with pytest.raises(ValueError, match=r"BOOLEAN field.*default must be bool"):
        _field("x", type_=FieldType.BOOLEAN, default=1)


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_money_default_wrong_type_raises() -> None:
    """MONEY field with non-MoneyValue default raises ValueError."""
    with pytest.raises(ValueError, match=r"MONEY field.*default must be MoneyValue"):
        _field("x", type_=FieldType.MONEY, default=100)


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_object_default_wrong_type_raises() -> None:
    """OBJECT field with non-dict default raises ValueError."""
    with pytest.raises(ValueError, match=r"OBJECT field.*default must be a dict"):
        _field("x", type_=FieldType.OBJECT, default="not_a_dict")


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_array_default_wrong_type_raises() -> None:
    """ARRAY field with non-list default raises ValueError."""
    with pytest.raises(ValueError, match=r"ARRAY field.*default must be a list"):
        _field("x", type_=FieldType.ARRAY, default="not_a_list")


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_array_default_tuple_accepted() -> None:
    """ARRAY field with tuple default is accepted (tuple is list-like)."""
    f = _field("x", type_=FieldType.ARRAY, default=(1, 2, 3))
    assert f.default == (1, 2, 3)


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_object_default_dict_accepted() -> None:
    """OBJECT field with dict default is accepted."""
    f = _field("x", type_=FieldType.OBJECT, default={"key": "value"})
    assert f.default == {"key": "value"}


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_string_default_none_allowed() -> None:
    """default=None is always allowed (means 'no default')."""
    f = _field("x", type_=FieldType.STRING, default=None)
    assert f.default is None


# --- CanonicalField: id / path / name validation ----------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_empty_id_raises() -> None:
    """Empty id raises ValueError."""
    with pytest.raises(ValueError, match="id must be a non-empty string"):
        CanonicalField(
            id="",
            path="x",
            name="x",
            type=FieldType.STRING,
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_empty_path_raises() -> None:
    """Empty path raises ValueError."""
    with pytest.raises(ValueError, match="path must be a non-empty string"):
        CanonicalField(
            id="f1",
            path="",
            name="x",
            type=FieldType.STRING,
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_empty_name_raises() -> None:
    """Empty name raises ValueError."""
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        CanonicalField(
            id="f1",
            path="x",
            name="",
            type=FieldType.STRING,
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_name_with_dot_raises() -> None:
    """name containing '.' raises ValueError."""
    with pytest.raises(ValueError, match="name must not contain"):
        CanonicalField(
            id="f1",
            path="a.b",
            name="a.b",
            type=FieldType.STRING,
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_name_with_brackets_raises() -> None:
    """name containing '[]' raises ValueError."""
    with pytest.raises(ValueError, match="name must not contain"):
        CanonicalField(
            id="f1",
            path="a",
            name="a[]",
            type=FieldType.STRING,
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_path_with_invalid_chars_raises() -> None:
    """Path with invalid characters raises ValueError."""
    with pytest.raises(ValueError, match="path must match"):
        CanonicalField(
            id="f1",
            path="1abc",
            name="x",
            type=FieldType.STRING,
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_path_dotted_valid() -> None:
    """Dotted path (a.b) is valid."""
    f = CanonicalField(
        id="f1",
        path="a.b",
        name="b",
        type=FieldType.STRING,
        required=True,
    )
    assert f.path == "a.b"


# --- CanonicalField: type / required / confidence_threshold -----------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_non_fieldtype_raises() -> None:
    """type that is not a FieldType raises TypeError."""
    with pytest.raises(TypeError, match="type must be a FieldType"):
        CanonicalField(
            id="f1",
            path="x",
            name="x",
            type="STRING",  # type: ignore[arg-type]
            required=True,
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_required_non_bool_raises() -> None:
    """required that is not a bool raises TypeError."""
    with pytest.raises(TypeError, match="required must be a bool"):
        CanonicalField(
            id="f1",
            path="x",
            name="x",
            type=FieldType.STRING,
            required=1,  # type: ignore[arg-type]
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_confidence_threshold_above_one_raises() -> None:
    """confidence_threshold > 1.0 raises ValueError."""
    with pytest.raises(ValueError, match="confidence_threshold must be in"):
        _field("x", confidence_threshold=1.5)


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_confidence_threshold_below_zero_raises() -> None:
    """confidence_threshold < 0.0 raises ValueError."""
    with pytest.raises(ValueError, match="confidence_threshold must be in"):
        _field("x", confidence_threshold=-0.1)


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_confidence_threshold_zero_valid() -> None:
    """confidence_threshold=0.0 is valid (boundary)."""
    f = _field("x", confidence_threshold=0.0)
    assert f.confidence_threshold == 0.0


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_confidence_threshold_one_valid() -> None:
    """confidence_threshold=1.0 is valid (boundary)."""
    f = _field("x", confidence_threshold=1.0)
    assert f.confidence_threshold == 1.0


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_confidence_threshold_bool_rejected() -> None:
    """Boolean confidence_threshold raises TypeError (bool is not a number)."""
    with pytest.raises(TypeError, match="confidence_threshold must be a number"):
        _field("x", confidence_threshold=True)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_fallback_policy_wrong_type_raises() -> None:
    """Non-ResolutionPolicy fallback_policy raises TypeError."""
    with pytest.raises(TypeError, match="fallback_policy must be a ResolutionPolicy"):
        CanonicalField(
            id="f1",
            path="x",
            name="x",
            type=FieldType.STRING,
            required=True,
            fallback_policy="UNRESOLVED",  # type: ignore[arg-type]
        )


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_field_is_frozen() -> None:
    """CanonicalField is frozen."""
    f = _field("x")
    with pytest.raises(BaseException):  # noqa: B017  (FrozenInstanceError)
        f.required = False  # type: ignore[misc]


# --- CanonicalContract: basic construction ----------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_minimal_valid() -> None:
    """Minimal CanonicalContract with one field."""
    c = CanonicalContract(
        id="contract-1",
        fields=(_field("a"),),
    )
    assert c.id == "contract-1"
    assert c.version == "1"
    assert len(c.fields) == 1
    assert c.constraints == ()
    assert c.policies is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_with_version_and_policy() -> None:
    """CanonicalContract with custom version and policies."""
    from paxman.contract._types import ContractPolicy

    c = CanonicalContract(
        id="c1",
        fields=(_field("a"),),
        version="2",
        policies=ContractPolicy(confidence_floor=0.9),
    )
    assert c.version == "2"
    assert c.policies is not None
    assert c.policies.confidence_floor == 0.9


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_empty_fields_raises() -> None:
    """Empty fields tuple raises ValueError."""
    with pytest.raises(ValueError, match="at least one field"):
        CanonicalContract(id="c1", fields=())


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_empty_id_raises() -> None:
    """Empty id raises ValueError."""
    with pytest.raises(ValueError, match="id must be a non-empty string"):
        CanonicalContract(id="", fields=(_field("a"),))


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_empty_version_raises() -> None:
    """Empty version raises ValueError."""
    with pytest.raises(ValueError, match="version must be a non-empty string"):
        CanonicalContract(id="c1", fields=(_field("a"),), version="")


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_duplicate_field_id_raises() -> None:
    """Duplicate field id raises ValueError."""
    f1 = CanonicalField(id="dup", path="a", name="a", type=FieldType.STRING, required=True)
    f2 = CanonicalField(id="dup", path="b", name="b", type=FieldType.STRING, required=True)
    with pytest.raises(ValueError, match="duplicate field id"):
        CanonicalContract(id="c1", fields=(f1, f2))


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_duplicate_field_path_raises() -> None:
    """Duplicate field path raises ValueError."""
    f1 = CanonicalField(id="f1", path="same", name="a", type=FieldType.STRING, required=True)
    f2 = CanonicalField(id="f2", path="same", name="b", type=FieldType.STRING, required=True)
    with pytest.raises(ValueError, match="duplicate field path"):
        CanonicalContract(id="c1", fields=(f1, f2))


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_non_canonical_field_raises() -> None:
    """Non-CanoonicalField entry raises TypeError."""
    with pytest.raises(TypeError, match="fields must be CanonicalField"):
        CanonicalContract(id="c1", fields=("not_a_field",))  # type: ignore[list-item]


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_money_default_not_moneyvalue_raises() -> None:
    """MONEY field with non-MoneyValue default raises in contract construction.

    This is a defensive duplicate of the CanonicalField check; we bypass
    the field-level validation via object.__setattr__ to exercise the
    contract-level guard.
    """
    f = CanonicalField(
        id="f1",
        path="amount",
        name="amount",
        type=FieldType.MONEY,
        required=False,
    )
    object.__setattr__(f, "default", "not_a_money_value")
    with pytest.raises(ValueError, match=r"MONEY field.*default must be a MoneyValue"):
        CanonicalContract(id="c1", fields=(f,))


@pytest.mark.deterministic
@pytest.mark.unit
def test_canonical_contract_is_frozen() -> None:
    """CanonicalContract is frozen."""
    c = CanonicalContract(id="c1", fields=(_field("a"),))
    with pytest.raises(BaseException):  # noqa: B017  (FrozenInstanceError)
        c.id = "hack"  # type: ignore[misc]


# --- CanonicalContract: helpers ---------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_field_by_path_found() -> None:
    """field_by_path returns the matching field."""
    f1 = CanonicalField(id="f1", path="a", name="a", type=FieldType.STRING, required=True)
    f2 = CanonicalField(id="f2", path="b", name="b", type=FieldType.STRING, required=True)
    c = CanonicalContract(id="c1", fields=(f1, f2))
    assert c.field_by_path("a") is f1
    assert c.field_by_path("b") is f2


@pytest.mark.deterministic
@pytest.mark.unit
def test_field_by_path_not_found() -> None:
    """field_by_path returns None for a missing path."""
    c = CanonicalContract(id="c1", fields=(_field("a"),))
    assert c.field_by_path("missing") is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_field_by_id_found() -> None:
    """field_by_id returns the matching field."""
    f1 = CanonicalField(id="f1", path="a", name="a", type=FieldType.STRING, required=True)
    f2 = CanonicalField(id="f2", path="b", name="b", type=FieldType.STRING, required=True)
    c = CanonicalContract(id="c1", fields=(f1, f2))
    assert c.field_by_id("f1") is f1
    assert c.field_by_id("f2") is f2


@pytest.mark.deterministic
@pytest.mark.unit
def test_field_by_id_not_found() -> None:
    """field_by_id returns None for a missing id."""
    c = CanonicalContract(id="c1", fields=(_field("a"),))
    assert c.field_by_id("missing") is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_required_fields_returns_only_required() -> None:
    """required_fields returns fields with required=True."""
    f1 = CanonicalField(id="f1", path="a", name="a", type=FieldType.STRING, required=True)
    f2 = CanonicalField(id="f2", path="b", name="b", type=FieldType.STRING, required=False)
    f3 = CanonicalField(id="f3", path="c", name="c", type=FieldType.STRING, required=True)
    c = CanonicalContract(id="c1", fields=(f1, f2, f3))
    required = c.required_fields()
    assert len(required) == 2
    assert required[0] is f1
    assert required[1] is f3


@pytest.mark.deterministic
@pytest.mark.unit
def test_required_fields_empty_when_all_optional() -> None:
    """required_fields returns empty tuple when all fields are optional."""
    f1 = CanonicalField(id="f1", path="a", name="a", type=FieldType.STRING, required=False)
    c = CanonicalContract(id="c1", fields=(f1,))
    assert c.required_fields() == ()


@pytest.mark.deterministic
@pytest.mark.unit
def test_required_fields_preserves_order() -> None:
    """required_fields preserves declaration order."""
    fields = tuple(
        CanonicalField(id=f"f{i}", path=f"p{i}", name=f"n{i}", type=FieldType.STRING, required=True)
        for i in range(5)
    )
    c = CanonicalContract(id="c1", fields=fields)
    assert tuple(f.name for f in c.required_fields()) == tuple(f"n{i}" for i in range(5))

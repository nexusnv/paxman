"""Unit tests for ``paxman.contract._types`` — structural primitives.

Covers ConstraintKind (7 members), Constraint, ResolutionStrategy,
ResolutionPolicy, ContractPolicy, EnumValue, and EnumValueSet. Every public
attribute and post-init validator is exercised. Per Sprint 2 exit criteria
#6, ``contract/`` must achieve >=90% line coverage; this file contributes
the ``_types.py`` share.
"""

from __future__ import annotations

import pytest

from paxman.contract._types import (
    Constraint,
    ConstraintKind,
    ContractPolicy,
    EnumValue,
    EnumValueSet,
    ResolutionPolicy,
    ResolutionStrategy,
)

# --- ConstraintKind ---------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_kind_has_seven_members() -> None:
    """ConstraintKind has exactly 7 members (the V1 set)."""
    assert len(list(ConstraintKind)) == 7


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_kind_values_are_documented_strings() -> None:
    """Each ConstraintKind value matches the documented string literal."""
    expected = {
        "MIN_LENGTH": "min_length",
        "MAX_LENGTH": "max_length",
        "PATTERN": "pattern",
        "MIN_VALUE": "min_value",
        "MAX_VALUE": "max_value",
        "ENUM": "enum",
        "ISO_4217": "iso_4217",
    }
    for name, value in expected.items():
        member = ConstraintKind[name]
        assert member.value == value, f"{name} value mismatch: {member.value!r}"


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_kind_is_unique_enum() -> None:
    """ConstraintKind values are unique (no duplicates)."""
    values = [m.value for m in ConstraintKind]
    assert len(values) == len(set(values))


# --- Constraint -------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_minimal_construction() -> None:
    """Constraint with only kind uses default params={} and message=None."""
    c = Constraint(kind=ConstraintKind.MIN_LENGTH)
    assert c.kind is ConstraintKind.MIN_LENGTH
    assert c.params == {}
    assert c.message is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_with_params_and_message() -> None:
    """Constraint accepts params dict and message string."""
    c = Constraint(
        kind=ConstraintKind.MIN_LENGTH,
        params={"min": 5},
        message="too short",
    )
    assert c.params == {"min": 5}
    assert c.message == "too short"


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_default_params_are_independent_per_instance() -> None:
    """Default params dict is not shared across instances (attrs factory)."""
    c1 = Constraint(kind=ConstraintKind.PATTERN)
    c2 = Constraint(kind=ConstraintKind.PATTERN)
    c1.params["regex"] = "abc"
    assert "regex" not in c2.params, "default dict shared across instances"


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_post_init_raises_on_bad_kind() -> None:
    """__attrs_post_init__ raises TypeError when kind is not a ConstraintKind."""
    with pytest.raises(TypeError, match="kind must be a ConstraintKind"):
        Constraint(kind="min_length")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_post_init_raises_on_int_kind() -> None:
    """__attrs_post_init__ raises TypeError when kind is an int."""
    with pytest.raises(TypeError, match="kind must be a ConstraintKind"):
        Constraint(kind=42)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_post_init_raises_on_none_kind() -> None:
    """__attrs_post_init__ raises TypeError when kind is None."""
    with pytest.raises(TypeError, match="kind must be a ConstraintKind"):
        Constraint(kind=None)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_is_frozen() -> None:
    """Constraint is frozen; attribute assignment raises."""
    c = Constraint(kind=ConstraintKind.MIN_LENGTH)
    with pytest.raises(BaseException):  # noqa: B017  (FrozenInstanceError)
        c.message = "hack"  # type: ignore[misc]


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_equality() -> None:
    """Two Constraints with same attributes are equal."""
    c1 = Constraint(kind=ConstraintKind.PATTERN, params={"regex": "x"})
    c2 = Constraint(kind=ConstraintKind.PATTERN, params={"regex": "x"})
    assert c1 == c2


@pytest.mark.deterministic
@pytest.mark.unit
def test_constraint_inequality_different_params() -> None:
    """Constraints with different params are not equal."""
    c1 = Constraint(kind=ConstraintKind.PATTERN, params={"regex": "x"})
    c2 = Constraint(kind=ConstraintKind.PATTERN, params={"regex": "y"})
    assert c1 != c2


# --- ResolutionStrategy -----------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_strategy_has_three_values() -> None:
    """ResolutionStrategy has exactly 3 members."""
    assert len(list(ResolutionStrategy)) == 3


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_strategy_values() -> None:
    """ResolutionStrategy values match the documented SCREAMING_SNAKE_CASE."""
    expected = {"UNRESOLVED", "USE_DEFAULT", "REQUIRE_HUMAN"}
    actual = {m.name for m in ResolutionStrategy}
    assert actual == expected


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_strategy_string_values() -> None:
    """ResolutionStrategy values are uppercase strings."""
    for member in ResolutionStrategy:
        assert isinstance(member.value, str)
        assert member.value == member.value.upper()


# --- ResolutionPolicy -------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_policy_defaults() -> None:
    """ResolutionPolicy() defaults to UNRESOLVED, require_human_review=False."""
    p = ResolutionPolicy()
    assert p.strategy is ResolutionStrategy.UNRESOLVED
    assert p.require_human_review is False


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_policy_custom_strategy() -> None:
    """ResolutionPolicy accepts a custom strategy."""
    p = ResolutionPolicy(strategy=ResolutionStrategy.USE_DEFAULT)
    assert p.strategy is ResolutionStrategy.USE_DEFAULT


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_policy_require_human_review_true() -> None:
    """ResolutionPolicy accepts require_human_review=True."""
    p = ResolutionPolicy(require_human_review=True)
    assert p.require_human_review is True


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_policy_all_custom() -> None:
    """ResolutionPolicy with all custom values."""
    p = ResolutionPolicy(
        strategy=ResolutionStrategy.REQUIRE_HUMAN,
        require_human_review=True,
    )
    assert p.strategy is ResolutionStrategy.REQUIRE_HUMAN
    assert p.require_human_review is True


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_policy_raises_on_bad_strategy_type() -> None:
    """ResolutionPolicy raises TypeError when strategy is not a ResolutionStrategy."""
    with pytest.raises(TypeError, match="strategy must be a ResolutionStrategy"):
        ResolutionPolicy(strategy="UNRESOLVED")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_policy_raises_on_int_strategy() -> None:
    """ResolutionPolicy raises TypeError when strategy is an int."""
    with pytest.raises(TypeError, match="strategy must be a ResolutionStrategy"):
        ResolutionPolicy(strategy=1)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.unit
def test_resolution_policy_is_frozen() -> None:
    """ResolutionPolicy is frozen."""
    p = ResolutionPolicy()
    with pytest.raises(BaseException):  # noqa: B017  (FrozenInstanceError)
        p.require_human_review = True  # type: ignore[misc]


# --- ContractPolicy ---------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_defaults_all_none() -> None:
    """ContractPolicy() defaults all fields to None (inherit call-site)."""
    p = ContractPolicy()
    assert p.confidence_floor is None
    assert p.unresolved_acceptable is None
    assert p.stop_on_first_unresolved is None


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_custom_confidence_floor() -> None:
    """ContractPolicy accepts a custom confidence_floor."""
    p = ContractPolicy(confidence_floor=0.85)
    assert p.confidence_floor == 0.85


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_custom_unresolved_acceptable() -> None:
    """ContractPolicy accepts unresolved_acceptable=True."""
    p = ContractPolicy(unresolved_acceptable=True)
    assert p.unresolved_acceptable is True


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_custom_stop_on_first_unresolved() -> None:
    """ContractPolicy accepts stop_on_first_unresolved=True."""
    p = ContractPolicy(stop_on_first_unresolved=True)
    assert p.stop_on_first_unresolved is True


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_all_custom() -> None:
    """ContractPolicy with all custom values."""
    p = ContractPolicy(
        confidence_floor=0.90,
        unresolved_acceptable=True,
        stop_on_first_unresolved=True,
    )
    assert p.confidence_floor == 0.90
    assert p.unresolved_acceptable is True
    assert p.stop_on_first_unresolved is True


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_confidence_floor_zero_is_valid() -> None:
    """confidence_floor=0.0 is valid (boundary)."""
    p = ContractPolicy(confidence_floor=0.0)
    assert p.confidence_floor == 0.0


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_confidence_floor_one_is_valid() -> None:
    """confidence_floor=1.0 is valid (boundary)."""
    p = ContractPolicy(confidence_floor=1.0)
    assert p.confidence_floor == 1.0


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_confidence_floor_above_one_raises() -> None:
    """confidence_floor > 1.0 raises ValueError."""
    with pytest.raises(ValueError, match="confidence_floor must be in"):
        ContractPolicy(confidence_floor=1.01)


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_confidence_floor_below_zero_raises() -> None:
    """confidence_floor < 0.0 raises ValueError."""
    with pytest.raises(ValueError, match="confidence_floor must be in"):
        ContractPolicy(confidence_floor=-0.01)


@pytest.mark.deterministic
@pytest.mark.unit
def test_contract_policy_is_frozen() -> None:
    """ContractPolicy is frozen."""
    p = ContractPolicy(confidence_floor=0.5)
    with pytest.raises(BaseException):  # noqa: B017  (FrozenInstanceError)
        p.confidence_floor = 0.9  # type: ignore[misc]


# --- EnumValue --------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_eq_against_enum_value() -> None:
    """EnumValue equals another EnumValue with the same underlying value."""
    assert EnumValue("active") == EnumValue("active")
    assert not (EnumValue("active") == EnumValue("inactive"))


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_eq_against_raw_value() -> None:
    """EnumValue equals its raw underlying value."""
    assert EnumValue("active") == "active"
    assert not (EnumValue("active") == "inactive")


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_eq_int_value() -> None:
    """EnumValue with an int value equals that int."""
    assert EnumValue(42) == 42
    assert not (EnumValue(42) == 43)


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_eq_unequal_value() -> None:
    """EnumValue does not equal a different value."""
    assert EnumValue("a") != "b"
    assert EnumValue("a") != EnumValue("b")


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_hash_matches_raw_value() -> None:
    """hash(EnumValue('x')) == hash('x') (interchangeable in sets/dicts)."""
    assert hash(EnumValue("x")) == hash("x")


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_hash_int() -> None:
    """hash(EnumValue(42)) == hash(42)."""
    assert hash(EnumValue(42)) == hash(42)


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_str_returns_underlying_str() -> None:
    """str(EnumValue('active')) == 'active'."""
    assert str(EnumValue("active")) == "active"


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_str_int_value() -> None:
    """str(EnumValue(42)) == '42'."""
    assert str(EnumValue(42)) == "42"


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_repr() -> None:
    """repr shows the underlying value."""
    r = repr(EnumValue("active"))
    assert "EnumValue" in r
    assert "'active'" in r


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_usable_in_set() -> None:
    """EnumValue and raw value are interchangeable in a set."""
    s = {EnumValue("a"), "a", EnumValue("b")}
    assert len(s) == 2  # EnumValue("a") and "a" hash to the same slot


# --- EnumValueSet -----------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_basic_construction() -> None:
    """EnumValueSet with a list of values."""
    s = EnumValueSet(("active", "inactive"))
    assert len(s) == 2


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_preserves_order() -> None:
    """EnumValueSet preserves insertion order."""
    s = EnumValueSet(("c", "a", "b"))
    assert tuple(s) == ("c", "a", "b")


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_dedup_duplicates() -> None:
    """EnumValueSet silently deduplicates repeated values."""
    s = EnumValueSet(("a", "b", "a", "c", "b"))
    assert len(s) == 3
    assert tuple(s) == ("a", "b", "c")


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_contains_raw_value() -> None:
    """``value in set`` returns True for raw values."""
    s = EnumValueSet(("active", "inactive"))
    assert "active" in s
    assert "inactive" in s


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_contains_enum_value() -> None:
    """``EnumValue in set`` returns True."""
    s = EnumValueSet(("active", "inactive"))
    assert EnumValue("active") in s
    assert EnumValue("inactive") in s


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_not_contains_missing() -> None:
    """Missing value returns False."""
    s = EnumValueSet(("active",))
    assert "missing" not in s
    assert EnumValue("missing") not in s


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_iter() -> None:
    """__iter__ yields values in deterministic order."""
    s = EnumValueSet(("b", "a"))
    assert list(s) == ["b", "a"]


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_len() -> None:
    """__len__ returns the count of deduplicated values."""
    s = EnumValueSet(("a", "a", "b"))
    assert len(s) == 2


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_empty_raises() -> None:
    """Empty EnumValueSet raises ValueError."""
    with pytest.raises(ValueError, match="at least one value"):
        EnumValueSet(())


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_single_value() -> None:
    """Single-value enum is valid."""
    s = EnumValueSet(("only",))
    assert len(s) == 1
    assert "only" in s


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_repr() -> None:
    """repr shows the values tuple."""
    s = EnumValueSet(("a", "b"))
    r = repr(s)
    assert "EnumValueSet" in r
    assert "values" in r


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_int_values() -> None:
    """EnumValueSet with integer values."""
    s = EnumValueSet((1, 2, 3))
    assert len(s) == 3
    assert 2 in s
    assert 4 not in s


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_accepts_list_input() -> None:
    """EnumValueSet accepts a list (converter=tuple)."""
    s = EnumValueSet(["a", "b"])
    assert len(s) == 2
    assert tuple(s) == ("a", "b")


@pytest.mark.deterministic
@pytest.mark.unit
def test_enum_value_set_dedup_with_enum_value_objects() -> None:
    """EnumValueSet deduplicates EnumValue objects by underlying value."""
    s = EnumValueSet((EnumValue("a"), EnumValue("a"), EnumValue("b")))
    assert len(s) == 2

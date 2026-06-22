"""Unit tests for ``paxman.types`` — Status, ConfidenceBand, FieldType enums."""

from __future__ import annotations

import enum

import pytest

from paxman.types import ConfidenceBand, FieldType, Status

# --- Status -----------------------------------------------------------------


@pytest.mark.deterministic
def test_status_inherits_from_enum() -> None:
    """``Status`` is an ``enum.Enum`` subclass."""
    assert issubclass(Status, enum.Enum)


@pytest.mark.deterministic
def test_status_has_five_members() -> None:
    """``Status`` has exactly 5 members."""
    assert len(list(Status)) == 5


@pytest.mark.deterministic
def test_status_values() -> None:
    """``Status`` values match the spec (ARCHITECTURE.md §6.1)."""
    names = {m.name for m in Status}
    assert names == {
        "SUCCESS",
        "PARTIAL_SUCCESS",
        "UNRESOLVED",
        "INVALID_CONTRACT",
        "EXECUTION_FAILED",
    }


@pytest.mark.deterministic
def test_status_string_values() -> None:
    """``Status`` values are strings (artifact JSON format)."""
    for member in Status:
        assert isinstance(member.value, str)


# --- ConfidenceBand ---------------------------------------------------------


@pytest.mark.deterministic
def test_confidence_band_inherits_from_enum() -> None:
    assert issubclass(ConfidenceBand, enum.Enum)


@pytest.mark.deterministic
def test_confidence_band_has_five_members() -> None:
    assert len(list(ConfidenceBand)) == 5


@pytest.mark.deterministic
def test_confidence_band_values() -> None:
    """``ConfidenceBand`` values match ADR-0005."""
    names = {m.name for m in ConfidenceBand}
    assert names == {"CERTAIN", "HIGH", "MEDIUM", "LOW", "UNTRUSTED"}


@pytest.mark.deterministic
def test_confidence_band_string_values() -> None:
    for member in ConfidenceBand:
        assert isinstance(member.value, str)


# --- FieldType --------------------------------------------------------------


@pytest.mark.deterministic
def test_field_type_inherits_from_enum() -> None:
    assert issubclass(FieldType, enum.Enum)


@pytest.mark.deterministic
def test_field_type_has_nine_members() -> None:
    """``FieldType`` has exactly 9 members (the V1 set)."""
    assert len(list(FieldType)) == 9


@pytest.mark.deterministic
def test_field_type_values() -> None:
    """``FieldType`` values match the canonical V1 set (ARCHITECTURE.md §4.1)."""
    names = {m.name for m in FieldType}
    assert names == {
        "STRING",
        "INTEGER",
        "DECIMAL",
        "BOOLEAN",
        "DATE",
        "ENUM",
        "OBJECT",
        "ARRAY",
        "MONEY",
    }


@pytest.mark.deterministic
def test_field_type_string_values() -> None:
    for member in FieldType:
        assert isinstance(member.value, str)


@pytest.mark.deterministic
def test_field_type_money_is_first_class() -> None:
    """``MONEY`` is a V1 field type per ADR-0004 (not a tagged DECIMAL)."""
    assert FieldType.MONEY.value == "MONEY"
    assert FieldType.MONEY in FieldType


# --- Enum integrity (uniqueness) -------------------------------------------


@pytest.mark.deterministic
def test_all_enums_are_unique() -> None:
    """All three enums have unique values within themselves (no duplicates)."""
    for enum_cls in (Status, ConfidenceBand, FieldType):
        values = [m.value for m in enum_cls]
        assert len(values) == len(set(values)), f"{enum_cls.__name__} has duplicate values"

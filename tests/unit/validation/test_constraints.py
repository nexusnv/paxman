"""Tests for the extracted check_constraint helper (issue #64)."""

from __future__ import annotations

import typing

from paxman.contract._types import Constraint, ConstraintKind
from paxman.validation.constraints import check_constraint


def test_check_constraint_passes_when_value_meets_constraint() -> None:
    """A passing constraint returns (True, '')."""
    constraint = Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0})
    passed, reason = check_constraint(constraint, 5)
    assert passed is True
    assert reason == ""


def test_check_constraint_fails_when_value_violates_constraint() -> None:
    """A failing constraint returns (False, reason-with-the-kind)."""
    constraint = Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0})
    passed, reason = check_constraint(constraint, -1)
    assert passed is False
    assert reason != ""
    assert "min" in reason.lower()


def test_check_constraint_pattern_pass() -> None:
    """A matching PATTERN constraint passes."""
    constraint = Constraint(kind=ConstraintKind.PATTERN, params={"regex": r"^\d+$"})
    passed, reason = check_constraint(constraint, "12345")
    assert passed is True
    assert reason == ""


def test_check_constraint_pattern_fail() -> None:
    """A non-matching PATTERN constraint fails."""
    constraint = Constraint(kind=ConstraintKind.PATTERN, params={"regex": r"^\d+$"})
    passed, reason = check_constraint(constraint, "abc")
    assert passed is False
    assert "pattern" in reason.lower() or "match" in reason.lower()


def test_check_constraint_enum_pass() -> None:
    """A value in the ENUM set passes."""
    constraint = Constraint(kind=ConstraintKind.ENUM, params={"values": ["a", "b", "c"]})
    passed, reason = check_constraint(constraint, "b")
    assert passed is True
    assert reason == ""


def test_check_constraint_enum_fail() -> None:
    """A value NOT in the ENUM set fails."""
    constraint = Constraint(kind=ConstraintKind.ENUM, params={"values": ["a", "b", "c"]})
    passed, reason = check_constraint(constraint, "z")
    assert passed is False
    assert "enum" in reason.lower() or "not in" in reason.lower()


def test_check_constraint_iso_4217_pass() -> None:
    """A valid ISO-4217 code passes."""
    constraint = Constraint(kind=ConstraintKind.ISO_4217, params={})
    passed, reason = check_constraint(constraint, "USD")
    assert passed is True
    assert reason == ""


def test_check_constraint_iso_4217_fail() -> None:
    """An invalid ISO-4217 code fails."""
    constraint = Constraint(kind=ConstraintKind.ISO_4217, params={})
    passed, reason = check_constraint(constraint, "usd")
    assert passed is False
    assert "iso" in reason.lower() or "4217" in reason.lower()


def test_check_constraint_max_value_pass() -> None:
    """A value within MAX_VALUE passes."""
    constraint = Constraint(kind=ConstraintKind.MAX_VALUE, params={"max": 100})
    passed, reason = check_constraint(constraint, 50)
    assert passed is True
    assert reason == ""


def test_check_constraint_max_value_fail() -> None:
    """A value exceeding MAX_VALUE fails."""
    constraint = Constraint(kind=ConstraintKind.MAX_VALUE, params={"max": 100})
    passed, reason = check_constraint(constraint, 200)
    assert passed is False
    assert "max" in reason.lower()


def test_check_constraint_min_length_pass() -> None:
    """A string meeting MIN_LENGTH passes."""
    constraint = Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 3})
    passed, reason = check_constraint(constraint, "hello")
    assert passed is True
    assert reason == ""


def test_check_constraint_min_length_fail() -> None:
    """A string shorter than MIN_LENGTH fails."""
    constraint = Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 10})
    passed, reason = check_constraint(constraint, "hi")
    assert passed is False
    assert "length" in reason.lower() or "min" in reason.lower()


def test_check_constraint_max_length_pass() -> None:
    """A string within MAX_LENGTH passes."""
    constraint = Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 10})
    passed, reason = check_constraint(constraint, "hello")
    assert passed is True
    assert reason == ""


def test_check_constraint_max_length_fail() -> None:
    """A string exceeding MAX_LENGTH fails."""
    constraint = Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 3})
    passed, reason = check_constraint(constraint, "hello world")
    assert passed is False
    assert "length" in reason.lower() or "max" in reason.lower()


def test_check_constraint_unknown_kind_is_noop() -> None:
    """Unknown constraint kinds return (True, '') — V1 no-op.

    The default-branch of `check_constraint` is exercised when a
    constraint's `kind` is not one of the 7 known `ConstraintKind`
    enum values. The function should treat unknown kinds as a
    no-op (V1 invariant: the contract layer catches unknown kinds
    at validation time; this is a defensive default).
    """

    class _FakeConstraint:
        """A constraint-like object whose kind is not a ConstraintKind enum."""

        kind = "not_a_real_constraint_kind"
        params: typing.ClassVar[dict[str, object]] = {}

    passed, reason = check_constraint(_FakeConstraint(), "anything")
    assert passed is True
    assert reason == ""

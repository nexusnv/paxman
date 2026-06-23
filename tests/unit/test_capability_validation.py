"""Unit tests for :mod:`paxman.capabilities.v1.validation`.

Per Sprint 3 D3.14: ``validation`` checks a candidate value against
the constraints on the target field. V1 supports type, range, regex,
enum, and (per the Sprint 3 risk register) ISO-4217 constraints.
Reference constraints are post-V1.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.validation import ValidationCapability
from paxman.contract._types import Constraint, ConstraintKind

pytestmark = pytest.mark.unit


def _ctx(
    value: object,
    constraints: tuple[Constraint, ...] = (),
    field_path: str = "supplier_name",
) -> CapabilityContext:
    return CapabilityContext(
        raw_input=b"",
        field_path=field_path,
        field_type_name="STRING",
        config={"value": value, "constraints": constraints},
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    """The spec is validation@1.0, LOCAL_DETERMINISTIC, free, accepts all types."""
    cap = ValidationCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "validation"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    # All 9 V1 types accepted.
    assert set(spec.input_types) == {
        "STRING",
        "INTEGER",
        "DECIMAL",
        "BOOLEAN",
        "DATE",
        "ENUM",
        "MONEY",
        "ARRAY",
        "OBJECT",
    }


# --- min_length / max_length ---------------------------------------------


def test_min_length_passes() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "ACME Corp",
            (Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),),
        )
    )
    assert result.candidates[0].value == "ACME Corp"
    assert result.diagnostics == ()


def test_min_length_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "",
            (Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_max_length_passes() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "hi",
            (Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 5}),),
        )
    )
    assert result.diagnostics == ()


def test_max_length_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "hello world",
            (Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 5}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


# --- pattern --------------------------------------------------------------


def test_pattern_passes() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "USD",
            (Constraint(kind=ConstraintKind.PATTERN, params={"regex": r"^[A-Z]{3}$"}),),
        )
    )
    assert result.diagnostics == ()


def test_pattern_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "usd",
            (Constraint(kind=ConstraintKind.PATTERN, params={"regex": r"^[A-Z]{3}$"}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


# --- min_value / max_value -----------------------------------------------


def test_min_value_passes() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            5,
            (Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0}),),
        )
    )
    assert result.diagnostics == ()


def test_min_value_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            -1,
            (Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_max_value_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            200,
            (Constraint(kind=ConstraintKind.MAX_VALUE, params={"max": 100}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_min_value_rejects_non_numeric() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "not a number",
            (Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


# --- enum -----------------------------------------------------------------


def test_enum_passes() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "USD",
            (
                Constraint(
                    kind=ConstraintKind.ENUM,
                    params={"values": ["USD", "EUR", "GBP"]},
                ),
            ),
        )
    )
    assert result.diagnostics == ()


def test_enum_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "XYZ",
            (
                Constraint(
                    kind=ConstraintKind.ENUM,
                    params={"values": ["USD", "EUR", "GBP"]},
                ),
            ),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


# --- iso_4217 -------------------------------------------------------------


def test_iso_4217_passes() -> None:
    cap = ValidationCapability()
    result = cap.invoke(_ctx("USD", (Constraint(kind=ConstraintKind.ISO_4217, params={}),)))
    assert result.diagnostics == ()


def test_iso_4217_fails_lowercase() -> None:
    cap = ValidationCapability()
    result = cap.invoke(_ctx("usd", (Constraint(kind=ConstraintKind.ISO_4217, params={}),)))
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_iso_4217_fails_too_long() -> None:
    cap = ValidationCapability()
    result = cap.invoke(_ctx("USDD", (Constraint(kind=ConstraintKind.ISO_4217, params={}),)))
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


# --- multiple constraints -------------------------------------------------


def test_multiple_constraints_all_pass() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "ACME Corp",
            (
                Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),
                Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 100}),
            ),
        )
    )
    assert result.diagnostics == ()


def test_multiple_constraints_some_fail() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "",
            (
                Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),
                Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": 100}),
            ),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED
    assert len(result.diagnostics[0].context["failures"]) == 1


# --- error path -----------------------------------------------------------


def test_invalid_constraints_type() -> None:
    """A non-tuple constraints arg returns an error diagnostic."""
    cap = ValidationCapability()
    ctx = CapabilityContext(
        raw_input=b"",
        field_path="x",
        field_type_name="STRING",
        config={"value": "x", "constraints": "not a tuple"},
    )
    result = cap.invoke(ctx)
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_duck_typed_constraint_rejected() -> None:
    """A non-Constraint object in the constraints list produces a failure."""

    class _NotAConstraint:
        pass

    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "x",
            (_NotAConstraint(),),  # type: ignore[arg-type]
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED
    assert "<unknown>" in result.diagnostics[0].context["failures"][0]["kind"]


def test_min_length_with_non_length_value() -> None:
    """A min_length constraint on a value without __len__ fails."""
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            42,  # int has no __len__
            (Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_min_value_bool_rejected() -> None:
    """A bool value is rejected by min_value (avoid bool-as-int trap)."""
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            True,
            (Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_max_value_bool_rejected() -> None:
    """A bool value is rejected by max_value (avoid bool-as-int trap)."""
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            True,
            (Constraint(kind=ConstraintKind.MAX_VALUE, params={"max": 100}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_pattern_with_invalid_regex_fails_cleanly() -> None:
    """A pattern with an unparseable regex produces a failure diagnostic."""
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "x",
            (Constraint(kind=ConstraintKind.PATTERN, params={"regex": r"(unclosed"}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_pattern_with_non_string_value_fails() -> None:
    """A pattern constraint on a non-string value fails."""
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            42,  # not a str
            (Constraint(kind=ConstraintKind.PATTERN, params={"regex": r"^x$"}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_pattern_with_no_regex_param_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "x",
            (Constraint(kind=ConstraintKind.PATTERN, params={}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_enum_with_no_values_list_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "x",
            (Constraint(kind=ConstraintKind.ENUM, params={}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_iso_4217_with_non_string_value_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            42,
            (Constraint(kind=ConstraintKind.ISO_4217, params={}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


def test_min_value_with_string_value_parses() -> None:
    """A numeric string parses via float()."""
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "5",
            (Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0}),),
        )
    )
    assert result.diagnostics == ()


def test_min_value_with_unparseable_string_fails() -> None:
    cap = ValidationCapability()
    result = cap.invoke(
        _ctx(
            "not a number",
            (Constraint(kind=ConstraintKind.MIN_VALUE, params={"min": 0}),),
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.VALIDATION_FAILED


# --- determinism ---------------------------------------------------------


@pytest.mark.deterministic
def test_validation_is_deterministic() -> None:
    cap = ValidationCapability()
    constraints = (Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),)
    r1 = cap.invoke(_ctx("ACME", constraints))
    r2 = cap.invoke(_ctx("ACME", constraints))
    assert r1.diagnostics == r2.diagnostics
    assert r1.candidates[0].value == r2.candidates[0].value

"""Unit tests for :mod:`paxman.planner.field_plan`."""

from __future__ import annotations

import pytest

from paxman.contract._types import ResolutionPolicy
from paxman.planner.field_plan import (
    ExecutionPlan,
    FieldPlan,
    FieldPlanStep,
    PlanDiagnostic,
)
from paxman.versioning import PLANNER_VERSION

pytestmark = pytest.mark.unit


# --- FieldPlanStep --------------------------------------------------------


def test_step_minimal() -> None:
    s = FieldPlanStep(capability_id="regex_extraction", capability_version="1.0")
    assert s.config == {}
    assert s.note == ""


def test_step_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="capability_id must be a non-empty string"):
        FieldPlanStep(capability_id="", capability_version="1.0")


def test_step_rejects_uppercase_id() -> None:
    with pytest.raises(ValueError, match="capability_id must be lowercase ASCII"):
        FieldPlanStep(capability_id="Regex_Extraction", capability_version="1.0")


def test_step_rejects_empty_version() -> None:
    with pytest.raises(ValueError, match="capability_version must be a non-empty string"):
        FieldPlanStep(capability_id="x", capability_version="")


def test_step_rejects_non_dict_config() -> None:
    with pytest.raises(TypeError, match="config must be a dict"):
        FieldPlanStep(
            capability_id="x",
            capability_version="1.0",
            config=[],  # type: ignore[arg-type]
        )


# --- FieldPlan ------------------------------------------------------------


def test_field_plan_minimal() -> None:
    fp = FieldPlan(field_id="f1")
    assert fp.target_confidence == 0.8
    assert fp.fallback_policy == ResolutionPolicy()
    assert fp.early_stop is True
    assert fp.capability_chain == ()


def test_field_plan_with_chain() -> None:
    fp = FieldPlan(
        field_id="f1",
        capability_chain=(
            FieldPlanStep(capability_id="regex_extraction", capability_version="1.0"),
        ),
        target_confidence=0.85,
    )
    assert len(fp.capability_chain) == 1
    assert fp.target_confidence == 0.85


def test_field_plan_rejects_empty_field_id() -> None:
    with pytest.raises(ValueError, match="field_id must be a non-empty string"):
        FieldPlan(field_id="")


def test_field_plan_rejects_invalid_target_confidence() -> None:
    with pytest.raises(ValueError, match="target_confidence must be in"):
        FieldPlan(field_id="f1", target_confidence=1.5)
    with pytest.raises(ValueError, match="target_confidence must be in"):
        FieldPlan(field_id="f1", target_confidence=-0.1)


def test_field_plan_rejects_non_field_plan_in_chain() -> None:
    with pytest.raises(TypeError, match="capability_chain entries must be FieldPlanStep"):
        FieldPlan(field_id="f1", capability_chain=("not a step",))  # type: ignore[arg-type]


# --- PlanDiagnostic -------------------------------------------------------


def test_diagnostic_minimal() -> None:
    d = PlanDiagnostic(code="FIELD_UNRESOLVED", message="no chain")
    assert d.field_id is None
    assert d.context == {}


def test_diagnostic_rejects_empty_code() -> None:
    with pytest.raises(ValueError, match="code must be a non-empty string"):
        PlanDiagnostic(code="", message="x")


# --- ExecutionPlan --------------------------------------------------------


def test_execution_plan_minimal() -> None:
    plan = ExecutionPlan(
        field_plans=(FieldPlan(field_id="f1"),),
        input_content_hash="a" * 64,
        contract_id="invoice",
    )
    assert plan.planner_version == PLANNER_VERSION
    assert plan.diagnostics == ()


def test_execution_plan_rejects_duplicate_field_id() -> None:
    with pytest.raises(ValueError, match="duplicate field_id"):
        ExecutionPlan(
            field_plans=(FieldPlan(field_id="f1"), FieldPlan(field_id="f1")),
            input_content_hash="a" * 64,
        )


def test_execution_plan_rejects_short_hash() -> None:
    with pytest.raises(ValueError, match="input_content_hash must be 64 hex chars"):
        ExecutionPlan(
            field_plans=(FieldPlan(field_id="f1"),),
            input_content_hash="abc",
        )


def test_execution_plan_rejects_non_hex_hash() -> None:
    """A 64-character hash that contains non-hex characters is rejected."""
    bad_hash = "z" * 64  # 64 chars but not hex
    with pytest.raises(ValueError, match="input_content_hash must be 64 lowercase hex chars"):
        ExecutionPlan(
            field_plans=(FieldPlan(field_id="f1"),),
            input_content_hash=bad_hash,
        )


def test_execution_plan_rejects_uppercase_hex() -> None:
    """A 64-character hash with uppercase characters is rejected."""
    bad_hash = "A" * 64
    with pytest.raises(ValueError, match="input_content_hash must be 64 lowercase hex chars"):
        ExecutionPlan(
            field_plans=(FieldPlan(field_id="f1"),),
            input_content_hash=bad_hash,
        )


def test_execution_plan_rejects_non_plan_diagnostic_in_diagnostics() -> None:
    """A non-PlanDiagnostic in the diagnostics tuple is rejected."""
    with pytest.raises(TypeError, match="diagnostics entries must be PlanDiagnostic"):
        ExecutionPlan(
            field_plans=(FieldPlan(field_id="f1"),),
            input_content_hash="a" * 64,
            diagnostics=("not a PlanDiagnostic",),  # type: ignore[arg-type]
        )


def test_execution_plan_allows_empty_hash() -> None:
    """An empty input_content_hash is allowed (e.g., for tests)."""
    plan = ExecutionPlan(
        field_plans=(FieldPlan(field_id="f1"),),
        input_content_hash="",
    )
    assert plan.input_content_hash == ""


def test_execution_plan_rejects_non_field_plan() -> None:
    with pytest.raises(TypeError, match="field_plans entries must be FieldPlan"):
        ExecutionPlan(
            field_plans=("not a FieldPlan",),  # type: ignore[arg-type]
            input_content_hash="a" * 64,
        )


def test_execution_plan_is_frozen() -> None:
    """ExecutionPlan is frozen (immutable)."""
    import attrs.exceptions

    plan = ExecutionPlan(
        field_plans=(FieldPlan(field_id="f1"),),
        input_content_hash="a" * 64,
    )
    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        plan.contract_id = "new"  # type: ignore[misc]

"""Unit tests for :mod:`paxman.executor.execution_state`.

Per Sprint 4 D4.1: ``ExecutionState`` is the Executor's
transient in-flight state. The tests pin the invariants
recorded in the module's docstring.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.capabilities.result import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.executor.execution_state import ExecutionState
from paxman.planner.field_plan import FieldPlan

pytestmark = pytest.mark.unit


def _empty_state() -> ExecutionState:
    """Build a fresh ``ExecutionState`` with no field plans."""
    return ExecutionState()


def _one_field_state() -> ExecutionState:
    """Build a state with one ``FieldPlan`` registered."""
    fp = FieldPlan(field_id="f1", capability_chain=())
    state = ExecutionState(field_plans={"f1": fp})
    state.init_field("f1")
    return state


# --- defaults ----------------------------------------------------------


def test_defaults_are_zero() -> None:
    s = _empty_state()
    assert s.total_cost_usd == 0.0
    assert s.total_latency_ms == 0
    assert s.invocation_count == 0
    assert s.remote_inference_count == 0
    assert s.budget_exceeded is False
    assert s.budget_exceeded_reason is None
    assert s.diagnostics == []
    assert s.evidence == []


# --- record_invocation -----------------------------------------------


def test_record_invocation_increments_counters() -> None:
    s = _empty_state()
    s.record_invocation(cost_usd=0.001, latency_ms=100, is_remote_inference=True)
    # ``total_cost_usd`` is ``Decimal`` (MONEY is Decimal per
    # ADR-0004 / ADR-0010). Use exact ``Decimal`` comparison.
    assert s.total_cost_usd == Decimal("0.001")
    assert s.total_latency_ms == 100
    assert s.invocation_count == 1
    assert s.remote_inference_count == 1


def test_record_invocation_accumulates() -> None:
    s = _empty_state()
    s.record_invocation(cost_usd=0.001, latency_ms=100)
    s.record_invocation(cost_usd=0.002, latency_ms=200, is_remote_inference=True)
    assert s.total_cost_usd == Decimal("0.003")
    assert s.total_latency_ms == 300
    assert s.invocation_count == 2
    assert s.remote_inference_count == 1


def test_record_invocation_rejects_negative_cost() -> None:
    s = _empty_state()
    with pytest.raises(ValueError, match="cost_usd must be non-negative"):
        s.record_invocation(cost_usd=-0.001)


def test_record_invocation_rejects_negative_latency() -> None:
    s = _empty_state()
    with pytest.raises(ValueError, match="latency_ms must be non-negative"):
        s.record_invocation(latency_ms=-1)


# --- mark_budget_exceeded --------------------------------------------


def test_mark_budget_exceeded_sets_flag_and_reason() -> None:
    s = _empty_state()
    s.mark_budget_exceeded("max_total_cost_usd")
    assert s.budget_exceeded is True
    assert s.budget_exceeded_reason == "max_total_cost_usd"


# --- add_diagnostic ---------------------------------------------------


def test_add_diagnostic_appends() -> None:
    s = _empty_state()
    d = Diagnostic(
        code=DiagnosticCode.PATTERN_NO_MATCH,
        severity=DiagnosticSeverity.INFO,
        message="no match",
    )
    s.add_diagnostic(d)
    assert s.diagnostics == [d]


def test_add_diagnostic_rejects_non_diagnostic() -> None:
    s = _empty_state()
    with pytest.raises(TypeError, match="diagnostic must be a Diagnostic"):
        s.add_diagnostic("not a diagnostic")  # type: ignore[arg-type]


# --- add_evidence ----------------------------------------------------


def test_add_evidence_appends() -> None:
    s = _empty_state()
    e = EvidenceRef(
        capability_id="text_extraction",
        capability_version="1.0",
        field_path="supplier_name",
    )
    s.add_evidence(e)
    assert s.evidence == [e]


def test_add_evidence_rejects_non_evidence_ref() -> None:
    s = _empty_state()
    with pytest.raises(TypeError, match="evidence must be an EvidenceRef"):
        s.add_evidence("not an evidence ref")  # type: ignore[arg-type]


# --- init_field / get_field_results ---------------------------------


def test_init_field_idempotent() -> None:
    s = _empty_state()
    s.init_field("f1")
    s.init_field("f1")  # idempotent
    assert s.get_field_results("f1") == []


def test_get_field_results_unknown_field_returns_empty_list() -> None:
    s = _empty_state()
    assert s.get_field_results("missing") == []


def test_get_field_results_returns_initialized_list() -> None:
    s = _one_field_state()
    s.field_results["f1"].append("a result")
    s.field_results["f1"].append("b result")
    results = s.get_field_results("f1")
    assert results == ["a result", "b result"]

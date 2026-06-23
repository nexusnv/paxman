"""Unit tests for :mod:`paxman.executor.early_stop`.

Per Sprint 4 D4.5: V1 early-stop is chain-exhaustion only. The
tests pin the contract that ``should_stop`` returns
``CHAIN_EXHAUSTED`` only when the next step index is past the
end of the chain.
"""

from __future__ import annotations

import pytest

from paxman.executor.early_stop import EarlyStop, StopDecision
from paxman.planner.field_plan import FieldPlan, FieldPlanStep

pytestmark = pytest.mark.unit


def _field_plan(*step_ids: str) -> FieldPlan:
    """Build a FieldPlan with the given step ids."""
    return FieldPlan(
        field_id="f1",
        capability_chain=tuple(
            FieldPlanStep(capability_id=s, capability_version="1.0") for s in step_ids
        ),
    )


# --- should_stop ------------------------------------------------------


def test_should_stop_continue_when_chain_has_steps() -> None:
    es = EarlyStop()
    fp = _field_plan("a", "b", "c")
    assert es.should_stop(field_plan=fp, current_step_index=0) is StopDecision.CONTINUE
    assert es.should_stop(field_plan=fp, current_step_index=1) is StopDecision.CONTINUE
    assert es.should_stop(field_plan=fp, current_step_index=2) is StopDecision.CONTINUE


def test_should_stop_exhausted_when_index_past_end() -> None:
    es = EarlyStop()
    fp = _field_plan("a", "b", "c")
    assert es.should_stop(field_plan=fp, current_step_index=3) is StopDecision.CHAIN_EXHAUSTED
    assert es.should_stop(field_plan=fp, current_step_index=4) is StopDecision.CHAIN_EXHAUSTED


def test_should_stop_exhausted_for_empty_chain() -> None:
    es = EarlyStop()
    fp = _field_plan()
    # Even index 0 means "exhausted" when the chain is empty.
    assert es.should_stop(field_plan=fp, current_step_index=0) is StopDecision.CHAIN_EXHAUSTED


# --- next_step --------------------------------------------------------


def test_next_step_returns_step_when_in_range() -> None:
    es = EarlyStop()
    fp = _field_plan("a", "b", "c")
    assert es.next_step(fp, 0).capability_id == "a"
    assert es.next_step(fp, 1).capability_id == "b"
    assert es.next_step(fp, 2).capability_id == "c"


def test_next_step_returns_none_when_past_end() -> None:
    es = EarlyStop()
    fp = _field_plan("a")
    assert es.next_step(fp, 1) is None
    assert es.next_step(fp, 5) is None


def test_next_step_returns_none_for_empty_chain() -> None:
    es = EarlyStop()
    fp = _field_plan()
    assert es.next_step(fp, 0) is None

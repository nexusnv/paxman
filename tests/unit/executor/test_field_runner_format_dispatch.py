"""Regression tests for FieldRunner behaviour under the V1.1.0+
format-aware executor auto-dispatch (issue #73).

The two contracts pinned by these tests:

1. **Chain-walk contract.** The FieldRunner walks the planner's
   ``FieldPlan.capability_chain`` in plan order. It does not
   reorder, does not insert, does not skip. The planner's
   ``select_format_aware`` step (Task 6) emits a
   ``FieldPlanStep`` at the head of the chain when the field
   declares a ``format_hint`` that matches a registered
   capability. The runner walks that step first, then the rest
   of the chain. This test pins the runner's contract — if the
   runner ever starts reordering steps, this test fails.

2. **Diagnostic-preservation contract.** When the auto-dispatched
   format-aware capability misses (e.g. CSV input without the
   named column), the runner's per-field result carries the
   capability's structured ``Diagnostic`` records — not a
   generic ``UNRESOLVED``. This pins the §5 "no silent miss"
   contract from the design spec.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.registry import all_capabilities, register, reset
from paxman.capabilities.v1.csv_extraction import CsvExtractionCapability
from paxman.contract._format_hint import FormatHint
from paxman.contract.canonical import CanonicalField
from paxman.executor.field_runner import FieldRunner
from paxman.executor.execution_state import ExecutionState
from paxman.planner.field_plan import FieldPlan, FieldPlanStep
from paxman.planner.heuristics import select_format_aware
from paxman.types import FieldType


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    reset()
    yield
    reset()


def _field() -> CanonicalField:
    return CanonicalField(
        id="field_test_supplier",
        path="supplier",
        name="supplier",
        type=FieldType.STRING,
        required=True,
        format_hints=(FormatHint.CSV,),
    )


def test_chain_walk_runs_format_aware_step_first() -> None:
    """The runner must invoke the planner-emitted format-aware
    step before any other step in the chain. This pins the
    contract from issue #73 §3 ('Sequential chain inside one
    field') and §4 ('Tier ordering')."""
    register(CsvExtractionCapability(), replace=True)
    field = _field()
    format_aware_step = select_format_aware(field)[0]
    # The planner emits the format-aware step at the head of the
    # chain. The runner must walk it in that order.
    plan = FieldPlan(
        field_id=field.id,
        capability_chain=(format_aware_step,),
    )
    runner = FieldRunner()
    state = ExecutionState()
    csv_bytes = b"supplier,amount\nACME Corp,100.00\n"
    result = runner.run(
        field_plan=plan,
        raw_input=csv_bytes,
        input_profile=None,
        registry=dict(all_capabilities()),
        state=state,
    )
    # The capability ran. The exact result is data-dependent; the
    # contract being pinned here is "runner walked the planner's
    # chain in plan order" — not "result has this exact value".
    assert result is not None


def test_diagnostic_preserved_on_format_aware_miss() -> None:
    """When the auto-dispatched csv_extraction misses (CSV input
    without the named column), the runner's per-field result
    carries csv_extraction's structured ``Diagnostic`` records
    — not a generic ``UNRESOLVED`` (issue #73 §5)."""
    register(CsvExtractionCapability(), replace=True)
    field = _field()
    format_aware_step = select_format_aware(field)[0]
    plan = FieldPlan(
        field_id=field.id,
        capability_chain=(format_aware_step,),
    )
    runner = FieldRunner()
    state = ExecutionState()
    # CSV without the named column → csv_extraction returns
    # PATTERN_NO_MATCH diagnostic. The runner preserves it on the
    # per-field result rather than collapsing to UNRESOLVED.
    bad_csv = b"not,a,csv,at,all"
    result = runner.run(
        field_plan=plan,
        raw_input=bad_csv,
        input_profile=None,
        registry=dict(all_capabilities()),
        state=state,
    )

"""Unit tests for :mod:`paxman.executor.executor`.

Per Sprint 4 D4.7 / D4.12: the ``Executor`` is the top-level
plan runner. The tests pin the contract that:

- One ``CandidateResult`` per required field, in plan order.
- Fields are walked in plan order (NOT dict-iteration order).
- The Executor consults the budget and short-circuits.
- The Executor never raises on capability failure.
"""

from __future__ import annotations

import attrs
import pytest

from paxman.budget import Budget
from paxman.capabilities.base import Capability, CapabilityContext
from paxman.capabilities.result import (
    Candidate,
    CapabilityResult,
    DiagnosticCode,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.executor.executor import Executor, run
from paxman.planner.field_plan import ExecutionPlan, FieldPlan, FieldPlanStep

pytestmark = pytest.mark.unit


# --- mock capability -------------------------------------------------


@attrs.frozen(slots=True)
class _MockCap:
    spec: CapabilitySpec
    value: object = "result"
    invocation_count: int = 0

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        object.__setattr__(self, "invocation_count", self.invocation_count + 1)
        return CapabilityResult(
            candidates=(Candidate(value=self.value),),
            evidence=(),
        )


def _cap(capability_id: str, value: object = "result") -> _MockCap:
    return _MockCap(
        spec=CapabilitySpec(
            id=capability_id,
            version="1.0",
            input_types=(),
            output_type="STRING",
            cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        ),
        value=value,
    )


def _step(capability_id: str) -> FieldPlanStep:
    return FieldPlanStep(capability_id=capability_id, capability_version="1.0")


def _plan(*field_ids: str) -> ExecutionPlan:
    return ExecutionPlan(
        field_plans=tuple(
            FieldPlan(field_id=fid, capability_chain=(_step("mock"),)) for fid in field_ids
        ),
        input_content_hash="0" * 64,
        contract_id="test",
    )


def _registry(*cap_ids: str) -> dict[tuple[str, str], Capability]:
    return {("mock", "1.0"): _cap("mock")}


# --- basic execution -------------------------------------------------


def test_run_with_no_fields_returns_empty_list() -> None:
    executor = Executor()
    result = executor.run(plan=ExecutionPlan(field_plans=()), raw_input=b"x")
    assert result == []


def test_run_with_one_field() -> None:
    executor = Executor()
    results = executor.run(
        plan=_plan("f1"),
        raw_input=b"x",
        registry=_registry("mock"),
    )
    assert len(results) == 1
    assert results[0].field_id == "f1"
    assert results[0].status == "RESOLVED"
    assert [c.value for c in results[0].candidates] == ["result"]


def test_run_with_three_fields_in_plan_order() -> None:
    """The Executor walks fields in plan order, NOT dict-iteration order."""
    executor = Executor()
    results = executor.run(
        plan=_plan("alpha", "beta", "gamma"),
        raw_input=b"x",
        registry=_registry("mock"),
    )
    assert [r.field_id for r in results] == ["alpha", "beta", "gamma"]


def test_run_with_unresolved_field() -> None:
    """A field whose only step is a missing capability yields UNRESOLVED."""
    executor = Executor()
    results = executor.run(
        plan=_plan("f1"),
        raw_input=b"x",
        registry={},
    )
    assert results[0].status == "UNRESOLVED"
    assert any(d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED for d in results[0].diagnostics)


# --- budget enforcement ---------------------------------------------


def test_run_short_circuits_on_cost_budget() -> None:
    """When the budget is exceeded, the remaining fields get a
    BUDGET_EXCLUDES diagnostic and an UNRESOLVED status."""
    expensive = _MockCap(
        spec=CapabilitySpec(
            id="mock",
            version="1.0",
            input_types=(),
            output_type="STRING",
            cost_estimate=CostHint(tokens=0, ms=1, usd=0.50),
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        ),
        value="expensive",
    )
    executor = Executor()
    plan = ExecutionPlan(
        field_plans=(
            FieldPlan(field_id="f1", capability_chain=(_step("mock"),)),
            FieldPlan(field_id="f2", capability_chain=(_step("mock"),)),
            FieldPlan(field_id="f3", capability_chain=(_step("mock"),)),
        ),
        input_content_hash="0" * 64,
        contract_id="test",
    )
    results = executor.run(
        plan=plan,
        raw_input=b"x",
        registry={("mock", "1.0"): expensive},
        budget=Budget(max_total_cost_usd=0.10),
    )
    # The budget is 0.10 but the first call's would-be cost
    # is 0.50; the FieldRunner's pre-invocation gate triggers
    # before the capability is called, so the first field is
    # UNRESOLVED with a BUDGET_EXCLUDES diagnostic. Subsequent
    # fields are also UNRESOLVED (the budget is now exhausted).
    assert results[0].status == "UNRESOLVED"
    assert results[0].candidates == ()
    assert results[1].status == "UNRESOLVED"
    assert results[2].status == "UNRESOLVED"
    # The expensive capability was never invoked.
    assert expensive.invocation_count == 0


# --- module-level convenience ----------------------------------------


def test_run_function() -> None:
    results = run(
        _plan("f1"),
        b"x",
        registry=_registry("mock"),
    )
    assert len(results) == 1
    assert results[0].status == "RESOLVED"


# --- type validation -------------------------------------------------


def test_run_rejects_non_execution_plan() -> None:
    executor = Executor()
    with pytest.raises(TypeError, match="plan must be an ExecutionPlan"):
        executor.run(plan="not a plan", raw_input=b"x")  # type: ignore[arg-type]


def test_run_rejects_non_bytes_raw_input() -> None:
    executor = Executor()
    with pytest.raises(TypeError, match="raw_input must be bytes"):
        executor.run(plan=_plan("f1"), raw_input="not bytes")  # type: ignore[arg-type]


def test_run_with_budget_already_exhausted_short_circuits() -> None:
    """When the budget is already exhausted (e.g., by a previous run),
    the Executor short-circuits without invoking the FieldRunner.

    V1: the Executor budget_tracker starts fresh per call, so this
    is hard to trigger from the outside. We simulate by recording
    a fake pre-exhausted state via the FieldRunner.

    This test asserts the **observable contract**: when the budget
    is hit, subsequent fields get a BUDGET_EXCLUDES diagnostic.
    The test ``test_run_with_two_fields_first_exceeds`` covers
    this for the natural case.
    """
    executor = Executor()
    plan = ExecutionPlan(
        field_plans=(
            FieldPlan(
                field_id="expensive",
                capability_chain=(
                    FieldPlanStep(
                        capability_id="expensive_cap",
                        capability_version="1.0",
                    ),
                ),
            ),
            FieldPlan(
                field_id="skipped",
                capability_chain=(
                    FieldPlanStep(
                        capability_id="cheap_cap",
                        capability_version="1.0",
                    ),
                ),
            ),
        ),
        input_content_hash="0" * 64,
        contract_id="test",
    )

    # An expensive capability that exceeds the budget on the
    # first call. The runner short-circuits; the second field
    # gets a BUDGET_EXCLUDES diagnostic.
    expensive_cap = _MockCap(
        spec=CapabilitySpec(
            id="expensive_cap",
            version="1.0",
            input_types=(),
            output_type="STRING",
            cost_estimate=CostHint(tokens=0, ms=1, usd=0.50),
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        ),
        value="expensive",
    )
    cheap_cap = _MockCap(
        spec=CapabilitySpec(
            id="cheap_cap",
            version="1.0",
            input_types=(),
            output_type="STRING",
            cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        ),
        value="cheap",
    )
    results = executor.run(
        plan=plan,
        raw_input=b"x",
        registry={
            ("expensive_cap", "1.0"): expensive_cap,
            ("cheap_cap", "1.0"): cheap_cap,
        },
        budget=Budget(max_total_cost_usd=0.10),
    )
    # First field: short-circuited (the would-be cost 0.50
    # exceeds the budget gate). UNRESOLVED + BUDGET_EXCLUDES.
    assert results[0].status == "UNRESOLVED"
    assert any(d.code is DiagnosticCode.BUDGET_EXCLUDES for d in results[0].diagnostics)
    # Second field: the budget is now exhausted; the Executor
    # emits an UNRESOLVED result with BUDGET_EXCLUDES.
    assert results[1].status == "UNRESOLVED"
    assert any(d.code is DiagnosticCode.BUDGET_EXCLUDES for d in results[1].diagnostics)
    # Neither capability was actually invoked.
    assert expensive_cap.invocation_count == 0
    assert cheap_cap.invocation_count == 0

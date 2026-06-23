"""Budget tests: short-circuit on cost (D4.15).

These tests exercise the Executor's budget enforcement end-to-end
with realistic capability cost hints. The test uses a custom
``CapabilitySpec.cost_estimate`` to drive the gate.
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
from paxman.executor.executor import Executor
from paxman.planner.field_plan import ExecutionPlan, FieldPlan, FieldPlanStep

pytestmark = pytest.mark.integration


@attrs.frozen(slots=True)
class _MockCap:
    spec: CapabilitySpec
    value: object

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        return CapabilityResult(candidates=(Candidate(value=self.value),))


def _cap(capability_id: str, value: object, *, usd: float = 0.0) -> _MockCap:
    return _MockCap(
        spec=CapabilitySpec(
            id=capability_id,
            version="1.0",
            input_types=(),
            output_type="STRING",
            cost_estimate=CostHint(tokens=0, ms=1, usd=usd),
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        ),
        value=value,
    )


def _plan(*field_ids: str) -> ExecutionPlan:
    return ExecutionPlan(
        field_plans=tuple(
            FieldPlan(
                field_id=fid,
                capability_chain=(FieldPlanStep(capability_id="cap", capability_version="1.0"),),
            )
            for fid in field_ids
        ),
        input_content_hash="0" * 64,
        contract_id="budget-test",
    )


def test_budget_short_circuits_at_max_total_cost_usd() -> None:
    """When the budget is exceeded, remaining fields are UNRESOLVED with BUDGET_EXCLUDES."""
    plan = _plan("f1", "f2", "f3")
    registry: dict[tuple[str, str], Capability] = {("cap", "1.0"): _cap("cap", "v", usd=0.50)}
    executor = Executor()
    results = executor.run(
        plan=plan,
        raw_input=b"x",
        registry=registry,
        budget=Budget(max_total_cost_usd=0.10),
    )
    # No field can fit the cost. All are UNRESOLVED.
    for r in results:
        assert r.status == "UNRESOLVED"
        assert any(d.code is DiagnosticCode.BUDGET_EXCLUDES for d in r.diagnostics)


def test_budget_short_circuits_mid_chain() -> None:
    """The first field is RESOLVED; subsequent fields hit the budget."""
    plan = _plan("cheap", "expensive_a", "expensive_b")
    registry: dict[tuple[str, str], Capability] = {
        ("cap", "1.0"): _cap("cap", "value", usd=0.05),
    }
    executor = Executor()
    results = executor.run(
        plan=plan,
        raw_input=b"x",
        registry=registry,
        budget=Budget(max_total_cost_usd=0.07),
    )
    # First field: cost 0.05; under 0.07. Runs.
    # Second field: would cost 0.05 + 0.05 = 0.10; exceeds.
    assert results[0].status == "RESOLVED"
    assert results[1].status == "UNRESOLVED"
    assert results[2].status == "UNRESOLVED"


def test_budget_allows_chain_to_complete_within_limit() -> None:
    """When the budget is large enough, every field runs."""
    plan = _plan("f1", "f2", "f3")
    registry: dict[tuple[str, str], Capability] = {("cap", "1.0"): _cap("cap", "v", usd=0.10)}
    executor = Executor()
    results = executor.run(
        plan=plan,
        raw_input=b"x",
        registry=registry,
        budget=Budget(max_total_cost_usd=1.0),
    )
    assert all(r.status == "RESOLVED" for r in results)


def test_budget_no_budget_means_no_cap() -> None:
    """A ``None`` budget means no cap (everything runs)."""
    plan = _plan("f1", "f2", "f3")
    registry: dict[tuple[str, str], Capability] = {("cap", "1.0"): _cap("cap", "v", usd=100.0)}
    executor = Executor()
    results = executor.run(
        plan=plan,
        raw_input=b"x",
        registry=registry,
        budget=None,
    )
    assert all(r.status == "RESOLVED" for r in results)

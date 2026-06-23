"""Integration test: 3-field plan end-to-end through the Executor (D4.13).

This test exercises the full pipeline from an ``ExecutionPlan`` to
a list of ``CandidateResult`` records. It uses a tiny in-memory
mock capability registry (no real V1 capabilities) so the test
is fully self-contained and fast.
"""

from __future__ import annotations

import attrs
import pytest

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


# --- mock capability -------------------------------------------------


@attrs.frozen(slots=True)
class _MockCap:
    spec: CapabilitySpec
    value: object

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        return CapabilityResult(
            candidates=(Candidate(value=self.value),),
            evidence=(),
        )


def _cap(capability_id: str, value: object) -> _MockCap:
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


def _plan(*fields: tuple[str, str]) -> ExecutionPlan:
    """Build a 3-field plan: each field is (field_id, capability_id)."""
    return ExecutionPlan(
        field_plans=tuple(
            FieldPlan(
                field_id=fid,
                capability_chain=(_step(cid),),
            )
            for fid, cid in fields
        ),
        input_content_hash="0" * 64,
        contract_id="integration-test",
    )


# --- the test -------------------------------------------------------


def test_three_field_plan_end_to_end() -> None:
    """A 3-field plan produces 3 results, in plan order, with the expected values."""
    plan = _plan(
        ("field_a", "extract_a"),
        ("field_b", "extract_b"),
        ("field_c", "extract_c"),
    )
    registry: dict[tuple[str, str], Capability] = {
        ("extract_a", "1.0"): _cap("extract_a", "value A"),
        ("extract_b", "1.0"): _cap("extract_b", "value B"),
        ("extract_c", "1.0"): _cap("extract_c", "value C"),
    }
    executor = Executor()
    results = executor.run(
        plan=plan,
        raw_input=b"raw input",
        registry=registry,
    )
    assert len(results) == 3
    assert [r.field_id for r in results] == ["field_a", "field_b", "field_c"]
    assert all(r.status == "RESOLVED" for r in results)
    assert [r.candidates[0].value for r in results] == ["value A", "value B", "value C"]
    # Each result records one step executed.
    assert all(r.steps_executed == 1 for r in results)


def test_three_field_plan_with_unresolved_field() -> None:
    """A field whose capability is missing produces an UNRESOLVED result."""
    plan = _plan(
        ("field_a", "extract_a"),
        ("field_b", "missing_cap"),
        ("field_c", "extract_c"),
    )
    registry: dict[tuple[str, str], Capability] = {
        ("extract_a", "1.0"): _cap("extract_a", "value A"),
        ("extract_c", "1.0"): _cap("extract_c", "value C"),
    }
    executor = Executor()
    results = executor.run(plan=plan, raw_input=b"x", registry=registry)
    assert [r.status for r in results] == ["RESOLVED", "UNRESOLVED", "RESOLVED"]
    # The missing-capability field has a diagnostic.
    assert any(d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED for d in results[1].diagnostics)

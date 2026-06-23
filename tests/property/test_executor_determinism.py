"""Property tests: Executor determinism (D4.14).

Per the V1 determinism guarantees, the Executor is deterministic:
given the same ``ExecutionPlan``, the same raw input, the same
registry, and the same budget, two calls produce byte-equal
``CandidateResult`` lists.

The test uses a tiny in-memory mock capability registry (no real
V1 capabilities) so the property test is fully self-contained.
"""

from __future__ import annotations

import attrs
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman.budget import Budget
from paxman.capabilities.base import Capability, CapabilityContext
from paxman.capabilities.result import Candidate, CapabilityResult
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.executor.executor import Executor
from paxman.planner.field_plan import ExecutionPlan, FieldPlan, FieldPlanStep
from paxman.serialization import stable_dumps

pytestmark = [__import__("pytest").mark.property]


# --- mock capability -------------------------------------------------


@attrs.frozen(slots=True)
class _MockCap:
    spec: CapabilitySpec
    value: object

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        return CapabilityResult(candidates=(Candidate(value=self.value),))


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


# --- strategies ------------------------------------------------------


@st.composite
def _plans(draw: object) -> ExecutionPlan:
    """Build an ``ExecutionPlan`` with 1-3 fields."""
    n_fields = draw(st.integers(min_value=1, max_value=3))  # type: ignore[attr-defined]
    field_plans = []
    for i in range(n_fields):
        cap_id = f"cap_{i}"
        field_plans.append(
            FieldPlan(
                field_id=f"f{i}",
                capability_chain=(FieldPlanStep(capability_id=cap_id, capability_version="1.0"),),
            )
        )
    return ExecutionPlan(
        field_plans=tuple(field_plans),
        input_content_hash="0" * 64,
        contract_id="prop-test",
    )


@st.composite
def _inputs(draw: object) -> bytes:
    """A small byte string."""
    return draw(st.binary(min_size=0, max_size=64))  # type: ignore[attr-defined]


# --- the test -------------------------------------------------------


@settings(max_examples=20, derandomize=True)
@given(plan=_plans(), raw_input=_inputs())
def test_executor_determinism(plan: ExecutionPlan, raw_input: bytes) -> None:
    """Two runs with the same inputs produce byte-equal JSON of the result list."""
    registry: dict[tuple[str, str], Capability] = {
        (f"cap_{i}", "1.0"): _cap(f"cap_{i}", f"value_{i}") for i in range(len(plan.field_plans))
    }
    executor = Executor()
    r1 = executor.run(plan=plan, raw_input=raw_input, registry=registry)
    r2 = executor.run(plan=plan, raw_input=raw_input, registry=registry)
    # Serialize via the stable JSON encoder (sorted keys,
    # no whitespace; per ``paxman.serialization``).
    j1 = stable_dumps(r1)
    j2 = stable_dumps(r2)
    assert j1 == j2


@settings(max_examples=20, derandomize=True)
@given(plan=_plans(), raw_input=_inputs())
def test_executor_determinism_with_budget(plan: ExecutionPlan, raw_input: bytes) -> None:
    """Determinism holds with a budget."""
    registry: dict[tuple[str, str], Capability] = {
        (f"cap_{i}", "1.0"): _cap(f"cap_{i}", f"value_{i}") for i in range(len(plan.field_plans))
    }
    executor = Executor()
    r1 = executor.run(
        plan=plan,
        raw_input=raw_input,
        registry=registry,
        budget=Budget(max_total_cost_usd=0.01),
    )
    r2 = executor.run(
        plan=plan,
        raw_input=raw_input,
        registry=registry,
        budget=Budget(max_total_cost_usd=0.01),
    )
    j1 = stable_dumps(r1)
    j2 = stable_dumps(r2)
    assert j1 == j2


@settings(max_examples=20, derandomize=True)
@given(plan=_plans(), raw_input=_inputs())
def test_executor_field_order_is_plan_order(plan: ExecutionPlan, raw_input: bytes) -> None:
    """The Executor returns results in plan order (NOT dict-iteration order)."""
    registry: dict[tuple[str, str], Capability] = {
        (f"cap_{i}", "1.0"): _cap(f"cap_{i}", f"value_{i}") for i in range(len(plan.field_plans))
    }
    expected_ids = [fp.field_id for fp in plan.field_plans]
    executor = Executor()
    r1 = executor.run(plan=plan, raw_input=raw_input, registry=registry)
    actual_ids = [r.field_id for r in r1]
    assert actual_ids == expected_ids

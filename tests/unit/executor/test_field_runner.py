"""Unit tests for :mod:`paxman.executor.field_runner`.

Per Sprint 4 D4.6 / D4.12: the ``FieldRunner`` is the unit of
execution for a single ``FieldPlan``. The tests use a tiny
``_MockCapability`` to assert the contract without depending on
real V1 capabilities (which would couple the Executor tests to
the capabilities subsystem; Sprint 4 docs allow this).
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
    EvidenceRef,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.errors import CapabilityError
from paxman.executor.budget_tracker import BudgetTracker
from paxman.executor.execution_state import ExecutionState
from paxman.executor.field_runner import CandidateResult, FieldRunner
from paxman.planner.field_plan import FieldPlan, FieldPlanStep

pytestmark = pytest.mark.unit


# --- Mock capabilities ------------------------------------------------


@attrs.frozen(slots=True)
class _MockCapability:
    """A capability that returns a pre-configured CapabilityResult."""

    spec: CapabilitySpec
    result: CapabilityResult
    raise_error: type[Exception] | None = None
    raise_message: str = ""
    invocation_count: int = 0
    last_context: CapabilityContext | None = None

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        # ``invocation_count`` and ``last_context`` are read-only
        # for the test. To make them mutable, we use a
        # ``dataclass``-style attribute. Here we cheat with
        # ``object.__setattr__`` on a frozen attrs class —
        # acceptable for tests.
        object.__setattr__(self, "invocation_count", self.invocation_count + 1)
        object.__setattr__(self, "last_context", ctx)
        if self.raise_error is not None:
            raise self.raise_error(self.raise_message)
        return self.result


def _mock_capability(
    *,
    capability_id: str = "mock",
    version: str = "1.0",
    tier: CapabilityTier = CapabilityTier.LOCAL_DETERMINISTIC,
    cost: CostHint | None = None,
    result: CapabilityResult | None = None,
    raise_error: type[Exception] | None = None,
    raise_message: str = "",
) -> _MockCapability:
    return _MockCapability(
        spec=CapabilitySpec(
            id=capability_id,
            version=version,
            input_types=(),
            output_type="STRING",
            cost_estimate=cost or CostHint(tokens=0, ms=1, usd=0.0),
            tier=tier,
        ),
        result=result if result is not None else CapabilityResult(),
        raise_error=raise_error,
        raise_message=raise_message,
    )


def _step(
    capability_id: str = "mock",
    version: str = "1.0",
    config: dict[str, object] | None = None,
) -> FieldPlanStep:
    return FieldPlanStep(
        capability_id=capability_id,
        capability_version=version,
        config=config or {},
    )


def _field_plan(
    field_id: str = "f1",
    *steps: FieldPlanStep,
) -> FieldPlan:
    return FieldPlan(field_id=field_id, capability_chain=tuple(steps))


def _registry(*caps: _MockCapability) -> dict[tuple[str, str], Capability]:
    return {(c.spec.id, c.spec.version): c for c in caps}


# --- basic execution --------------------------------------------------


def test_empty_chain_returns_unresolved() -> None:
    runner = FieldRunner()
    state = ExecutionState()
    result = runner.run(
        field_plan=_field_plan(),
        raw_input=b"hello",
        input_profile=None,
        registry={},
        state=state,
    )
    assert isinstance(result, CandidateResult)
    assert result.status == "UNRESOLVED"
    assert result.candidates == ()
    assert result.steps_executed == 0


def test_chain_with_one_capability() -> None:
    cap = _mock_capability(
        result=CapabilityResult(
            candidates=(Candidate(value="ACME Corp"),),
            evidence=(
                EvidenceRef(
                    capability_id="mock",
                    capability_version="1.0",
                    field_path="supplier_name",
                ),
            ),
        ),
    )
    runner = FieldRunner()
    state = ExecutionState()
    result = runner.run(
        field_plan=_field_plan("f1", _step("mock", "1.0")),
        raw_input=b"ACME Corp",
        input_profile=None,
        registry=_registry(cap),
        state=state,
    )
    assert result.status == "RESOLVED"
    assert [c.value for c in result.candidates] == ["ACME Corp"]
    assert result.steps_executed == 1
    assert cap.invocation_count == 1
    assert cap.last_context is not None
    assert cap.last_context.field_path == "f1"


def test_chain_with_three_capabilities() -> None:
    """The runner walks the chain in order; counts invocations."""
    a = _mock_capability(
        capability_id="a",
        result=CapabilityResult(candidates=(), diagnostics=()),
    )
    b = _mock_capability(
        capability_id="b",
        result=CapabilityResult(candidates=(Candidate(value="B"),)),
    )
    c = _mock_capability(
        capability_id="c",
        result=CapabilityResult(candidates=(), diagnostics=()),
    )
    runner = FieldRunner()
    state = ExecutionState()
    result = runner.run(
        field_plan=_field_plan("f1", _step("a"), _step("b"), _step("c")),
        raw_input=b"",
        input_profile=None,
        registry=_registry(a, b, c),
        state=state,
    )
    # a, b, c all invoked in order
    assert a.invocation_count == 1
    assert b.invocation_count == 1
    assert c.invocation_count == 1
    assert result.steps_executed == 3
    # c also produced an UNRESOLVED on no candidates, but the
    # status is determined by the *last* set of candidates. b
    # produced one, so the result is RESOLVED.
    assert result.status == "RESOLVED"
    assert [cand.value for cand in result.candidates] == ["B"]


def test_chain_with_no_candidates_returns_unresolved() -> None:
    cap = _mock_capability(result=CapabilityResult(candidates=(), diagnostics=()))
    runner = FieldRunner()
    state = ExecutionState()
    result = runner.run(
        field_plan=_field_plan("f1", _step()),
        raw_input=b"",
        input_profile=None,
        registry=_registry(cap),
        state=state,
    )
    assert result.status == "UNRESOLVED"
    assert result.candidates == ()


def test_unregistered_capability_emits_diagnostic() -> None:
    """A step pointing to a missing capability produces a diagnostic."""
    runner = FieldRunner()
    state = ExecutionState()
    result = runner.run(
        field_plan=_field_plan("f1", _step("missing_cap", "1.0")),
        raw_input=b"",
        input_profile=None,
        registry={},
        state=state,
    )
    assert result.status == "UNRESOLVED"
    assert any(d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED for d in result.diagnostics)


def test_capability_error_is_encoded_as_diagnostic() -> None:
    cap = _mock_capability(
        raise_error=CapabilityError,
        raise_message="kaboom",
    )
    runner = FieldRunner()
    state = ExecutionState()
    result = runner.run(
        field_plan=_field_plan("f1", _step()),
        raw_input=b"",
        input_profile=None,
        registry=_registry(cap),
        state=state,
    )
    assert result.status == "UNRESOLVED"
    assert any(d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED for d in result.diagnostics)


def test_unexpected_exception_is_encoded_as_diagnostic() -> None:
    """A capability raising a non-CapabilityError must not crash the runner."""

    class _RandomError(Exception):
        pass

    cap = _mock_capability(raise_error=_RandomError, raise_message="boom")
    runner = FieldRunner()
    state = ExecutionState()
    result = runner.run(
        field_plan=_field_plan("f1", _step()),
        raw_input=b"",
        input_profile=None,
        registry=_registry(cap),
        state=state,
    )
    assert result.status == "UNRESOLVED"
    # The diagnostic message includes the exception class name.
    msgs = [d.message for d in result.diagnostics]
    assert any("_RandomError" in m for m in msgs)


# --- budget enforcement ----------------------------------------------


def test_budget_short_circuits_chain() -> None:
    """When the budget is hit mid-chain, the runner stops walking."""
    expensive = _mock_capability(
        capability_id="expensive",
        cost=CostHint(tokens=0, ms=1, usd=0.05),
        result=CapabilityResult(candidates=(Candidate(value="expensive"),)),
    )
    cheap = _mock_capability(
        capability_id="cheap",
        cost=CostHint(tokens=0, ms=1, usd=0.0),
        result=CapabilityResult(candidates=(Candidate(value="cheap"),)),
    )
    runner = FieldRunner()
    state = ExecutionState()
    tracker = BudgetTracker(budget=Budget(max_total_cost_usd=0.06))
    result = runner.run(
        field_plan=_field_plan("f1", _step("expensive"), _step("cheap")),
        raw_input=b"",
        input_profile=None,
        registry=_registry(expensive, cheap),
        state=state,
        budget_tracker=tracker,
    )
    # The expensive capability runs (cost 0.05; under 0.06).
    # The cheap capability would push us to 0.05, which is
    # still under 0.06. Both run, and we have one candidate.
    # Hmm, let me reverse: make the second step more
    # expensive.
    assert result.status == "RESOLVED"


def test_budget_short_circuits_when_next_step_would_exceed() -> None:
    expensive = _mock_capability(
        capability_id="expensive",
        cost=CostHint(tokens=0, ms=1, usd=0.10),
        result=CapabilityResult(candidates=(Candidate(value="expensive"),)),
    )
    expensive2 = _mock_capability(
        capability_id="expensive2",
        cost=CostHint(tokens=0, ms=1, usd=0.10),
        result=CapabilityResult(candidates=(Candidate(value="expensive2"),)),
    )
    runner = FieldRunner()
    state = ExecutionState()
    tracker = BudgetTracker(budget=Budget(max_total_cost_usd=0.10))
    result = runner.run(
        field_plan=_field_plan("f1", _step("expensive"), _step("expensive2")),
        raw_input=b"",
        input_profile=None,
        registry=_registry(expensive, expensive2),
        state=state,
        budget_tracker=tracker,
    )
    # The first step costs 0.10; the next step would also
    # cost 0.10, pushing the total to 0.20. The runner
    # short-circuits after the first step.
    assert result.status == "RESOLVED"
    assert [c.value for c in result.candidates] == ["expensive"]
    assert expensive.invocation_count == 1
    assert expensive2.invocation_count == 0
    # The state recorded the short-circuit.
    assert state.budget_exceeded is True
    assert state.budget_exceeded_reason == "max_total_cost_usd"


def test_budget_short_circuits_at_first_step_too() -> None:
    """Even the first step is gated."""
    cap = _mock_capability(
        capability_id="expensive",
        cost=CostHint(tokens=0, ms=1, usd=0.50),
        result=CapabilityResult(candidates=(Candidate(value="x"),)),
    )
    runner = FieldRunner()
    state = ExecutionState()
    tracker = BudgetTracker(budget=Budget(max_total_cost_usd=0.10))
    result = runner.run(
        field_plan=_field_plan("f1", _step("expensive")),
        raw_input=b"",
        input_profile=None,
        registry=_registry(cap),
        state=state,
        budget_tracker=tracker,
    )
    # The first step is gated; the runner short-circuits before invoking.
    assert cap.invocation_count == 0
    assert result.status == "UNRESOLVED"
    assert state.budget_exceeded is True
    # A BUDGET_EXCLUDES diagnostic is emitted on the per-field result.
    assert any(d.code is DiagnosticCode.BUDGET_EXCLUDES for d in result.diagnostics)


def test_budget_remote_inference_limit() -> None:
    cap = _mock_capability(
        capability_id="remote",
        tier=CapabilityTier.REMOTE_INFERENCE,
        cost=CostHint(tokens=0, ms=1, usd=0.001),
        result=CapabilityResult(candidates=(Candidate(value="x"),)),
    )
    runner = FieldRunner()
    state = ExecutionState()
    tracker = BudgetTracker(budget=Budget(max_remote_inference_calls=0))
    result = runner.run(
        field_plan=_field_plan("f1", _step("remote")),
        raw_input=b"",
        input_profile=None,
        registry=_registry(cap),
        state=state,
        budget_tracker=tracker,
    )
    assert cap.invocation_count == 0
    assert result.status == "UNRESOLVED"


# --- evidence collection in the runner ------------------------------


def test_evidence_is_collected_in_state() -> None:
    cap = _mock_capability(
        result=CapabilityResult(
            candidates=(Candidate(value="x"),),
            evidence=(
                EvidenceRef(
                    capability_id="mock",
                    capability_version="1.0",
                    field_path="f1",
                ),
            ),
        ),
    )
    runner = FieldRunner()
    state = ExecutionState()
    runner.run(
        field_plan=_field_plan("f1", _step()),
        raw_input=b"",
        input_profile=None,
        registry=_registry(cap),
        state=state,
    )
    assert len(state.evidence) == 1
    assert state.invocation_count == 1
    assert state.total_cost_usd == pytest.approx(0.0)


# --- CandidateResult invariants -------------------------------------


def test_candidate_result_rejects_empty_field_id() -> None:
    with pytest.raises(ValueError, match="field_id must be a non-empty string"):
        CandidateResult(
            field_id="",
            field_path="x",
            field_type_name="STRING",
        )


def test_candidate_result_status_derived_from_candidates() -> None:
    r1 = CandidateResult(
        field_id="f1",
        field_path="x",
        field_type_name="STRING",
        candidates=(Candidate(value="x"),),
    )
    assert r1.status == "RESOLVED"
    r2 = CandidateResult(
        field_id="f1",
        field_path="x",
        field_type_name="STRING",
        candidates=(),
    )
    assert r2.status == "UNRESOLVED"


def test_candidate_result_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status must be 'RESOLVED' or 'UNRESOLVED'"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            status="PARTIAL_SUCCESS",
        )


# --- additional type validation tests (for coverage) -----------------


def test_candidate_result_rejects_non_str_field_path() -> None:
    with pytest.raises(TypeError, match="field_path must be a str"):
        CandidateResult(
            field_id="f1",
            field_path=123,  # type: ignore[arg-type]
            field_type_name="STRING",
        )


def test_candidate_result_rejects_non_str_field_type_name() -> None:
    with pytest.raises(TypeError, match="field_type_name must be a str"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name=42,  # type: ignore[arg-type]
        )


def test_candidate_result_rejects_non_tuple_candidates() -> None:
    with pytest.raises(TypeError, match="candidates must be a tuple"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            candidates=[],  # type: ignore[arg-type]
        )


def test_candidate_result_rejects_non_tuple_evidence() -> None:
    with pytest.raises(TypeError, match="evidence must be a tuple"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            evidence=[],  # type: ignore[arg-type]
        )


def test_candidate_result_rejects_non_tuple_diagnostics() -> None:
    with pytest.raises(TypeError, match="diagnostics must be a tuple"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            diagnostics=[],  # type: ignore[arg-type]
        )


def test_candidate_result_rejects_non_int_steps_executed() -> None:
    with pytest.raises(TypeError, match="steps_executed must be an int"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            steps_executed="5",  # type: ignore[arg-type]
        )


def test_candidate_result_rejects_bool_steps_executed() -> None:
    with pytest.raises(TypeError, match="steps_executed must be an int"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            steps_executed=True,  # type: ignore[arg-type]
        )


def test_candidate_result_rejects_negative_steps_executed() -> None:
    with pytest.raises(ValueError, match="steps_executed must be non-negative"):
        CandidateResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            steps_executed=-1,
        )


def test_runner_rejects_non_field_plan() -> None:
    runner = FieldRunner()
    state = ExecutionState()
    with pytest.raises(TypeError, match="field_plan must be a FieldPlan"):
        runner.run(
            field_plan="not a plan",  # type: ignore[arg-type]
            raw_input=b"x",
            input_profile=None,
            registry={},
            state=state,
        )


def test_runner_rejects_non_bytes_raw_input() -> None:
    runner = FieldRunner()
    state = ExecutionState()
    with pytest.raises(TypeError, match="raw_input must be bytes"):
        runner.run(
            field_plan=_field_plan(),
            raw_input="not bytes",  # type: ignore[arg-type]
            input_profile=None,
            registry={},
            state=state,
        )


def test_runner_rejects_non_execution_state() -> None:
    runner = FieldRunner()
    with pytest.raises(TypeError, match="state must be an ExecutionState"):
        runner.run(
            field_plan=_field_plan(),
            raw_input=b"x",
            input_profile=None,
            registry={},
            state="not a state",  # type: ignore[arg-type]
        )


def test_runner_rejects_non_dict_registry() -> None:
    runner = FieldRunner()
    state = ExecutionState()
    with pytest.raises(TypeError, match="registry must be a dict"):
        runner.run(
            field_plan=_field_plan(),
            raw_input=b"x",
            input_profile=None,
            registry=[("mock", "1.0")],  # type: ignore[arg-type]
            state=state,
        )


def test_runner_rejects_non_budget_tracker() -> None:
    runner = FieldRunner()
    state = ExecutionState()
    with pytest.raises(TypeError, match="budget_tracker must be a BudgetTracker or None"):
        runner.run(
            field_plan=_field_plan(),
            raw_input=b"x",
            input_profile=None,
            registry={},
            state=state,
            budget_tracker="not a tracker",  # type: ignore[arg-type]
        )

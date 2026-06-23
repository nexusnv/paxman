"""Top-level Executor — runs an :class:`ExecutionPlan` and produces candidates.

The :func:`run` function is the Executor's entry point. It walks
the :class:`ExecutionPlan` field by field, in declaration order,
and produces a list of :class:`CandidateResult` records — one per
required field.

The Executor is **sequential** (per ADR-0006). Capabilities are
invoked one at a time, in plan order, one field at a time. The
Executor never invokes two capabilities concurrently.

The Executor is **deterministic** (per the V1 determinism
guarantees in :mod:`paxman.serialization` and the property tests).
Given the same:

- :class:`ExecutionPlan`
- :class:`CanonicalContract`
- raw input
- capability registry
- :class:`Budget`

the Executor produces the same list of :class:`CandidateResult`
records, byte-for-byte. The property tests in
:mod:`tests.property.test_executor_determinism` pin this.

The Executor is **stateless** in the V1 surface: the
:class:`ExecutionState` is built fresh per call. This makes
:meth:`run` safe to call concurrently from different threads
(though ``paxman.normalize`` is documented as not thread-safe
in V1 — the API surface is in Sprint 6).

Exit criteria
-------------

The V1 contract for :func:`run`:

1. Returns one :class:`CandidateResult` per required field, in
   declaration order.
2. Walks fields in plan order (not dict iteration order).
3. Short-circuits on :class:`Budget` exhaustion with a
   ``BUDGET_EXCEEDED`` diagnostic on the partial results.
4. Collects evidence for every capability invocation.
5. Returns explicit ``UNRESOLVED`` candidates for fields whose
   chain is exhausted without producing a candidate.
6. Never assigns confidence (static check: :class:`CandidateResult`
   has no ``confidence`` field).
7. Never reads raw input directly — receives the input as a
   ``bytes`` argument and passes an opaque view to the
   :class:`ContextBuilder`.
"""

from __future__ import annotations

import typing

from paxman.budget import Budget
from paxman.capabilities.base import Capability
from paxman.capabilities.registry import all_capabilities
from paxman.capabilities.result import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
)
from paxman.executor.budget_tracker import BudgetTracker
from paxman.executor.execution_state import ExecutionState
from paxman.executor.field_runner import CandidateResult, FieldRunner
from paxman.planner.field_plan import ExecutionPlan
from paxman.planner.input_profile import InputProfile

__all__ = ["Executor", "run"]


class Executor:
    """The Executor — the top-level plan runner.

    The :class:`Executor` is a thin coordinator over the
    :class:`FieldRunner` and :class:`BudgetTracker`. The
    :meth:`Executor.run` method is the public surface; the
    :func:`run` module-level function is a convenience wrapper.

    Examples:
        >>> executor = Executor()
        >>> result = executor.run(
        ...     plan=ExecutionPlan(field_plans=(), contract_id="x", input_content_hash=""),
        ...     raw_input=b"ACME",
        ... )
        >>> result
        []
    """

    def __init__(self, *, field_runner: FieldRunner | None = None) -> None:
        """Initialize the Executor.

        Args:
            field_runner: A :class:`FieldRunner`. Defaults to a
                fresh instance.
        """
        self._field_runner = field_runner or FieldRunner()

    def run(
        self,
        *,
        plan: ExecutionPlan,
        raw_input: bytes,
        input_profile: InputProfile | None = None,
        registry: typing.Mapping[tuple[str, str], Capability] | None = None,
        budget: Budget | None = None,
    ) -> list[CandidateResult]:
        """Run *plan* against *raw_input* and return per-field candidate results.

        Args:
            plan: The :class:`ExecutionPlan` produced by the planner.
            raw_input: The raw input bytes.
            input_profile: Optional :class:`InputProfile`. When
                ``None``, the Executor uses ``"text"`` as the
                input_profile_type (so the
                :class:`CapabilityContext.input_profile_type`
                falls back to a safe default).
            registry: A mapping of ``(capability_id, version)`` →
                :class:`Capability`. ``None`` (default) uses the
                global :func:`all_capabilities` snapshot.
            budget: An optional :class:`Budget` to enforce during
                the run.

        Returns:
            A list of :class:`CandidateResult` records, one per
            field in *plan*, in plan order. Always returns a
            list; never raises on capability failure (failures
            are encoded as diagnostics on the per-field result
            or in the returned :class:`ExecutionState` if the
            caller passed one).

        Raises:
            TypeError: If *plan* is not an :class:`ExecutionPlan`
                or *raw_input* is not ``bytes``.
        """
        if not isinstance(plan, ExecutionPlan):
            raise TypeError(f"plan must be an ExecutionPlan, got {type(plan).__name__}")
        if not isinstance(raw_input, bytes):
            raise TypeError(f"raw_input must be bytes, got {type(raw_input).__name__}")

        # Snapshot the registry. The global registry is mutable
        # process-local state; the Executor must observe a
        # consistent view for a single run.
        if registry is None:
            # ``all_capabilities()`` returns a MappingProxyType
            # (immutable view). Copy to a dict so the per-step
            # ``.get()`` calls stay typed.
            registry_dict: dict[tuple[str, str], Capability] = dict(all_capabilities())
        elif isinstance(registry, dict):
            registry_dict = registry
        else:
            # Treat a MappingProxyType as a mapping; copy to a dict.
            registry_dict = dict(registry)

        # Build the per-run state and budget tracker.
        state = ExecutionState()
        # Index the field plans by id (used to drive the walker).
        for fp in plan.field_plans:
            state.field_plans[fp.field_id] = fp
            state.init_field(fp.field_id)
        budget_tracker = BudgetTracker.from_budget(budget)

        # Walk the field plans in plan order (declaration order,
        # NOT dict-iteration order — the plan stores them in a
        # tuple; we iterate the tuple).
        results: list[CandidateResult] = []
        for fp in plan.field_plans:
            # Short-circuit: if the budget is already exceeded,
            # the field is UNRESOLVED with a BUDGET_EXCLUDES
            # diagnostic. The FieldRunner's per-step gate is
            # the real check (per capability); the pre-loop
            # check is a fast-path for "every remaining field
            # will hit the budget."
            if budget_tracker.is_exceeded():
                results.append(
                    CandidateResult(
                        field_id=fp.field_id,
                        field_path=fp.field_id,
                        field_type_name="STRING",
                        diagnostics=(
                            Diagnostic(
                                code=DiagnosticCode.BUDGET_EXCLUDES,
                                severity=DiagnosticSeverity.WARNING,
                                message=(f"budget exhausted; field {fp.field_id!r} skipped"),
                                context={
                                    "field_id": fp.field_id,
                                    "reason": budget_tracker.exceeded_reason(),
                                },
                            ),
                        ),
                    )
                )
                continue
            result = self._field_runner.run(
                field_plan=fp,
                raw_input=raw_input,
                input_profile=input_profile,
                registry=registry_dict,
                state=state,
                budget_tracker=budget_tracker,
            )
            results.append(result)
            state.field_results[fp.field_id] = [result]

        return results


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def run(
    plan: ExecutionPlan,
    raw_input: bytes,
    *,
    input_profile: InputProfile | None = None,
    registry: typing.Mapping[tuple[str, str], Capability] | None = None,
    budget: Budget | None = None,
    field_runner: FieldRunner | None = None,
) -> list[CandidateResult]:
    """Run *plan* against *raw_input* and return per-field candidate results.

    Functional wrapper around :class:`Executor` for callers that
    do not need to hold an :class:`Executor` instance.

    Args:
        plan: The :class:`ExecutionPlan` to run.
        raw_input: The raw input bytes.
        input_profile: Optional :class:`InputProfile`.
        registry: Optional capability registry. ``None`` uses
            the global :func:`all_capabilities` snapshot.
        budget: Optional :class:`Budget`.
        field_runner: Optional :class:`FieldRunner` (advanced:
            pass a custom runner to swap collaborators).

    Returns:
        A list of :class:`CandidateResult` records, one per
        field in *plan*, in plan order.
    """
    executor = Executor(field_runner=field_runner)
    return executor.run(
        plan=plan,
        raw_input=raw_input,
        input_profile=input_profile,
        registry=registry,
        budget=budget,
    )

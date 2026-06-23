"""Field runner — executes one :class:`FieldPlan` end-to-end.

The :class:`FieldRunner` is the unit of execution for a single
:class:`FieldPlan`. It walks the capability chain in order, invokes
each step, and accumulates the results into a per-field
:class:`CandidateResult` (defined in this module).

The :class:`FieldRunner` is **not** an authority on confidence (per
ADR-0005): it only collects candidates + evidence + diagnostics.
The Reconciler (Sprint 5) merges candidates and assigns confidence.

V1 invariants (per ``PACKAGE_STRUCTURE.md`` §6.4 and the Sprint 4
spec):

- The runner walks the chain **in plan order** (the planner's
  ordering is authoritative; the runner does not reorder).
- The runner stops on **chain exhaustion** (V1 has no
  confidence-based early stop; the Sprint 4 deliverable is
  "chain-exhausted only").
- The runner **never** assigns confidence. The
  :class:`CandidateResult` carries only candidates + evidence
  + diagnostics.
- The runner records **explicit ``UNRESOLVED``** candidates when
  the chain is exhausted without producing a candidate.
- The runner consults the :class:`BudgetTracker` *before* every
  invocation; if the budget would be exceeded, the runner
  short-circuits and emits a ``BUDGET_EXCEEDED`` diagnostic on
  the per-field result.
- The runner is **deterministic**: same plan + registry + input
  → same per-field :class:`CandidateResult`, byte-for-byte.

Cost attribution
----------------

The :class:`FieldRunner` uses the capability's
:class:`~paxman.capabilities.spec.CapabilitySpec.cost_estimate` as
the per-invocation cost hint. The plan does not embed cost (cost
is metadata, not plan state); the runner reads the spec from the
capability registry at execution time. This keeps the plan
serializable and version-independent.
"""

from __future__ import annotations

import typing

import attrs

from paxman.capabilities.base import Capability
from paxman.capabilities.result import (
    Candidate,
    CapabilityResult,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier
from paxman.errors import CapabilityError
from paxman.executor.budget_tracker import BudgetTracker
from paxman.executor.context import ContextBuilder
from paxman.executor.early_stop import EarlyStop, StopDecision
from paxman.executor.evidence import EvidenceCollector
from paxman.executor.execution_state import ExecutionState
from paxman.planner.field_plan import FieldPlan
from paxman.planner.input_profile import InputProfile

__all__ = ["CandidateResult", "FieldRunner"]


@attrs.frozen(slots=True)
class CandidateResult:
    """The per-field output of the Executor.

    Per ADR-0005, the :class:`CandidateResult` carries **no
    confidence field**. The Reconciler (Sprint 5) is the sole
    confidence authority. The Executor only collects the
    candidates + evidence + diagnostics.

    Attributes:
        field_id: The :class:`CanonicalField.id`.
        field_path: The :class:`CanonicalField.path`.
        field_type_name: The :class:`FieldType` value name.
        candidates: The merged :class:`Candidate` records from
            every capability invocation in the chain. May be
            empty (the chain was exhausted without producing a
            candidate).
        evidence: The :class:`EvidenceRef` records collected
            from every invocation. Defaults to an empty tuple.
        diagnostics: The :class:`Diagnostic` records collected
            from every invocation. Defaults to an empty tuple.
        steps_executed: The number of capability invocations
            that ran (0 or more).
        status: ``"RESOLVED"`` if at least one candidate was
            produced, ``"UNRESOLVED"`` otherwise. Defaults to
            ``"UNRESOLVED"``.

    Examples:
        >>> from paxman.capabilities.result import Candidate
        >>> r = CandidateResult(
        ...     field_id="f1",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ...     candidates=(Candidate(value="ACME"),),
        ...     steps_executed=1,
        ...     status="RESOLVED",
        ... )
        >>> r.status
        'RESOLVED'
    """

    field_id: str = attrs.field()
    field_path: str = attrs.field()
    field_type_name: str = attrs.field()
    candidates: tuple[Candidate, ...] = ()
    evidence: tuple[object, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    steps_executed: int = 0
    status: str = "UNRESOLVED"

    def __attrs_post_init__(self) -> None:
        """Validate invariants and auto-derive ``status`` from ``candidates``.

        Raises:
            ValueError: If ``field_id`` is empty or ``status`` is
                not one of the two valid values.
        """
        if not isinstance(self.field_id, str) or not self.field_id:
            raise ValueError(f"field_id must be a non-empty string, got {self.field_id!r}")
        if not isinstance(self.field_path, str):
            raise TypeError(f"field_path must be a str, got {type(self.field_path).__name__}")
        if not isinstance(self.field_type_name, str):
            raise TypeError(
                f"field_type_name must be a str, got {type(self.field_type_name).__name__}"
            )
        if not isinstance(self.candidates, tuple):
            raise TypeError(f"candidates must be a tuple, got {type(self.candidates).__name__}")
        if not isinstance(self.evidence, tuple):
            raise TypeError(f"evidence must be a tuple, got {type(self.evidence).__name__}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError(f"diagnostics must be a tuple, got {type(self.diagnostics).__name__}")
        if not isinstance(self.steps_executed, int) or isinstance(self.steps_executed, bool):
            raise TypeError(
                f"steps_executed must be an int, got {type(self.steps_executed).__name__}"
            )
        if self.steps_executed < 0:
            raise ValueError(f"steps_executed must be non-negative, got {self.steps_executed}")
        if self.status not in ("RESOLVED", "UNRESOLVED"):
            raise ValueError(f"status must be 'RESOLVED' or 'UNRESOLVED', got {self.status!r}")
        # The candidate count drives the status. An empty candidate
        # list ALWAYS means UNRESOLVED, regardless of what the
        # caller passed.
        if not self.candidates:
            object.__setattr__(self, "status", "UNRESOLVED")
        else:
            object.__setattr__(self, "status", "RESOLVED")


class FieldRunner:
    """Executes one :class:`FieldPlan` end-to-end.

    The :class:`FieldRunner` is stateless and safe to share across
    runs and threads (the only mutable state during a run is the
    :class:`ExecutionState` it is given).

    Examples:
        >>> runner = FieldRunner()
        >>> state = ExecutionState()
        >>> result = runner.run(
        ...     field_plan=FieldPlan(field_id="f1", capability_chain=()),
        ...     raw_input=b"ACME Corp",
        ...     input_profile=None,
        ...     registry={},
        ...     state=state,
        ... )
        >>> result.status
        'UNRESOLVED'
    """

    def __init__(
        self,
        *,
        context_builder: ContextBuilder | None = None,
        evidence_collector: EvidenceCollector | None = None,
        early_stop: EarlyStop | None = None,
    ) -> None:
        """Initialize the field runner.

        Args:
            context_builder: A :class:`ContextBuilder`. Defaults to
                a fresh instance.
            evidence_collector: An :class:`EvidenceCollector`.
                Defaults to a fresh instance.
            early_stop: An :class:`EarlyStop`. Defaults to a fresh
                instance.
        """
        self._context_builder = context_builder or ContextBuilder()
        self._evidence_collector = evidence_collector or EvidenceCollector()
        self._early_stop = early_stop or EarlyStop()

    def run(
        self,
        *,
        field_plan: FieldPlan,
        raw_input: bytes,
        input_profile: InputProfile | None,
        registry: dict[tuple[str, str], Capability],
        state: ExecutionState,
        budget_tracker: BudgetTracker | None = None,
    ) -> CandidateResult:
        """Execute *field_plan* and return a :class:`CandidateResult`.

        Args:
            field_plan: The :class:`FieldPlan` for one field.
            raw_input: The raw input bytes.
            input_profile: The :class:`InputProfile` for the
                input (used for the :class:`CapabilityContext.input_profile_type`).
                ``None`` is tolerated (the context defaults to
                ``"text"``).
            registry: A mapping of ``(capability_id, version)`` →
                :class:`Capability`. May be the global
                :func:`paxman.capabilities.registry.all_capabilities`
                snapshot.
            state: The :class:`ExecutionState` to update with
                counters, evidence, and diagnostics.
            budget_tracker: Optional :class:`BudgetTracker` for
                budget enforcement. ``None`` means no cap
                (every invocation is allowed).

        Returns:
            A :class:`CandidateResult` summarizing the run for
            the field. Always returns a value; never raises on
            capability failure (failures are encoded as
            diagnostics).
        """
        if not isinstance(field_plan, FieldPlan):
            raise TypeError(f"field_plan must be a FieldPlan, got {type(field_plan).__name__}")
        if not isinstance(raw_input, bytes):
            raise TypeError(f"raw_input must be bytes, got {type(raw_input).__name__}")
        if not isinstance(state, ExecutionState):
            raise TypeError(f"state must be an ExecutionState, got {type(state).__name__}")
        if not isinstance(registry, dict):
            raise TypeError(f"registry must be a dict, got {type(registry).__name__}")
        if budget_tracker is not None and not isinstance(budget_tracker, BudgetTracker):
            raise TypeError(
                f"budget_tracker must be a BudgetTracker or None, "
                f"got {type(budget_tracker).__name__}"
            )

        input_type = input_profile.input_type if input_profile is not None else "text"

        # Accumulators
        candidates: list[Candidate] = []
        evidence_list: list[object] = []
        diagnostics_list: list[Diagnostic] = []
        steps_executed = 0

        # Walk the chain. ``step_index`` is the index of the next
        # step the runner is about to invoke.
        step_index = 0
        while True:
            decision = self._early_stop.should_stop(
                field_plan=field_plan, current_step_index=step_index
            )
            if decision is StopDecision.CHAIN_EXHAUSTED:
                break
            step = field_plan.capability_chain[step_index]
            capability = registry.get((step.capability_id, step.capability_version))
            if capability is None:
                # Capability not registered. Emit a diagnostic
                # and continue. The Executor must not crash
                # because a step points at a missing capability.
                diagnostics_list.append(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            f"capability not registered: "
                            f"{step.capability_id}@{step.capability_version}"
                        ),
                        context={
                            "field_id": field_plan.field_id,
                            "field_path": _field_path_from_plan(field_plan),
                            "capability_id": step.capability_id,
                            "capability_version": step.capability_version,
                            "step_index": step_index,
                        },
                    )
                )
                step_index += 1
                continue

            # Build the per-step context. The context is fresh per
            # invocation so the capability cannot affect the
            # executor's state.
            spec = typing.cast(CapabilitySpec, capability.spec)
            tier = spec.tier
            field_path = _field_path_from_plan(field_plan)
            try:
                ctx = self._context_builder.build(
                    step=step,
                    raw_input=raw_input,
                    field_path=field_path,
                    field_type_name=_field_type_name_from_plan(field_plan),
                    input_profile_type=input_type,
                    tier=tier,
                )
            except (TypeError, ValueError) as e:
                # Malformed step → diagnostic, skip.
                diagnostics_list.append(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"context build failed for {step.capability_id}: {e}",
                        context={
                            "field_id": field_plan.field_id,
                            "capability_id": step.capability_id,
                            "error": str(e),
                        },
                    )
                )
                step_index += 1
                continue

            # Budget gate: if the would-be invocation exceeds a
            # cap, short-circuit. The tracker's
            # ``would_exceed_reason`` does NOT mutate the counters,
            # so we ask first and book later. Asking for the
            # reason (not just the bool) lets us record the
            # specific cap in the diagnostic.
            is_remote = tier is CapabilityTier.REMOTE_INFERENCE
            would_exceed_reason: str | None = None
            if budget_tracker is not None:
                would_exceed_reason = budget_tracker.would_exceed_reason(
                    cost_usd=spec.cost_estimate.usd,
                    latency_ms=spec.cost_estimate.ms,
                    is_remote_inference=is_remote,
                )
            if would_exceed_reason is not None:
                # ``budget_tracker`` is non-None because
                # ``would_exceed_reason`` is non-None; the
                # ``if budget_tracker is not None`` guard
                # above established that.
                if budget_tracker is None:  # pragma: no cover - defensive
                    raise RuntimeError("budget_tracker is None but would_exceed_reason is not None")
                state.mark_budget_exceeded(would_exceed_reason)
                # Also mark the tracker as exhausted so the
                # Executor's pre-loop gate (which calls
                # ``budget_tracker.is_exceeded()``) sees it.
                # The exact counter value does not matter; we
                # record a zero-cost invocation to flip the
                # ``exceeded`` flag.
                budget_tracker.mark_exhausted()
                diagnostics_list.append(
                    Diagnostic(
                        code=DiagnosticCode.BUDGET_EXCLUDES,
                        severity=DiagnosticSeverity.WARNING,
                        message=(
                            f"budget exceeded before invoking "
                            f"{step.capability_id}@{step.capability_version}"
                        ),
                        context={
                            "field_id": field_plan.field_id,
                            "field_path": field_path,
                            "capability_id": step.capability_id,
                            "capability_version": step.capability_version,
                            "reason": would_exceed_reason,
                            "spent_usd": budget_tracker.total_cost_usd,
                            "limit_usd": (
                                budget_tracker.budget.max_total_cost_usd
                                if budget_tracker.budget is not None
                                else None
                            ),
                        },
                    )
                )
                break

            # Invoke the capability.
            try:
                result: CapabilityResult = capability.invoke(ctx)
            except CapabilityError as e:
                # The capability raised a structured error.
                # Encode as a diagnostic; do not propagate.
                diagnostics_list.append(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=str(e),
                        context=e.context,
                    )
                )
                step_index += 1
                continue
            except Exception as e:
                # Defensive: a capability raised an unexpected
                # (non-CapabilityError) exception. Encode as a
                # diagnostic and continue. The Executor never
                # crashes on a capability bug.
                diagnostics_list.append(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(f"{step.capability_id} raised {type(e).__name__}: {e}"),
                        context={
                            "field_id": field_plan.field_id,
                            "capability_id": step.capability_id,
                            "exception_type": type(e).__name__,
                        },
                    )
                )
                step_index += 1
                continue

            # Book the cost. ``is_remote_inference`` is gated by
            # the spec's tier (not by a tag on the result).
            if budget_tracker is not None:
                budget_tracker.record(
                    cost_usd=spec.cost_estimate.usd,
                    latency_ms=spec.cost_estimate.ms,
                    is_remote_inference=is_remote,
                )
            state.record_invocation(
                cost_usd=spec.cost_estimate.usd,
                latency_ms=spec.cost_estimate.ms,
                is_remote_inference=is_remote,
            )
            steps_executed += 1

            # Collect candidates and evidence.
            for c in result.candidates:
                if isinstance(c, Candidate):
                    candidates.append(c)
            for ev in result.evidence:
                evidence_list.append(ev)
            for c in result.candidates:
                for ev in c.evidence_refs:
                    evidence_list.append(ev)

            # Per-invocation diagnostics: keep at the field level
            # (so the Reconciler can correlate with the candidate).
            for d in result.diagnostics:
                if isinstance(d, Diagnostic):
                    diagnostics_list.append(d)

            # Run-level collection (the evidence collector decides
            # what to promote to the run level).
            self._evidence_collector.collect(result, state=state)

            step_index += 1

        # The post-loop diagnostics from a budget short-circuit
        # include the BUDGET_EXCLUDES warning. The result is
        # whatever candidates we managed to collect.
        return CandidateResult(
            field_id=field_plan.field_id,
            field_path=_field_path_from_plan(field_plan),
            field_type_name=_field_type_name_from_plan(field_plan),
            candidates=tuple(candidates),
            evidence=tuple(evidence_list),
            diagnostics=tuple(diagnostics_list),
            steps_executed=steps_executed,
            status="RESOLVED" if candidates else "UNRESOLVED",
        )


def _field_path_from_plan(field_plan: FieldPlan) -> str:
    """Return a human-readable path for the field, defaulting to the id.

    The :class:`FieldPlan` does not embed the :class:`CanonicalField`
    (it carries the id only); the :class:`FieldRunner` cannot
    recover the path. The Reconciler (Sprint 5) and the artifact
    map ``field_id`` → ``field_path`` at composition time. For
    diagnostic context, the runner defaults to the id.
    """
    return field_plan.field_id


def _field_type_name_from_plan(field_plan: FieldPlan) -> str:
    """Return the field type name (best-effort).

    The :class:`FieldPlan` does not carry the
    :class:`CanonicalField.type`. The :class:`FieldRunner` records
    ``"STRING"`` as a safe default. The Reconciler fills in the
    real type from the canonical contract.
    """
    return "STRING"

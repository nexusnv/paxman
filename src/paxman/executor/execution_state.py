"""Transient in-flight state for plan execution.

The :class:`ExecutionState` is the Executor's **working memory** during a
single :func:`paxman.executor.executor.run` call. It accumulates:

- per-field candidate results (a mapping of ``field_id`` to the running
  candidates and evidence collected so far),
- aggregate statistics (cumulative cost, latency, and invocation count),
- collected diagnostics from the planner and from capability invocations,
- collected evidence references from every capability invocation,
- a flag indicating whether the budget has been exhausted (and which
  cap was hit).

The :class:`ExecutionState` is **not authoritative**: it is a transient
view. The authoritative per-field output is the :class:`CandidateResult`
returned by :func:`paxman.executor.executor.run`. The state object is
discarded at the end of a run.

V1 invariants (per ``PACKAGE_STRUCTURE.md`` §6.4 and the Sprint 4 spec):

- The state is **mutable in-flight** — the Executor mutates it
  incrementally. This is the one place in Paxman where mutation is
  allowed (everything else is frozen attrs).
- The state is **never** written to the artifact or replayed; it is
  transient.
- The state is **deterministic** — the same plan + registry + input
  produces the same state at the end of the run, byte-for-byte.
- The state has no I/O, no clock reads, and no randomness.

This module is a leaf in the executor subsystem — it depends only on
cross-cutting modules and the planner's data models.
"""

from __future__ import annotations

import typing

import attrs

from paxman.capabilities.result import Diagnostic, EvidenceRef
from paxman.planner.field_plan import FieldPlan

__all__ = ["ExecutionState"]


@attrs.define(slots=True, eq=False, hash=False)
class ExecutionState:
    """Transient in-flight state for one :func:`executor.run` call.

    Mutable on purpose: the Executor appends to the per-field maps and
    counters as it walks the plan. The state is discarded at the end
    of the run; it is never persisted.

    Attributes:
        field_results: A mapping of ``field_id`` to the running list of
            :class:`~paxman.executor.field_runner.CandidateResult`
            records collected so far. Initialized empty; the
            :class:`~paxman.executor.field_runner.FieldRunner` appends
            one entry per capability invocation.
        total_cost_usd: Cumulative USD cost across all capability
            invocations in this run. Defaults to ``0.0``.
        total_latency_ms: Cumulative wall-clock latency across all
            capability invocations. Defaults to ``0``.
        invocation_count: Total number of capability invocations
            attempted in this run. Defaults to ``0``.
        remote_inference_count: Number of remote-inference invocations
            (``REMOTE_INFERENCE``-tier capabilities). Defaults to ``0``.
        budget_exceeded: ``True`` if the budget was hit and the
            Executor short-circuited. Defaults to ``False``.
        budget_exceeded_reason: A human-readable reason for the
            short-circuit (e.g., ``"max_total_cost_usd"``). ``None``
            if the budget is not exceeded.
        diagnostics: A list of :class:`Diagnostic` records collected
            from capability invocations. Defaults to an empty list.
        evidence: A list of :class:`EvidenceRef` records collected
            from every capability invocation. Defaults to an empty
            list.
        field_plans: A mapping of ``field_id`` to the originating
            :class:`FieldPlan`. Set once at construction time and
            never mutated; used by the Executor to look up the
            target_confidence and fallback_policy for each field.

    Examples:
        >>> state = ExecutionState(field_plans={})
        >>> state.total_cost_usd
        0.0
        >>> state.invocation_count
        0
    """

    field_plans: dict[str, FieldPlan] = attrs.field(factory=dict)
    field_results: dict[str, list[object]] = attrs.field(factory=dict)
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    invocation_count: int = 0
    remote_inference_count: int = 0
    budget_exceeded: bool = False
    budget_exceeded_reason: str | None = None
    diagnostics: list[Diagnostic] = attrs.field(factory=list)
    evidence: list[EvidenceRef] = attrs.field(factory=list)

    def record_invocation(
        self,
        *,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        is_remote_inference: bool = False,
    ) -> None:
        """Update aggregate counters after a capability invocation.

        Args:
            cost_usd: The USD cost of this invocation (non-negative).
                Defaults to ``0.0``.
            latency_ms: The wall-clock latency in milliseconds
                (non-negative). Defaults to ``0``.
            is_remote_inference: ``True`` if this was a remote-inference
                call (``REMOTE_INFERENCE``-tier). Defaults to ``False``.
        """
        # Oracle review F2: defensive against non-numeric cost. Calling
        # code may pass a Decimal-like object; coerce to float and
        # reject negatives to keep the budget tracking honest.
        cost = float(cost_usd)
        if cost < 0:
            raise ValueError(f"cost_usd must be non-negative, got {cost_usd!r}")
        if latency_ms < 0:
            raise ValueError(f"latency_ms must be non-negative, got {latency_ms!r}")
        self.total_cost_usd += cost
        self.total_latency_ms += int(latency_ms)
        self.invocation_count += 1
        if is_remote_inference:
            self.remote_inference_count += 1

    def mark_budget_exceeded(self, reason: str) -> None:
        """Mark the budget as exceeded and record the reason.

        Args:
            reason: A short identifier for the cap that was hit
                (e.g., ``"max_total_cost_usd"``,
                ``"max_total_latency_ms"``,
                ``"max_remote_inference_calls"``,
                ``"max_capability_invocations"``).
        """
        self.budget_exceeded = True
        self.budget_exceeded_reason = reason

    def add_diagnostic(self, diagnostic: Diagnostic) -> None:
        """Append a :class:`Diagnostic` to the run-level diagnostics list.

        Args:
            diagnostic: The diagnostic to record.
        """
        if not isinstance(diagnostic, Diagnostic):
            raise TypeError(f"diagnostic must be a Diagnostic, got {type(diagnostic).__name__}")
        self.diagnostics.append(diagnostic)

    def add_evidence(self, evidence: EvidenceRef) -> None:
        """Append an :class:`EvidenceRef` to the run-level evidence list.

        Args:
            evidence: The evidence reference to record.
        """
        if not isinstance(evidence, EvidenceRef):
            raise TypeError(f"evidence must be an EvidenceRef, got {type(evidence).__name__}")
        self.evidence.append(evidence)

    def init_field(self, field_id: str) -> None:
        """Initialize the per-field result list for *field_id*.

        Idempotent: re-initializing a known field is a no-op so the
        Executor can call this in any order.

        Args:
            field_id: The :class:`CanonicalField` id.
        """
        self.field_results.setdefault(field_id, [])

    @typing.overload
    def get_field_results(self, field_id: str) -> list[object]:
        """Overload: return field results as ``list[object]``."""
        ...

    @typing.overload
    def get_field_results(self, field_id: str, *, as_type: type[typing.Any]) -> list[typing.Any]:
        """Overload: return field results narrowed to ``as_type``."""
        ...

    def get_field_results(
        self, field_id: str, *, as_type: type[typing.Any] | None = None
    ) -> list[object]:
        """Return the collected results for *field_id*.

        Args:
            field_id: The :class:`CanonicalField` id.
            as_type: Optional type to narrow the return value's static
                type (no runtime check; the field is typed ``object``).

        Returns:
            The list of :class:`CandidateResult` records (or ``[]`` if
            the field has not been touched yet).
        """
        results = self.field_results.get(field_id, [])
        if as_type is not None:
            return typing.cast(list[typing.Any], results)
        return results

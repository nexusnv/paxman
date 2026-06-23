"""Early-stop policy for the Executor.

The :class:`EarlyStop` is the Executor's gate that decides whether to
walk the next :class:`FieldPlanStep` or to short-circuit. Per the
Sprint 4 spec, the V1 early-stop is **chain-exhaustion only** — the
Executor stops when a field's capability chain is exhausted, not
when a candidate meets ``target_confidence`` (the Reconciler
assigns confidence in Sprint 5; capabilities do not return
confidence per ADR-0005).

This module exists for two reasons:

1. **It is the future-proofing seam for confidence-based early stop.**
   The Sprint 4 deliverable is "just chain-exhausted logic," but the
   API of :class:`EarlyStop` is shaped so that the Reconciler (Sprint 5)
   can plug in a confidence-based gate without changing the
   :class:`FieldRunner` call site.
2. **It centralizes the "should I keep going?" decision** so the
   :class:`FieldRunner` stays focused on invoking capabilities and
   collecting results.

V1 policy (per ``docs/sprints/sprint-04-executor-and-capabilities.md``):

- **Stop when the chain is empty** (no more steps for the field).
- **Stop when the field's ``early_stop=False`` and the plan is empty.**
- **Stop on budget exhaustion** — but the :class:`BudgetTracker`
  raises this; the :class:`EarlyStop` is **not** the budget gate
  (the Executor checks the budget before invoking).

The :class:`EarlyStop` is stateless and pure. The :class:`FieldRunner`
calls :meth:`should_stop` after each invocation; the result is a
:class:`StopDecision` value.
"""

from __future__ import annotations

import enum

from paxman.planner.field_plan import FieldPlan, FieldPlanStep

__all__ = ["EarlyStop", "StopDecision"]


class StopDecision(enum.Enum):
    """Why the Executor should stop (or continue) walking a field's chain.

    Values:
        CONTINUE: Keep invoking the next step. The chain is not
            exhausted; the budget is fine.
        CHAIN_EXHAUSTED: The chain has no more steps. The field
            gets an ``UNRESOLVED`` candidate if no candidate was
            produced in the prior steps.
    """

    CONTINUE = "CONTINUE"
    CHAIN_EXHAUSTED = "CHAIN_EXHAUSTED"


class EarlyStop:
    """V1 early-stop policy for the Executor.

    The class is stateless and safe to share across runs. All state
    is supplied as method arguments.

    Examples:
        >>> es = EarlyStop()
        >>> es.should_stop(
        ...     field_plan=FieldPlan(field_id="f1", capability_chain=()),
        ...     current_step_index=0,
        ... )
        <StopDecision.CHAIN_EXHAUSTED: 'CHAIN_EXHAUSTED'>
    """

    def should_stop(
        self,
        *,
        field_plan: FieldPlan,
        current_step_index: int,
    ) -> StopDecision:
        """Decide whether to keep walking the field's chain.

        Args:
            field_plan: The :class:`FieldPlan` for the field being
                executed.
            current_step_index: The zero-based index of the
                *next* step the Executor is about to invoke.
                ``0`` is the first step; ``len(field_plan.capability_chain)``
                means the chain is exhausted.

        Returns:
            A :class:`StopDecision`:

            - :attr:`StopDecision.CHAIN_EXHAUSTED` if
              ``current_step_index >= len(field_plan.capability_chain)``.
            - :attr:`StopDecision.CONTINUE` otherwise.
        """
        # The chain is exhausted when the next step index is past
        # the end. The ``current_step_index`` is the index of the
        # step the Executor is *about* to invoke, so
        # ``current_step_index == len(chain)`` means "no more steps."
        if current_step_index >= len(field_plan.capability_chain):
            return StopDecision.CHAIN_EXHAUSTED
        return StopDecision.CONTINUE

    def next_step(self, field_plan: FieldPlan, current_step_index: int) -> FieldPlanStep | None:
        """Return the next :class:`FieldPlanStep`, or ``None`` if the chain is empty.

        Convenience helper: equivalent to
        ``field_plan.capability_chain[current_step_index]`` but
        returns ``None`` on out-of-bounds instead of raising
        :class:`IndexError`. The :class:`FieldRunner` uses this to
        avoid try/except on the index access.

        Args:
            field_plan: The :class:`FieldPlan` for the field.
            current_step_index: The zero-based index of the next step.

        Returns:
            The next :class:`FieldPlanStep`, or ``None`` if
            ``current_step_index`` is past the end of the chain.
        """
        if current_step_index >= len(field_plan.capability_chain):
            return None
        return field_plan.capability_chain[current_step_index]

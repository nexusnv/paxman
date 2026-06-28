"""Evidence and diagnostic collection for the Executor.

This module is a **pure** evidence/diagnostic aggregator: it merges
:class:`EvidenceRef` and :class:`Diagnostic` records from capability
invocations into the run-level :class:`ExecutionState`. The actual
mutation lives in :class:`ExecutionState`; this module is the policy
that decides what to keep, what to drop, and what to surface as a
run-level diagnostic.

Design notes
------------

- **Evidence is monotonic.** Once a piece of evidence is recorded,
  it is never removed. The Reconciler decides what to
  believe; the Executor only collects.
- **Diagnostics may be downgraded or dropped.** A capability-level
  diagnostic (e.g., ``PATTERN_NO_MATCH``) is **per-invocation** and
  stays with the :class:`CapabilityResult`. The Executor only
  collects run-level diagnostics (e.g., ``BUDGET_EXCEEDED``,
  ``CAPABILITY_INVOKE_FAILED`` at the run scope).
- **Run-level diagnostics are de-duplicated by code+message** so
  a single field with three repeated ``PATTERN_NO_MATCH`` errors
  becomes one diagnostic at the run level. (Per-invocation
  diagnostics are not de-duplicated; they live with the
  :class:`CapabilityResult`.)

The :class:`EvidenceCollector` is stateless. It is invoked once per
capability invocation by the :class:`FieldRunner`.
"""

from __future__ import annotations

from paxman.capabilities.result import (
    CapabilityResult,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.executor.execution_state import ExecutionState

__all__ = ["EvidenceCollector"]


class EvidenceCollector:
    """Collects evidence and run-level diagnostics from capability invocations.

    Stateless. :meth:`collect` takes a :class:`CapabilityResult` and
    a :class:`FieldPlanStep` (the step that produced it) and updates
    the :class:`ExecutionState` in place.

    Examples:
        >>> state = ExecutionState()
        >>> collector = EvidenceCollector()
        >>> result = CapabilityResult(candidates=(), diagnostics=())
        >>> collector.collect(result, state=state)
    """

    def collect(
        self,
        result: CapabilityResult,
        *,
        state: ExecutionState,
    ) -> None:
        """Merge a :class:`CapabilityResult` into the :class:`ExecutionState`.

        Args:
            result: The :class:`CapabilityResult` produced by one
                capability invocation.
            state: The :class:`ExecutionState` to update.
        """
        if not isinstance(result, CapabilityResult):
            raise TypeError(f"result must be a CapabilityResult, got {type(result).__name__}")
        if not isinstance(state, ExecutionState):
            raise TypeError(f"state must be an ExecutionState, got {type(state).__name__}")

        # Evidence: append every EvidenceRef from the result. Both
        # ``result.evidence`` (the run-level evidence, including
        # evidence not attached to any candidate) and
        # ``candidate.evidence_refs`` (per-candidate evidence) are
        # added to the run-level evidence list. The Reconciler
        # decides which ones to believe; the Executor collects
        # all of them.
        for ev in result.evidence:
            if isinstance(ev, EvidenceRef):
                state.add_evidence(ev)
        for cand in result.candidates:
            for ev in cand.evidence_refs:
                if isinstance(ev, EvidenceRef):
                    state.add_evidence(ev)

        # Diagnostics: de-duplicate run-level diagnostics.
        # Per the policy: only error-severity diagnostics and
        # INFERENCE_OUTPUT_UNTRUSTED warnings are promoted to
        # the run level. INFO/WARNING diagnostics (e.g.,
        # PATTERN_NO_MATCH) stay with the per-invocation
        # result — they are not noise at the run level.
        for d in result.diagnostics:
            if not isinstance(d, Diagnostic):
                continue
            if _should_promote_to_run_level(d):
                state.add_diagnostic(d)


def _should_promote_to_run_level(diagnostic: Diagnostic) -> bool:
    """Return ``True`` if *diagnostic* should be elevated to run-level.

    The rule:

    - ``ERROR`` severity → always promote.
    - ``WARNING`` severity for the untrusted-inference warning
      (``INFERENCE_OUTPUT_UNTRUSTED``) → promote (the Reconciler
      must see this).
    - All other ``WARNING`` and ``INFO`` severities → keep at
      the per-invocation level (no run-level noise).

    Args:
        diagnostic: The :class:`Diagnostic` to evaluate.

    Returns:
        ``True`` if the diagnostic belongs in the run-level list.
    """
    if diagnostic.severity is DiagnosticSeverity.ERROR:
        return True
    if (
        diagnostic.severity is DiagnosticSeverity.WARNING
        and diagnostic.code is DiagnosticCode.INFERENCE_OUTPUT_UNTRUSTED
    ):
        return True
    return False

"""Unit tests for :mod:`paxman.executor.evidence`.

Per Sprint 4 D4.3: ``EvidenceCollector`` merges a
``CapabilityResult`` into the ``ExecutionState``. The tests pin
the policy:

- Evidence is appended (never removed).
- ERROR diagnostics are promoted to the run level.
- INFERENCE_OUTPUT_UNTRUSTED warnings are promoted.
- Other WARNING and INFO diagnostics stay at the per-invocation level.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.result import (
    Candidate,
    CapabilityResult,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.executor.evidence import EvidenceCollector
from paxman.executor.execution_state import ExecutionState

pytestmark = pytest.mark.unit


def _ev(capability_id: str = "text_extraction") -> EvidenceRef:
    return EvidenceRef(
        capability_id=capability_id,
        capability_version="1.0",
        field_path="x",
    )


def _diag(
    code: DiagnosticCode,
    severity: DiagnosticSeverity = DiagnosticSeverity.INFO,
) -> Diagnostic:
    return Diagnostic(code=code, severity=severity, message="m")


def _candidate(value: object, *evidence: EvidenceRef) -> Candidate:
    return Candidate(value=value, evidence_refs=tuple(evidence))


# --- evidence collection --------------------------------------------


def test_collect_appends_run_level_evidence() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    ev = _ev("regex_extraction")
    result = CapabilityResult(evidence=(ev,))
    collector.collect(result, state=state)
    assert state.evidence == [ev]


def test_collect_appends_per_candidate_evidence() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    ev1 = _ev("regex_extraction")
    ev2 = _ev("validation")
    result = CapabilityResult(
        candidates=(_candidate("ACME", ev1, ev2),),
    )
    collector.collect(result, state=state)
    # Both evidence refs are recorded (deduplication is the
    # Reconciler's job, not the Executor's).
    assert state.evidence == [ev1, ev2]


def test_collect_accumulates_across_calls() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    collector.collect(
        CapabilityResult(evidence=(_ev("a"),)),
        state=state,
    )
    collector.collect(
        CapabilityResult(evidence=(_ev("b"),)),
        state=state,
    )
    assert len(state.evidence) == 2


# --- diagnostic promotion -------------------------------------------


def test_collect_promotes_error_diagnostics() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    d = _diag(DiagnosticCode.CAPABILITY_INVOKE_FAILED, DiagnosticSeverity.ERROR)
    result = CapabilityResult(diagnostics=(d,))
    collector.collect(result, state=state)
    assert d in state.diagnostics


def test_collect_promotes_inference_untrusted_warning() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    d = _diag(DiagnosticCode.INFERENCE_OUTPUT_UNTRUSTED, DiagnosticSeverity.WARNING)
    result = CapabilityResult(diagnostics=(d,))
    collector.collect(result, state=state)
    assert d in state.diagnostics


def test_collect_does_not_promote_pattern_no_match_info() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    d = _diag(DiagnosticCode.PATTERN_NO_MATCH, DiagnosticSeverity.INFO)
    result = CapabilityResult(diagnostics=(d,))
    collector.collect(result, state=state)
    # PATTERN_NO_MATCH is per-invocation, not run-level.
    assert state.diagnostics == []


def test_collect_does_not_promote_validation_failed_warning() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    d = _diag(DiagnosticCode.VALIDATION_FAILED, DiagnosticSeverity.WARNING)
    result = CapabilityResult(diagnostics=(d,))
    collector.collect(result, state=state)
    # VALIDATION_FAILED is per-invocation.
    assert state.diagnostics == []


def test_collect_rejects_non_capability_result() -> None:
    state = ExecutionState()
    collector = EvidenceCollector()
    with pytest.raises(TypeError, match="result must be a CapabilityResult"):
        collector.collect("not a result", state=state)  # type: ignore[arg-type]


def test_collect_rejects_non_execution_state() -> None:
    collector = EvidenceCollector()
    with pytest.raises(TypeError, match="state must be an ExecutionState"):
        collector.collect(
            CapabilityResult(),
            state="not a state",  # type: ignore[arg-type]
        )

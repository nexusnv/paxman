"""Unit tests for :mod:`paxman.capabilities.result` — the result data models.

Per Sprint 3 D3.10, the ``CapabilityResult`` data model is the only
return type of a capability invocation. Per ADR-0005, it MUST NOT
carry a ``confidence`` field; the static check
``test_capability_result_has_no_confidence`` enforces this.
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

pytestmark = pytest.mark.unit


# --- Diagnostic ------------------------------------------------------------


def test_diagnostic_minimal() -> None:
    """Diagnostic with only the required code is valid; defaults apply."""
    d = Diagnostic(code=DiagnosticCode.PATTERN_NO_MATCH)
    assert d.code is DiagnosticCode.PATTERN_NO_MATCH
    assert d.severity is DiagnosticSeverity.INFO
    assert d.message == ""
    assert d.context == {}


def test_diagnostic_with_all_fields() -> None:
    """All Diagnostic fields can be set; valid types are accepted."""
    d = Diagnostic(
        code=DiagnosticCode.VALIDATION_FAILED,
        severity=DiagnosticSeverity.WARNING,
        message="3 constraints failed",
        context={"field_path": "x", "n": 3},
    )
    assert d.severity is DiagnosticSeverity.WARNING
    assert d.message == "3 constraints failed"
    assert d.context == {"field_path": "x", "n": 3}


def test_diagnostic_rejects_non_code() -> None:
    """A non-DiagnosticCode raises TypeError."""
    with pytest.raises(TypeError, match="code must be a DiagnosticCode"):
        Diagnostic(code="PATTERN_NO_MATCH")  # type: ignore[arg-type]


def test_diagnostic_rejects_non_severity() -> None:
    """A non-DiagnosticSeverity raises TypeError."""
    with pytest.raises(TypeError, match="severity must be a DiagnosticSeverity"):
        Diagnostic(
            code=DiagnosticCode.PATTERN_NO_MATCH,
            severity="INFO",  # type: ignore[arg-type]
        )


# --- EvidenceRef -----------------------------------------------------------


def test_evidence_ref_minimal() -> None:
    """EvidenceRef with the 3 required fields is valid."""
    ev = EvidenceRef(
        capability_id="regex_extraction",
        capability_version="1.0",
        field_path="supplier_name",
    )
    assert ev.capability_id == "regex_extraction"
    assert ev.capability_version == "1.0"
    assert ev.field_path == "supplier_name"
    assert ev.span is None
    assert ev.model_id is None
    assert ev.context == {}


def test_evidence_ref_with_span() -> None:
    """EvidenceRef accepts a valid (start, end) span."""
    ev = EvidenceRef(
        capability_id="regex_extraction",
        capability_version="1.0",
        field_path="x",
        span=(0, 10),
    )
    assert ev.span == (0, 10)


def test_evidence_ref_rejects_empty_capability_id() -> None:
    """An empty capability_id raises ValueError."""
    with pytest.raises(ValueError, match="capability_id must be a non-empty string"):
        EvidenceRef(
            capability_id="",
            capability_version="1.0",
            field_path="x",
        )


def test_evidence_ref_rejects_empty_version() -> None:
    """An empty capability_version raises ValueError."""
    with pytest.raises(ValueError, match="capability_version must be a non-empty string"):
        EvidenceRef(
            capability_id="x",
            capability_version="",
            field_path="x",
        )


def test_evidence_ref_rejects_empty_field_path() -> None:
    """An empty field_path raises ValueError."""
    with pytest.raises(ValueError, match="field_path must be a non-empty string"):
        EvidenceRef(
            capability_id="x",
            capability_version="1.0",
            field_path="",
        )


def test_evidence_ref_rejects_inverted_span() -> None:
    """A span with start > end raises ValueError."""
    with pytest.raises(ValueError, match="span start must be <="):
        EvidenceRef(
            capability_id="x",
            capability_version="1.0",
            field_path="x",
            span=(10, 5),
        )


def test_evidence_ref_rejects_negative_span() -> None:
    """A span with negative offsets raises ValueError."""
    with pytest.raises(ValueError, match="span offsets must be non-negative"):
        EvidenceRef(
            capability_id="x",
            capability_version="1.0",
            field_path="x",
            span=(-1, 5),
        )


# --- Candidate -------------------------------------------------------------


def test_candidate_minimal() -> None:
    """Candidate with only the required value is valid."""
    c = Candidate(value="ACME Corp")
    assert c.value == "ACME Corp"
    assert c.evidence_refs == ()
    assert c.diagnostics == ()


def test_candidate_rejects_list_evidence() -> None:
    """A list (not tuple) of evidence_refs raises TypeError."""
    with pytest.raises(TypeError, match="evidence_refs must be a tuple"):
        Candidate(
            value="x",
            evidence_refs=[],  # type: ignore[arg-type]
        )


def test_candidate_rejects_list_diagnostics() -> None:
    """A list (not tuple) of diagnostics raises TypeError."""
    with pytest.raises(TypeError, match="diagnostics must be a tuple"):
        Candidate(
            value="x",
            diagnostics=[],  # type: ignore[arg-type]
        )


# --- CapabilityResult ------------------------------------------------------


def test_capability_result_empty() -> None:
    """An empty CapabilityResult is valid (no candidates, no evidence)."""
    r = CapabilityResult()
    assert r.candidates == ()
    assert r.evidence == ()
    assert r.diagnostics == ()


def test_capability_result_with_candidates() -> None:
    """A CapabilityResult with candidates and evidence is valid."""
    c = Candidate(value="ACME")
    ev = EvidenceRef(
        capability_id="regex_extraction",
        capability_version="1.0",
        field_path="supplier_name",
    )
    r = CapabilityResult(
        candidates=(c,),
        evidence=(ev,),
    )
    assert r.candidates == (c,)
    assert r.evidence == (ev,)


def test_capability_result_rejects_list_candidates() -> None:
    """A list (not tuple) of candidates raises TypeError."""
    with pytest.raises(TypeError, match="candidates must be a tuple"):
        CapabilityResult(candidates=[])  # type: ignore[arg-type]


def test_capability_result_rejects_list_evidence() -> None:
    """A list (not tuple) of evidence raises TypeError."""
    with pytest.raises(TypeError, match="evidence must be a tuple"):
        CapabilityResult(evidence=[])  # type: ignore[arg-type]


def test_capability_result_rejects_list_diagnostics() -> None:
    """A list (not tuple) of diagnostics raises TypeError."""
    with pytest.raises(TypeError, match="diagnostics must be a tuple"):
        CapabilityResult(diagnostics=[])  # type: ignore[arg-type]


# --- ADR-0005 structural check: CapabilityResult has NO confidence field ---


@pytest.mark.deterministic
def test_capability_result_has_no_confidence_attribute() -> None:
    """ADR-0005: CapabilityResult has no ``confidence`` field.

    The static check uses :func:`hasattr` and :func:`getattr` to
    confirm that ``confidence`` is not a defined attribute of the
    class. A capability that tries to set ``confidence`` would not
    be type-checked (no field exists) and would fail at runtime if
    it tried to assign one.
    """
    assert not hasattr(CapabilityResult, "confidence")
    # The instance has no ``confidence`` attribute either.
    r = CapabilityResult()
    assert not hasattr(r, "confidence")
    # getattr with a default also returns the default, confirming
    # the attribute is missing.
    assert getattr(r, "confidence", None) is None


@pytest.mark.deterministic
def test_candidate_has_no_confidence_attribute() -> None:
    """ADR-0005: Candidate has no ``confidence`` field either."""
    assert not hasattr(Candidate, "confidence")
    c = Candidate(value="ACME")
    assert not hasattr(c, "confidence")
    assert getattr(c, "confidence", None) is None


@pytest.mark.deterministic
def test_capability_result_is_frozen() -> None:
    """CapabilityResult is frozen (immutable)."""
    import attrs.exceptions

    r = CapabilityResult()
    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        r.candidates = ()  # type: ignore[misc]

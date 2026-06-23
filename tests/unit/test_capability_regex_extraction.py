"""Unit tests for :mod:`paxman.capabilities.v1.regex_extraction`.

Per Sprint 3 D3.13: ``regex_extraction`` is a V1 deterministic
capability that uses Python's :mod:`re` for pattern matching. The
capability produces one candidate per match in the input.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import (
    DiagnosticCode,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.regex_extraction import RegexExtractionCapability

pytestmark = pytest.mark.unit


def _ctx(
    raw: bytes = b"",
    field_path: str = "supplier_name",
    field_type: str = "STRING",
    config: dict | None = None,
) -> CapabilityContext:
    return CapabilityContext(
        raw_input=raw,
        field_path=field_path,
        field_type_name=field_type,
        config=config or {},
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    """The spec is regex_extraction@1.0, LOCAL_DETERMINISTIC, free."""
    cap = RegexExtractionCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "regex_extraction"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)


# --- basic matching -------------------------------------------------------


def test_extracts_match_without_named_group() -> None:
    """A pattern without a named group returns the whole match."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"ACME Corp", config={"pattern": r"^[A-Z][A-Za-z ]+$"}))
    assert [c.value for c in result.candidates] == ["ACME Corp"]


def test_extracts_named_group() -> None:
    """A pattern with a single named group returns the group value."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"Invoice #1234", config={"pattern": r"Invoice #(?P<num>\d+)"}))
    assert [c.value for c in result.candidates] == ["1234"]


def test_extracts_multiple_matches() -> None:
    """Multiple matches in the input produce multiple candidates."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"acme.com foo.com bar.com", config={"pattern": r"\b[a-z]+\.com\b"}))
    assert [c.value for c in result.candidates] == ["acme.com", "foo.com", "bar.com"]


def test_no_match_emits_diagnostic() -> None:
    """No matches → empty candidates + a PATTERN_NO_MATCH diagnostic."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"hello", config={"pattern": r"^\d+$"}))
    assert result.candidates == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code is DiagnosticCode.PATTERN_NO_MATCH


# --- error paths ----------------------------------------------------------


def test_missing_pattern_returns_error() -> None:
    """Missing config['pattern'] returns an error diagnostic."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"hi", config={}))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_invalid_pattern_returns_error() -> None:
    """A pattern that fails to compile returns an error diagnostic."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"hi", config={"pattern": r"(unclosed"}))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_multiple_named_groups_rejected() -> None:
    """V1 rejects patterns with > 1 named group (Sprint 3 risk register)."""
    cap = RegexExtractionCapability()
    result = cap.invoke(
        _ctx(
            b"abc 123",
            config={"pattern": r"(?P<a>\w+) (?P<b>\d+)"},
        )
    )
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


# --- evidence -------------------------------------------------------------


def test_evidence_includes_span() -> None:
    """Each candidate carries an EvidenceRef with a (start, end) span."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"ACME Corp", config={"pattern": r"^[A-Z][A-Za-z ]+$"}))
    assert len(result.candidates) == 1
    ev = result.candidates[0].evidence_refs[0]
    assert ev.capability_id == "regex_extraction"
    assert ev.capability_version == "1.0"
    assert ev.field_path == "supplier_name"
    assert ev.span is not None
    start, end = ev.span
    assert start == 0
    assert end == len(b"ACME Corp")


def test_evidence_includes_group_name_for_named_patterns() -> None:
    """When the pattern has a named group, the evidence records the name."""
    cap = RegexExtractionCapability()
    result = cap.invoke(_ctx(b"Invoice #1234", config={"pattern": r"Invoice #(?P<num>\d+)"}))
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context == {"group_name": "num"}


# --- determinism ----------------------------------------------------------


@pytest.mark.deterministic
def test_determinism() -> None:
    """Same input + same pattern = same candidates, byte-equal."""
    cap = RegexExtractionCapability()
    ctx = _ctx(b"ACME Corp foo bar", config={"pattern": r"\b\w+\b"})
    r1 = cap.invoke(ctx)
    r2 = cap.invoke(ctx)
    assert [c.value for c in r1.candidates] == [c.value for c in r2.candidates]
    assert [c.evidence_refs[0].span for c in r1.candidates] == [
        c.evidence_refs[0].span for c in r2.candidates
    ]

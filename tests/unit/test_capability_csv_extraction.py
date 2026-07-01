"""Unit tests for :mod:`paxman.capabilities.v1.csv_extraction`.

V1 deterministic capability that resolves a named column (or column
index) against the raw input parsed as CSV.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode, DiagnosticSeverity
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.csv_extraction import CsvExtractionCapability

pytestmark = pytest.mark.unit


def _ctx(raw: bytes = b"", **cfg: object) -> CapabilityContext:
    return CapabilityContext(
        raw_input=raw,
        field_path="supplier_name",
        field_type_name="STRING",
        config=cfg,
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    """The spec is csv_extraction@1.0, LOCAL_DETERMINISTIC, free."""
    cap = CsvExtractionCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "csv_extraction"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    assert "STRING" in spec.input_types
    assert "MIXED" in spec.input_types


# --- happy path -----------------------------------------------------------


def test_extracts_named_column() -> None:
    """A named column returns one value per non-empty data row."""
    cap = CsvExtractionCapability()
    raw = b"supplier,amount\nACME,100\nFoo,200\n"
    result = cap.invoke(_ctx(raw, column="supplier"))
    assert [c.value for c in result.candidates] == ["ACME", "Foo"]
    ev = result.candidates[0].evidence_refs[0]
    assert ev.capability_id == "csv_extraction"
    assert ev.context["csv_column"] == "supplier"
    assert ev.context["row_index"] == 1


def test_extracts_column_by_index() -> None:
    """A column index (int) returns one value per non-empty data row."""
    cap = CsvExtractionCapability()
    raw = b"supplier,amount\nACME,100\nFoo,200\n"
    result = cap.invoke(_ctx(raw, column=0))
    assert [c.value for c in result.candidates] == ["ACME", "Foo"]


def test_skips_empty_cells() -> None:
    """Empty cells in the data rows are silently skipped."""
    cap = CsvExtractionCapability()
    raw = b"name,amount\nACME,100\n,200\nFoo,300\n"
    result = cap.invoke(_ctx(raw, column="name"))
    assert [c.value for c in result.candidates] == ["ACME", "Foo"]


def test_handles_quoted_cells_with_commas() -> None:
    """Quoted cells containing commas are preserved verbatim."""
    cap = CsvExtractionCapability()
    raw = b'supplier\n"ACME, Inc."\nFoo Bar\n'
    result = cap.invoke(_ctx(raw, column="supplier"))
    assert [c.value for c in result.candidates] == ["ACME, Inc.", "Foo Bar"]


def test_handles_tab_delimiter() -> None:
    """Tab-delimited input is detected and parsed."""
    cap = CsvExtractionCapability()
    raw = b"supplier\tamount\nACME\t100\nFoo\t200\n"
    result = cap.invoke(_ctx(raw, column="supplier"))
    assert [c.value for c in result.candidates] == ["ACME", "Foo"]


def test_unicode_input() -> None:
    """UTF-8 encoded input is supported."""
    cap = CsvExtractionCapability()
    raw = "name\n日本語 🎉\nCafé".encode()
    result = cap.invoke(_ctx(raw, column="name"))
    assert [c.value for c in result.candidates] == ["日本語 🎉", "Café"]


def test_evidence_includes_header() -> None:
    """Evidence context records the full header for provenance."""
    cap = CsvExtractionCapability()
    raw = b"a,b,c\n1,2,3\n4,5,6\n"
    result = cap.invoke(_ctx(raw, column="b"))
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["header"] == ["a", "b", "c"]
    assert ev.context["row_index"] == 1


# --- failure modes --------------------------------------------------------


def test_missing_column_in_config() -> None:
    """Missing config['column'] returns an error diagnostic."""
    cap = CsvExtractionCapability()
    result = cap.invoke(_ctx(b"a,b\n1,2\n"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "column" in d.message


def test_column_wrong_type() -> None:
    """A column spec of an unsupported type returns an error diagnostic."""
    cap = CsvExtractionCapability()
    result = cap.invoke(_ctx(b"a,b\n1,2\n", column=1.5))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_column_is_bool_rejected() -> None:
    """bool is an int subclass; the capability rejects it explicitly."""
    cap = CsvExtractionCapability()
    result = cap.invoke(_ctx(b"a,b\n1,2\n", column=True))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_unknown_column_name() -> None:
    """A column name that is not in the header returns an error diagnostic."""
    cap = CsvExtractionCapability()
    raw = b"a,b\n1,2\n"
    result = cap.invoke(_ctx(raw, column="nonexistent"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "nonexistent" in d.message


def test_out_of_range_column_index() -> None:
    """A column index past the end of the header returns an error diagnostic."""
    cap = CsvExtractionCapability()
    raw = b"a,b\n1,2\n"
    result = cap.invoke(_ctx(raw, column=5))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "out of range" in d.message or "range" in d.message


def test_negative_column_index_rejected() -> None:
    """A negative column index returns an error diagnostic."""
    cap = CsvExtractionCapability()
    raw = b"a,b\n1,2\n"
    result = cap.invoke(_ctx(raw, column=-1))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_empty_input() -> None:
    """Empty raw_input returns an error diagnostic."""
    cap = CsvExtractionCapability()
    result = cap.invoke(_ctx(b"", column="a"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_empty_column_emits_pattern_no_match() -> None:
    """A column where every data row is empty emits a PATTERN_NO_MATCH diagnostic."""
    cap = CsvExtractionCapability()
    raw = b"name,amount\n,100\n,200\n"
    result = cap.invoke(_ctx(raw, column="name"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.PATTERN_NO_MATCH
    assert d.severity is DiagnosticSeverity.INFO


# --- determinism ----------------------------------------------------------


@pytest.mark.deterministic
def test_determinism() -> None:
    """Same input + same column = same candidates, byte-equal."""
    cap = CsvExtractionCapability()
    ctx = _ctx(b"a,b\n1,2\n3,4\n5,6\n", column="a")
    r1 = cap.invoke(ctx)
    r2 = cap.invoke(ctx)
    assert [c.value for c in r1.candidates] == [c.value for c in r2.candidates]
    assert [c.evidence_refs[0].context for c in r1.candidates] == [
        c.evidence_refs[0].context for c in r2.candidates
    ]

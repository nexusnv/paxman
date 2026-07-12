"""Tests for reconciler candidate preparation (typed parsing)."""

from __future__ import annotations

import datetime
import typing
from decimal import Decimal

import pytest

from paxman.capabilities.result import Candidate, Diagnostic, DiagnosticCode
from paxman.contract._parse import ParseSpec
from paxman.contract.canonical import CanonicalField
from paxman.reconciler.parsing import prepare_candidates
from paxman.types import FieldType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _field(
    name: str = "total",
    field_type: FieldType = FieldType.DECIMAL,
    parse_spec: ParseSpec | None = None,
) -> CanonicalField:
    """Build a minimal CanonicalField for testing."""
    from paxman.contract._extraction import ExtractionStep

    # Build a minimal extraction_step if parse_spec is present.
    extraction_step = None
    if parse_spec is not None:
        extraction_step = ExtractionStep(
            capability_id="regex_extraction",
            config={"pattern": r"\S+"},
        )
    return CanonicalField(
        id=f"field_{name}",
        path=name,
        name=name,
        type=field_type,
        required=True,
        parse_spec=parse_spec,
        extraction_step=extraction_step,
    )


# ---------------------------------------------------------------------------
# Happy-path tests: each kind for matching type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "parse_spec", "field_type", "expected"),
    [
        # INTEGER
        ("42", ParseSpec(kind="integer", config={}), FieldType.INTEGER, 42),
        ("-7", ParseSpec(kind="integer", config={}), FieldType.INTEGER, -7),
        ("0", ParseSpec(kind="integer", config={}), FieldType.INTEGER, 0),
        # DECIMAL
        ("12.50", ParseSpec(kind="decimal", config={}), FieldType.DECIMAL, Decimal("12.50")),
        ("0.01", ParseSpec(kind="decimal", config={}), FieldType.DECIMAL, Decimal("0.01")),
        ("-100", ParseSpec(kind="decimal", config={}), FieldType.DECIMAL, Decimal("-100")),
        # BOOLEAN
        (
            "yes",
            ParseSpec(kind="boolean", config={"true_values": ["yes"], "false_values": ["no"]}),
            FieldType.BOOLEAN,
            True,
        ),
        (
            "no",
            ParseSpec(kind="boolean", config={"true_values": ["yes"], "false_values": ["no"]}),
            FieldType.BOOLEAN,
            False,
        ),
        # DATE
        (
            "2026-07-12",
            ParseSpec(kind="date", config={"format": "%Y-%m-%d"}),
            FieldType.DATE,
            "2026-07-12",
        ),
    ],
    ids=["int-pos", "int-neg", "int-zero", "dec-pos", "dec-small", "dec-neg", "bool-true", "bool-false", "date-ymd"],
)
@pytest.mark.deterministic
@pytest.mark.unit
def test_prepare_candidate_returns_typed_candidate(
    value: str,
    parse_spec: ParseSpec,
    field_type: FieldType,
    expected: typing.Any,
) -> None:
    """Each parse kind converts the string value to the expected typed value."""
    field = _field(parse_spec=parse_spec, field_type=field_type)
    candidate = Candidate(value=value)
    prepared = prepare_candidates((candidate,), field)
    assert len(prepared) == 1
    assert prepared[0].value == expected


# ---------------------------------------------------------------------------
# Failure cases: invalid text for parse kind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "parse_spec", "field_type"),
    [
        ("twelve", ParseSpec(kind="integer", config={}), FieldType.INTEGER),
        ("abc", ParseSpec(kind="decimal", config={}), FieldType.DECIMAL),
        ("maybe", ParseSpec(kind="boolean", config={"true_values": ["yes"], "false_values": ["no"]}), FieldType.BOOLEAN),
        ("not-a-date", ParseSpec(kind="date", config={"format": "%Y-%m-%d"}), FieldType.DATE),
    ],
    ids=["bad-int", "bad-dec", "bad-bool", "bad-date"],
)
@pytest.mark.deterministic
@pytest.mark.unit
def test_prepare_candidate_invalid_text_yields_empty(
    value: str,
    parse_spec: ParseSpec,
    field_type: FieldType,
) -> None:
    """Invalid text for a parse kind yields zero prepared candidates + diagnostic."""
    field = _field(parse_spec=parse_spec, field_type=field_type)
    candidate = Candidate(value=value)
    prepared = prepare_candidates((candidate,), field)
    assert len(prepared) == 0


# ---------------------------------------------------------------------------
# Non-string value is passed through unchanged
# ---------------------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_prepare_candidate_non_string_passthrough() -> None:
    """Non-string values (already typed) pass through unchanged."""
    field = _field(parse_spec=ParseSpec(kind="decimal", config={}), field_type=FieldType.DECIMAL)
    candidate = Candidate(value=Decimal("12.50"))
    prepared = prepare_candidates((candidate,), field)
    assert len(prepared) == 1
    assert prepared[0].value == Decimal("12.50")


# ---------------------------------------------------------------------------
# No parse_spec: passthrough
# ---------------------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_prepare_candidate_no_parse_spec_passthrough() -> None:
    """Without a parse_spec, candidates pass through unchanged."""
    field = _field(parse_spec=None)
    candidate = Candidate(value="hello")
    prepared = prepare_candidates((candidate,), field)
    assert len(prepared) == 1
    assert prepared[0].value == "hello"


# ---------------------------------------------------------------------------
# Evidence preservation
# ---------------------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_prepare_candidate_preserves_evidence() -> None:
    """Evidence refs are preserved through parsing."""
    from paxman.capabilities.result import EvidenceRef

    field = _field(parse_spec=ParseSpec(kind="integer", config={}), field_type=FieldType.INTEGER)
    refs = (EvidenceRef(capability_id="regex_extraction", capability_version="1.0", field_path="total"),)
    candidate = Candidate(value="42", evidence_refs=refs)
    prepared = prepare_candidates((candidate,), field)
    assert len(prepared) == 1
    assert prepared[0].value == 42
    assert prepared[0].evidence_refs == refs


# ---------------------------------------------------------------------------
# Determinism property test
# ---------------------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
@pytest.mark.property
def test_prepare_candidates_determinism() -> None:
    """Same input/config produces byte-equal result."""
    field = _field(parse_spec=ParseSpec(kind="decimal", config={}), field_type=FieldType.DECIMAL)
    candidate = Candidate(value="12.50")
    r1 = prepare_candidates((candidate,), field)
    r2 = prepare_candidates((candidate,), field)
    assert len(r1) == len(r2) == 1
    assert r1[0].value == r2[0].value
    assert r1[0].evidence_refs == r2[0].evidence_refs

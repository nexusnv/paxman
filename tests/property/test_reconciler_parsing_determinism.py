"""Property tests for reconciler candidate preparation determinism."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from paxman.capabilities.result import Candidate
from paxman.contract._extraction import ExtractionStep
from paxman.contract._parse import ParseSpec
from paxman.contract.canonical import CanonicalField
from paxman.reconciler.parsing import prepare_candidates
from paxman.types import FieldType


@st.composite
def _parse_spec_strategy(draw: st.DrawFn) -> tuple[ParseSpec, FieldType]:
    """Strategy for generating (ParseSpec, FieldType) pairs."""
    kind = draw(st.sampled_from(["integer", "decimal", "boolean", "date"]))
    if kind == "integer":
        return ParseSpec(kind="integer", config={}), FieldType.INTEGER
    if kind == "decimal":
        return ParseSpec(kind="decimal", config={}), FieldType.DECIMAL
    if kind == "boolean":
        return ParseSpec(
            kind="boolean",
            config={"true_values": ["yes", "y", "true"], "false_values": ["no", "n", "false"]},
        ), FieldType.BOOLEAN
    # date
    return ParseSpec(kind="date", config={"format": "%Y-%m-%d"}), FieldType.DATE


@st.composite
def _candidate_strategy(draw: st.DrawFn) -> tuple[str, ParseSpec, FieldType]:
    """Strategy for generating (value, parse_spec, field_type) tuples."""
    spec, field_type = draw(_parse_spec_strategy())
    if spec.kind == "integer":
        value = draw(st.integers(min_value=-10000, max_value=10000).map(str))
    elif spec.kind == "decimal":
        value = draw(
            st.decimals(min_value=Decimal("-9999"), max_value=Decimal("9999"), places=2).map(str)
        )
    elif spec.kind == "boolean":
        value = draw(st.sampled_from(["yes", "no", "y", "n", "true", "false"]))
    else:
        value = draw(st.sampled_from(["2026-01-01", "2026-07-12", "2026-12-31"]))
    return value, spec, field_type


@given(data=_candidate_strategy())
@settings(max_examples=50, derandomize=True)
def test_prepare_candidates_deterministic(data: tuple[str, ParseSpec, FieldType]) -> None:
    """Same input/config produces byte-equal result."""
    value, spec, field_type = data
    field = CanonicalField(
        id="field_test",
        path="test",
        name="test",
        type=field_type,
        required=True,
        parse_spec=spec,
        extraction_step=ExtractionStep(
            capability_id="regex_extraction", config={"pattern": r"\S+"}
        ),
    )
    candidate = Candidate(value=value)
    r1 = prepare_candidates((candidate,), field)
    r2 = prepare_candidates((candidate,), field)
    assert len(r1) == len(r2)
    for a, b in zip(r1, r2, strict=True):
        assert a.value == b.value
        assert a.evidence_refs == b.evidence_refs

"""Unit tests for explicit contract extraction metadata."""

from __future__ import annotations

import pytest

from paxman.contract._extraction import ExtractionValidationError, parse_extraction
from paxman.contract.canonical import CanonicalField
from paxman.types import FieldType

pytestmark = pytest.mark.unit


def test_parse_extraction_accepts_regex_pattern() -> None:
    """A declared regex extractor retains its field-specific pattern."""
    step = parse_extraction(
        {
            "capability": "regex_extraction",
            "config": {"pattern": r"ID:\s*(?P<value>\S+)"},
        },
        field_name="invoice_id",
    )

    assert step is not None
    assert step.capability_id == "regex_extraction"
    assert step.config == {"pattern": r"ID:\s*(?P<value>\S+)"}


@pytest.mark.parametrize(
    "raw",
    [
        {"capability": "text_extraction", "config": {}},
        {"capability": "regex_extraction", "config": {}},
        {"capability": "regex_extraction", "config": {"pattern": ""}},
    ],
)
def test_parse_extraction_rejects_unsafe_or_incomplete_declarations(raw: object) -> None:
    """Only a regex extractor with a non-empty pattern is accepted."""
    with pytest.raises(ExtractionValidationError) as exc_info:
        parse_extraction(raw, field_name="invoice_id")

    assert exc_info.value.error_code == "INVALID_EXTRACTION"


def test_canonical_field_retains_extraction_step() -> None:
    """The extraction declaration is immutable canonical field state."""
    field = CanonicalField(
        id="field_invoice_id",
        path="invoice_id",
        name="invoice_id",
        type=FieldType.STRING,
        required=True,
        extraction_step=parse_extraction(
            {
                "capability": "regex_extraction",
                "config": {"pattern": r"ID:(?P<value>\S+)"},
            },
            field_name="invoice_id",
        ),
    )

    assert field.extraction_step is not None

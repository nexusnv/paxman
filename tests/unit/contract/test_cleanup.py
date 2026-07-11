"""Unit tests for explicit contract cleanup metadata."""

from __future__ import annotations

import pytest

from paxman.contract._cleanup import CleanupValidationError, parse_cleanup
from paxman.contract.canonical import CanonicalField
from paxman.types import FieldType

pytestmark = pytest.mark.unit


def test_parse_cleanup_preserves_declared_order_and_config() -> None:
    """Declared cleanup steps retain their order and capability configuration."""
    steps = parse_cleanup(
        [
            {"capability": "trim_extraction"},
            {"capability": "case_normalization", "config": {"mode": "lower"}},
        ],
        field_name="supplier",
    )

    assert [step.capability_id for step in steps] == ["trim_extraction", "case_normalization"]
    assert steps[1].config == {"mode": "lower"}


@pytest.mark.parametrize(
    "raw",
    [
        [{"capability": "unknown"}],
        [{"capability": "case_normalization"}],
        [{"capability": "trim_extraction", "config": []}],
    ],
)
def test_parse_cleanup_rejects_invalid_entries(raw: object) -> None:
    """Unsupported and incomplete cleanup declarations are invalid contracts."""
    with pytest.raises(CleanupValidationError) as exc_info:
        parse_cleanup(raw, field_name="supplier")

    assert exc_info.value.error_code == "INVALID_CLEANUP"


def test_canonical_field_retains_cleanup_steps() -> None:
    """Cleanup metadata is immutable canonical field state."""
    field = CanonicalField(
        id="field_supplier",
        path="supplier",
        name="supplier",
        type=FieldType.STRING,
        required=True,
        cleanup_steps=parse_cleanup(
            [{"capability": "trim_extraction"}],
            field_name="supplier",
        ),
    )

    assert field.cleanup_steps[0].capability_id == "trim_extraction"

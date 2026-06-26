"""Unit tests for ``paxman.artifact.statistics`` — CapabilityStats, Statistics."""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.artifact.statistics import CapabilityStats, Statistics
from paxman.types import Status

pytestmark = pytest.mark.unit


# ============================================================================
# CapabilityStats
# ============================================================================


def _minimal_cap_stats() -> CapabilityStats:
    """Build a minimal valid CapabilityStats."""
    return CapabilityStats(
        capability_id="regex_extraction",
        capability_version="1.0",
    )


@pytest.mark.deterministic
def test_cap_stats_minimal() -> None:
    """CapabilityStats with required fields is valid; defaults apply."""
    cs = _minimal_cap_stats()
    assert cs.capability_id == "regex_extraction"
    assert cs.capability_version == "1.0"
    assert cs.invocation_count == 0
    assert cs.total_duration_ms == 0.0
    assert cs.total_cost_usd == Decimal("0")
    assert cs.total_tokens == 0


@pytest.mark.deterministic
def test_cap_stats_frozen_and_slots() -> None:
    """CapabilityStats is frozen and uses slots."""
    cs = _minimal_cap_stats()
    with pytest.raises(AttributeError):
        cs.capability_id = "other"  # type: ignore[misc]
    assert not hasattr(cs, "__dict__")


@pytest.mark.deterministic
@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("capability_id", "", "capability_id must be a non-empty string"),
        ("capability_id", 123, "capability_id must be a non-empty string"),
        ("capability_version", "", "capability_version must be a non-empty string"),
        ("capability_version", None, "capability_version must be a non-empty string"),
    ],
)
def test_cap_stats_rejects_empty_required_strings(field: str, value: object, match: str) -> None:
    """Empty or non-string capability_id/capability_version raises ValueError."""
    kwargs = {"capability_id": "test", "capability_version": "1.0"}
    kwargs[field] = value
    with pytest.raises((ValueError, TypeError), match=match):
        CapabilityStats(**kwargs)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_cap_stats_rejects_negative_invocation_count() -> None:
    """Negative invocation_count raises ValueError."""
    with pytest.raises(ValueError, match="invocation_count must be a non-negative int"):
        CapabilityStats(
            capability_id="test",
            capability_version="1.0",
            invocation_count=-1,
        )


@pytest.mark.deterministic
def test_cap_stats_rejects_non_int_invocation_count() -> None:
    """Non-int invocation_count raises ValueError."""
    with pytest.raises(ValueError, match="invocation_count must be a non-negative int"):
        CapabilityStats(
            capability_id="test",
            capability_version="1.0",
            invocation_count=1.5,  # type: ignore[arg-type]
        )


@pytest.mark.deterministic
def test_cap_stats_rejects_negative_duration() -> None:
    """Negative total_duration_ms raises ValueError."""
    with pytest.raises(ValueError, match="total_duration_ms must be non-negative"):
        CapabilityStats(
            capability_id="test",
            capability_version="1.0",
            total_duration_ms=-0.1,
        )


@pytest.mark.deterministic
def test_cap_stats_rejects_bool_duration() -> None:
    """bool for total_duration_ms raises TypeError."""
    with pytest.raises(TypeError, match="total_duration_ms must be a number"):
        CapabilityStats(
            capability_id="test",
            capability_version="1.0",
            total_duration_ms=True,  # type: ignore[arg-type]
        )


@pytest.mark.deterministic
def test_cap_stats_accepts_all_fields() -> None:
    """CapabilityStats accepts all fields with valid values."""
    cs = CapabilityStats(
        capability_id="inference",
        capability_version="2.0",
        invocation_count=5,
        total_duration_ms=1234.56,
        total_cost_usd=Decimal("0.05"),
        total_tokens=1500,
    )
    assert cs.invocation_count == 5
    assert cs.total_duration_ms == 1234.56
    assert cs.total_cost_usd == Decimal("0.05")
    assert cs.total_tokens == 1500


# ============================================================================
# Statistics
# ============================================================================


@pytest.mark.deterministic
def test_statistics_minimal() -> None:
    """Statistics with defaults is valid."""
    stats = Statistics()
    assert stats.status is Status.UNRESOLVED
    assert stats.wall_clock_ms == 0.0
    assert stats.monotonic_ms == 0.0
    assert stats.total_cost_usd == Decimal("0")
    assert stats.total_fields == 0
    assert stats.resolved_fields == 0
    assert stats.unresolved_fields == 0
    assert stats.capability_stats == ()


@pytest.mark.deterministic
def test_statistics_frozen_and_slots() -> None:
    """Statistics is frozen and uses slots."""
    stats = Statistics()
    with pytest.raises(AttributeError):
        stats.status = Status.SUCCESS  # type: ignore[misc]
    assert not hasattr(stats, "__dict__")


@pytest.mark.deterministic
def test_statistics_rejects_non_status() -> None:
    """Non-Status value for status raises TypeError."""
    with pytest.raises(TypeError, match="status must be a Status enum"):
        Statistics(status="SUCCESS")  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.parametrize(
    ("attr_name", "value", "match"),
    [
        ("wall_clock_ms", -1.0, "wall_clock_ms must be non-negative"),
        ("wall_clock_ms", "fast", "wall_clock_ms must be a number"),
        ("wall_clock_ms", True, "wall_clock_ms must be a number"),
        ("monotonic_ms", -0.5, "monotonic_ms must be non-negative"),
        ("monotonic_ms", "slow", "monotonic_ms must be a number"),
        ("total_cost_usd", -0.01, "total_cost_usd must be a Decimal"),
        ("total_cost_usd", "free", "total_cost_usd must be a Decimal"),
    ],
)
def test_statistics_rejects_invalid_duration_or_cost(
    attr_name: str, value: object, match: str
) -> None:
    """Negative or non-numeric duration/cost fields raise TypeError or ValueError."""
    kwargs: dict[str, object] = {}
    kwargs[attr_name] = value
    with pytest.raises((TypeError, ValueError), match=match):
        Statistics(**kwargs)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.parametrize(
    ("attr_name", "value", "match"),
    [
        ("total_fields", -1, "total_fields must be a non-negative int"),
        ("total_fields", 1.5, "total_fields must be a non-negative int"),
        ("total_fields", "ten", "total_fields must be a non-negative int"),
        ("resolved_fields", -1, "resolved_fields must be a non-negative int"),
        ("unresolved_fields", -1, "unresolved_fields must be a non-negative int"),
    ],
)
def test_statistics_rejects_invalid_field_counts(attr_name: str, value: object, match: str) -> None:
    """Negative or non-int field count fields raise ValueError."""
    kwargs: dict[str, object] = {}
    kwargs[attr_name] = value
    with pytest.raises((ValueError, TypeError), match=match):
        Statistics(**kwargs)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_statistics_rejects_non_tuple_capability_stats() -> None:
    """capability_stats must be a tuple."""
    with pytest.raises(TypeError, match="capability_stats must be a tuple"):
        Statistics(capability_stats=[])  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_statistics_accepts_all_valid_fields() -> None:
    """Statistics with all valid fields is accepted."""
    cap_stat = CapabilityStats(
        capability_id="regex_extraction",
        capability_version="1.0",
        invocation_count=3,
    )
    stats = Statistics(
        status=Status.SUCCESS,
        wall_clock_ms=100.0,
        monotonic_ms=95.0,
        total_cost_usd=Decimal("0.03"),
        total_fields=10,
        resolved_fields=8,
        unresolved_fields=2,
        capability_stats=(cap_stat,),
    )
    assert stats.status is Status.SUCCESS
    assert stats.wall_clock_ms == 100.0
    assert stats.monotonic_ms == 95.0
    assert stats.total_cost_usd == Decimal("0.03")
    assert stats.total_fields == 10
    assert stats.resolved_fields == 8
    assert stats.unresolved_fields == 2
    assert stats.capability_stats == (cap_stat,)

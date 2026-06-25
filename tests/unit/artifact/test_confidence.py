"""Unit tests for ``paxman.artifact.confidence`` — band_from_float, float_from_band, bounds."""

from __future__ import annotations

import pytest

from paxman.artifact.confidence import (
    BAND_LOWER_BOUNDS,
    BAND_UPPER_BOUNDS,
    band_from_float,
    float_from_band,
)
from paxman.types import ConfidenceBand

pytestmark = pytest.mark.unit


# ============================================================================
# Constants
# ============================================================================


def test_band_lower_bounds_accessible() -> None:
    """BAND_LOWER_BOUNDS is a dict with all 5 bands."""
    assert len(BAND_LOWER_BOUNDS) == 5
    assert ConfidenceBand.CERTAIN in BAND_LOWER_BOUNDS
    assert BAND_LOWER_BOUNDS[ConfidenceBand.CERTAIN] == 0.95


def test_band_upper_bounds_accessible() -> None:
    """BAND_UPPER_BOUNDS is a dict with all 5 bands."""
    assert len(BAND_UPPER_BOUNDS) == 5
    assert ConfidenceBand.UNTRUSTED in BAND_UPPER_BOUNDS
    assert BAND_UPPER_BOUNDS[ConfidenceBand.UNTRUSTED] == 0.30


# ============================================================================
# band_from_float
# ============================================================================


@pytest.mark.deterministic
@pytest.mark.parametrize(
    ("score", "expected_band"),
    [
        (1.0, ConfidenceBand.CERTAIN),
        (0.95, ConfidenceBand.CERTAIN),
        (0.99, ConfidenceBand.CERTAIN),
        (0.94, ConfidenceBand.HIGH),
        (0.80, ConfidenceBand.HIGH),
        (0.79, ConfidenceBand.MEDIUM),
        (0.60, ConfidenceBand.MEDIUM),
        (0.59, ConfidenceBand.LOW),
        (0.30, ConfidenceBand.LOW),
        (0.29, ConfidenceBand.UNTRUSTED),
        (0.0, ConfidenceBand.UNTRUSTED),
        (0.5, ConfidenceBand.LOW),
        (0.9, ConfidenceBand.HIGH),
    ],
)
def test_band_from_float_boundaries(score: float, expected_band: ConfidenceBand) -> None:
    """band_from_float maps scores to the correct band at boundary values."""
    assert band_from_float(score) is expected_band


@pytest.mark.deterministic
@pytest.mark.parametrize(
    "score",
    [0, 1],
)
def test_band_from_float_accepts_int(score: int) -> None:
    """band_from_float accepts int values (0 and 1)."""
    if score == 0:
        assert band_from_float(score) is ConfidenceBand.UNTRUSTED
    else:
        assert band_from_float(score) is ConfidenceBand.CERTAIN


@pytest.mark.deterministic
@pytest.mark.parametrize(
    "non_number",
    [
        "0.5",
        None,
        [0.5],
        {"score": 0.5},
        object(),
    ],
)
def test_band_from_float_rejects_non_number(non_number: object) -> None:
    """Non-numeric types raise TypeError."""
    with pytest.raises(TypeError, match="score must be a number"):
        band_from_float(non_number)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_band_from_float_rejects_bool() -> None:
    """bool is explicitly rejected (subclass of int)."""
    with pytest.raises(TypeError, match="score must be a number"):
        band_from_float(True)  # type: ignore[arg-type]


@pytest.mark.deterministic
@pytest.mark.parametrize("out_of_range", [-0.1, 1.1, 2.0, -1.0])
def test_band_from_float_rejects_out_of_range(out_of_range: float) -> None:
    """Values outside [0.0, 1.0] raise ValueError."""
    with pytest.raises(ValueError, match=r"score must be in \[0.0, 1.0\]"):
        band_from_float(out_of_range)


# ============================================================================
# float_from_band
# ============================================================================


@pytest.mark.deterministic
@pytest.mark.parametrize(
    ("band", "expected_midpoint"),
    [
        (ConfidenceBand.CERTAIN, 0.975),
        (ConfidenceBand.HIGH, 0.875),
        (ConfidenceBand.MEDIUM, 0.70),
        (ConfidenceBand.LOW, 0.45),
        (ConfidenceBand.UNTRUSTED, 0.15),
    ],
)
def test_float_from_band_midpoints(band: ConfidenceBand, expected_midpoint: float) -> None:
    """float_from_band returns the midpoint of each band's range."""
    assert float_from_band(band) == pytest.approx(expected_midpoint)


@pytest.mark.deterministic
@pytest.mark.parametrize(
    "non_band",
    [
        "CERTAIN",
        "HIGH",
        None,
        0.95,
        1,
        object(),
    ],
)
def test_float_from_band_rejects_non_band(non_band: object) -> None:
    """Non-ConfidenceBand raises TypeError."""
    with pytest.raises(TypeError, match="band must be a ConfidenceBand"):
        float_from_band(non_band)  # type: ignore[arg-type]

"""Confidence band mapping — float ↔ :class:`ConfidenceBand` conversion.

Per ADR-0005 (Confidence Ownership), the Reconciler is the sole authority
for assigning confidence. This module provides the mapping from raw float
scores to the fixed five discrete bands:

    - ``CERTAIN``:    [0.95, 1.00]
    - ``HIGH``:       [0.80, 0.95)
    - ``MEDIUM``:     [0.60, 0.80)
    - ``LOW``:        [0.30, 0.60)
    - ``UNTRUSTED``:  [0.00, 0.30)
"""

from __future__ import annotations

import typing

from paxman.types import ConfidenceBand

__all__ = [
    "BAND_LOWER_BOUNDS",
    "BAND_UPPER_BOUNDS",
    "band_from_float",
    "float_from_band",
]

#: Lower bound (inclusive) for each confidence band.
BAND_LOWER_BOUNDS: typing.Final[dict[ConfidenceBand, float]] = {
    ConfidenceBand.CERTAIN: 0.95,
    ConfidenceBand.HIGH: 0.80,
    ConfidenceBand.MEDIUM: 0.60,
    ConfidenceBand.LOW: 0.30,
    ConfidenceBand.UNTRUSTED: 0.00,
}

#: Upper bound (exclusive except CERTAIN which is inclusive).
BAND_UPPER_BOUNDS: typing.Final[dict[ConfidenceBand, float]] = {
    ConfidenceBand.CERTAIN: 1.00,
    ConfidenceBand.HIGH: 0.80,
    ConfidenceBand.MEDIUM: 0.60,
    ConfidenceBand.LOW: 0.30,
    ConfidenceBand.UNTRUSTED: 0.30,
}


def band_from_float(score: float) -> ConfidenceBand:
    """Map a float confidence score to its corresponding :class:`ConfidenceBand`.

    The mapping follows the band definitions in ADR-0005:

    - ``score >= 0.95`` → ``CERTAIN``
    - ``score >= 0.80`` → ``HIGH``
    - ``score >= 0.60`` → ``MEDIUM``
    - ``score >= 0.30`` → ``LOW``
    - otherwise → ``UNTRUSTED``

    Args:
        score: A float confidence score in ``[0.0, 1.0]``.

    Returns:
        The corresponding :class:`ConfidenceBand`.

    Raises:
        ValueError: If *score* is outside ``[0.0, 1.0]``.

    Examples:
        >>> band_from_float(0.95)
        <ConfidenceBand.CERTAIN: 'CERTAIN'>
        >>> band_from_float(0.50)
        <ConfidenceBand.LOW: 'LOW'>
    """
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise TypeError(f"score must be a number, got {type(score).__name__}")
    if score < 0.0 or score > 1.0:
        raise ValueError(f"score must be in [0.0, 1.0], got {score}")
    if score >= BAND_LOWER_BOUNDS[ConfidenceBand.CERTAIN]:
        return ConfidenceBand.CERTAIN
    if score >= BAND_LOWER_BOUNDS[ConfidenceBand.HIGH]:
        return ConfidenceBand.HIGH
    if score >= BAND_LOWER_BOUNDS[ConfidenceBand.MEDIUM]:
        return ConfidenceBand.MEDIUM
    if score >= BAND_LOWER_BOUNDS[ConfidenceBand.LOW]:
        return ConfidenceBand.LOW
    return ConfidenceBand.UNTRUSTED


def float_from_band(band: ConfidenceBand) -> float:
    """Return the midpoint of the *band*'s numeric range.

    Args:
        band: The :class:`ConfidenceBand` to convert.

    Returns:
        The midpoint float value of the band's range.

    Examples:
        >>> float_from_band(ConfidenceBand.HIGH)
        0.875
        >>> float_from_band(ConfidenceBand.UNTRUSTED)
        0.15
    """
    if not isinstance(band, ConfidenceBand):
        raise TypeError(f"band must be a ConfidenceBand, got {type(band).__name__}")
    lo = BAND_LOWER_BOUNDS[band]
    hi = BAND_UPPER_BOUNDS[band]
    if band == ConfidenceBand.CERTAIN:
        # CERTAIN is [0.95, 1.00], both inclusive
        return (lo + hi) / 2.0
    # Other bands: [lo, hi) — midpoint is still meaningful
    return (lo + hi) / 2.0

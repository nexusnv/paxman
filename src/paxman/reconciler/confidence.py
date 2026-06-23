"""Confidence assignment and band mapping for the Reconciler.

The Reconciler is the **sole** confidence authority (`ADR-0005`). This
module is the only place in Paxman that constructs
:class:`~paxman.types.ConfidenceBand` values on the resolved-output
side and assigns float confidence scores.

Confidence calibration rubric
----------------------------

The :func:`assign_confidence` function is a deterministic, documented
mapping from evidence characteristics to a float in ``[0.0, 1.0]``. The
rubric is fixed in V1 (changing it requires an ADR):

- **Base:** ``0.50`` (start at MEDIUM)
- **+0.10** per additional agreeing candidate (cap at 3 → +0.20)
- **+0.05** per evidence ref (cap at 5 → +0.25)
- **+0.10** if validation passed
- **-0.15** if conflict was detected
- **+0.05** per unique capability source (cap at 3 → +0.15)
- **Final clamp to [0.0, 1.0]**

This produces a globally comparable score: the same evidence
characteristics always produce the same float, and therefore the same
ConfidenceBand. The same input always produces the same output
(determinism invariant per ``REPLAY_AND_DETERMINISM.md``).

Band mapping (per `ADR-0005` lines 74-81):

- :attr:`ConfidenceBand.CERTAIN`:   ``[0.95, 1.00]``
- :attr:`ConfidenceBand.HIGH`:      ``[0.80, 0.95)``
- :attr:`ConfidenceBand.MEDIUM`:    ``[0.60, 0.80)``
- :attr:`ConfidenceBand.LOW`:       ``[0.30, 0.60)``
- :attr:`ConfidenceBand.UNTRUSTED`: ``[0.00, 0.30)``

The bands are half-open: the lower bound is inclusive, the upper bound
is exclusive (except CERTAIN, which includes 1.0). This matches the
``types.py`` docstring.
"""

from __future__ import annotations

import typing

from paxman.types import ConfidenceBand

__all__ = ["assign_confidence", "float_to_band"]


def float_to_band(confidence: float) -> ConfidenceBand:
    """Map a confidence float to a :class:`ConfidenceBand`.

    Fixed intervals (per `ADR-0005` and ``types.py``):

    - :attr:`ConfidenceBand.CERTAIN`:   ``[0.95, 1.00]``
    - :attr:`ConfidenceBand.HIGH`:      ``[0.80, 0.95)``
    - :attr:`ConfidenceBand.MEDIUM`:    ``[0.60, 0.80)``
    - :attr:`ConfidenceBand.LOW`:       ``[0.30, 0.60)``
    - :attr:`ConfidenceBand.UNTRUSTED`: ``[0.00, 0.30)``

    Args:
        confidence: Float in ``[0.0, 1.0]``.

    Returns:
        The :class:`ConfidenceBand`.

    Raises:
        TypeError: If ``confidence`` is not a real number (bool rejected).
        ValueError: If ``confidence`` is outside ``[0.0, 1.0]``.

    Examples:
        >>> float_to_band(1.0)
        <ConfidenceBand.CERTAIN: 'CERTAIN'>
        >>> float_to_band(0.50)
        <ConfidenceBand.LOW: 'LOW'>
        >>> float_to_band(0.0)
        <ConfidenceBand.UNTRUSTED: 'UNTRUSTED'>
    """
    # Reject bool explicitly (bool is a subclass of int in Python).
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise TypeError(
            f"confidence must be a number, got {type(confidence).__name__}: {confidence!r}"
        )
    value = float(confidence)
    if value < 0.0 or value > 1.0:
        raise ValueError(f"confidence must be in [0.0, 1.0], got {value}")
    if value >= 0.95:
        return ConfidenceBand.CERTAIN
    if value >= 0.80:
        return ConfidenceBand.HIGH
    if value >= 0.60:
        return ConfidenceBand.MEDIUM
    if value >= 0.30:
        return ConfidenceBand.LOW
    return ConfidenceBand.UNTRUSTED


def assign_confidence(
    *,
    candidate_count: int,
    evidence_count: int,
    capability_ids: typing.Iterable[str],
    has_validation_pass: bool,
    has_conflict: bool,
    base_confidence: float = 0.50,
) -> float:
    """Assign a confidence float based on evidence characteristics.

    This is a deterministic pure function. The same inputs always
    produce the same output. The Reconciler is the sole confidence
    authority (`ADR-0005`); this is the single function that produces
    the float on the resolved-output side.

    The scoring rubric is fixed in V1 (see module docstring):

    - Base: ``0.50``
    - +0.10 per additional agreeing candidate (cap at 3 → +0.20)
    - +0.05 per evidence ref (cap at 5 → +0.25)
    - +0.10 if validation passed
    - -0.15 if conflict detected
    - +0.05 per unique capability source (cap at 3 → +0.15)
    - Clamp to ``[0.0, 1.0]``

    Args:
        candidate_count: Number of agreeing candidates for this field
            (non-negative int).
        evidence_count: Total evidence refs across all candidates
            (non-negative int).
        capability_ids: Iterable of capability IDs that produced
            candidates. Duplicates are counted once via a set.
        has_validation_pass: ``True`` if the
            :class:`~paxman.capabilities.v1.validation.ValidationCapability`
            passed for the chosen value.
        has_conflict: ``True`` if conflict was detected between
            candidates.
        base_confidence: Starting confidence. Defaults to ``0.50``.

    Returns:
        Float in ``[0.0, 1.0]``.

    Raises:
        TypeError: If any argument has the wrong type.
        ValueError: If a numeric argument is negative.

    Examples:
        >>> assign_confidence(
        ...     candidate_count=2,
        ...     evidence_count=3,
        ...     capability_ids=("regex_extraction", "validation"),
        ...     has_validation_pass=True,
        ...     has_conflict=False,
        ... )
        1.0
    """
    # --- type checks ---
    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int):
        raise TypeError(f"candidate_count must be an int, got {type(candidate_count).__name__}")
    if isinstance(evidence_count, bool) or not isinstance(evidence_count, int):
        raise TypeError(f"evidence_count must be an int, got {type(evidence_count).__name__}")
    if not isinstance(has_validation_pass, bool):
        raise TypeError(
            f"has_validation_pass must be a bool, got {type(has_validation_pass).__name__}"
        )
    if not isinstance(has_conflict, bool):
        raise TypeError(f"has_conflict must be a bool, got {type(has_conflict).__name__}")
    if isinstance(base_confidence, bool) or not isinstance(base_confidence, (int, float)):
        raise TypeError(f"base_confidence must be a number, got {type(base_confidence).__name__}")
    if not isinstance(capability_ids, typing.Iterable):
        raise TypeError(f"capability_ids must be iterable, got {type(capability_ids).__name__}")
    for cid in capability_ids:
        if not isinstance(cid, str):
            raise TypeError(
                f"capability_ids entries must be str, got {type(cid).__name__}: {cid!r}"
            )

    # --- value checks ---
    if candidate_count < 0:
        raise ValueError(f"candidate_count must be non-negative, got {candidate_count}")
    if evidence_count < 0:
        raise ValueError(f"evidence_count must be non-negative, got {evidence_count}")

    # --- scoring rubric ---
    confidence = float(base_confidence)
    # +0.10 per additional agreeing candidate (cap at 3 → +0.20)
    confidence += 0.10 * min(candidate_count, 3)
    # +0.05 per evidence ref (cap at 5 → +0.25)
    confidence += 0.05 * min(evidence_count, 5)
    # +0.10 if validation passed
    if has_validation_pass:
        confidence += 0.10
    # -0.15 if conflict detected
    if has_conflict:
        confidence -= 0.15
    # +0.05 per unique capability source (cap at 3 → +0.15)
    unique_caps = set(capability_ids)
    confidence += 0.05 * min(len(unique_caps), 3)
    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, confidence))

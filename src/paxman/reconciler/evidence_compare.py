"""Evidence quality comparison for candidate merging.

The :func:`compare_evidence_quality` function is a deterministic,
documented ordering used by the Reconciler's ``PREFER_BY_EVIDENCE``
merge strategy (in :mod:`paxman.reconciler.merge`). The same evidence
sets always produce the same comparison result.

Quality heuristic
-----------------

The comparison is based on the following ordered criteria (earlier
criteria dominate later ones):

1. **More evidence refs > fewer refs.** A candidate with 3 evidence
   refs beats a candidate with 1 evidence ref, all else equal.
2. **Evidence with span > evidence without span.** A ref with a
   specific byte-offset span into the raw input is stronger
   provenance than an "I extracted this from somewhere" ref.
3. **Deterministic capability > non-deterministic capability.**
   Refs from :class:`~paxman.capabilities.spec.CapabilityTier.LOCAL_DETERMINISTIC`
   and :class:`~paxman.capabilities.spec.CapabilityTier.STRUCTURED_LOOKUP`
   outrank refs from
   :class:`~paxman.capabilities.spec.CapabilityTier.LOCAL_INFERENCE`
   and :class:`~paxman.capabilities.spec.CapabilityTier.REMOTE_INFERENCE`.
4. **Capability tier rank** (lower tier rank = better).
5. **Capability id lexicographic** — final deterministic tiebreak.

The :class:`~paxman.capabilities.spec.CapabilityTier` enum is the
source of truth for tier semantics; this module only reads it.
"""

from __future__ import annotations

import typing

from paxman.capabilities.registry import all_capabilities
from paxman.capabilities.result import Candidate, EvidenceRef
from paxman.capabilities.spec import CapabilityTier

__all__ = [
    "best_candidate_by_evidence",
    "compare_evidence_quality",
    "evidence_has_span",
]


#: Tiers considered "deterministic" (V1: tier 1 + 2).
_DETERMINISTIC_TIER_VALUES: typing.Final[frozenset[int]] = frozenset(
    {int(CapabilityTier.LOCAL_DETERMINISTIC.value), int(CapabilityTier.STRUCTURED_LOOKUP.value)}
)

#: Sentinel tier rank for unknown capabilities (ranked after all known tiers).
_UNKNOWN_TIER_RANK: typing.Final[int] = 10


def _tier_rank(ref: EvidenceRef) -> int:
    """Return the tier rank of the capability that produced *ref*.

    Lower rank = better. Unknown capability ids return a large
    sentinel (10) so they are ranked after all known tiers.

    Args:
        ref: An :class:`EvidenceRef` whose capability is looked up
            in the global :func:`~paxman.capabilities.registry.all_capabilities`.

    Returns:
        The integer tier rank.
    """
    caps = all_capabilities()
    cap = caps.get((ref.capability_id, ref.capability_version))
    if cap is None:
        return _UNKNOWN_TIER_RANK
    spec = getattr(cap, "spec", None)
    if spec is None:
        return _UNKNOWN_TIER_RANK
    return int(spec.tier.value)


def _is_deterministic(ref: EvidenceRef) -> bool:
    """Return True if *ref* came from a deterministic capability tier."""
    return _tier_rank(ref) in _DETERMINISTIC_TIER_VALUES


def evidence_has_span(refs: tuple[EvidenceRef, ...]) -> bool:
    """Return True if any evidence ref has a span (specific provenance).

    Args:
        refs: Tuple of :class:`EvidenceRef` to inspect.

    Returns:
        ``True`` if at least one ref has a non-None span. ``False`` otherwise.

    Raises:
        TypeError: If ``refs`` is not a tuple.
    """
    if not isinstance(refs, tuple):
        raise TypeError(f"refs must be a tuple, got {type(refs).__name__}")
    return any(r.span is not None for r in refs if isinstance(r, EvidenceRef))


def compare_evidence_quality(
    a_refs: tuple[EvidenceRef, ...],
    b_refs: tuple[EvidenceRef, ...],
) -> int:
    """Compare evidence quality between two candidate evidence sets.

    Quality heuristic (deterministic, documented in module docstring):

    1. More evidence refs > fewer refs.
    2. If equal count: prefer refs with span > no span.
    3. If still equal: prefer refs from deterministic capabilities.
    4. If still equal: prefer lower tier rank.
    5. Final tiebreak: lexicographic sort on capability_id.

    Args:
        a_refs: Evidence refs from candidate A.
        b_refs: Evidence refs from candidate B.

    Returns:
        ``-1`` if A is better, ``0`` if equal, ``1`` if B is better.

    Raises:
        TypeError: If either input is not a tuple.

    Examples:
        >>> a = (EvidenceRef(
        ...     capability_id="regex_extraction",
        ...     capability_version="1.0",
        ...     field_path="x",
        ... ),)
        >>> b = (EvidenceRef(
        ...     capability_id="regex_extraction",
        ...     capability_version="1.0",
        ...     field_path="x",
        ...     span=(0, 5),
        ... ),)
        >>> compare_evidence_quality(a, b)
        1
    """
    if not isinstance(a_refs, tuple):
        raise TypeError(f"a_refs must be a tuple, got {type(a_refs).__name__}")
    if not isinstance(b_refs, tuple):
        raise TypeError(f"b_refs must be a tuple, got {type(b_refs).__name__}")

    # Criterion 1: more refs is better.
    a_count = len(a_refs)
    b_count = len(b_refs)
    if a_count != b_count:
        return -1 if a_count > b_count else 1
    if a_count == 0:
        return 0

    # Criterion 2: span beats no span.
    a_has_span = evidence_has_span(a_refs)
    b_has_span = evidence_has_span(b_refs)
    if a_has_span != b_has_span:
        return -1 if a_has_span else 1

    # Criterion 3: deterministic beats non-deterministic.
    a_det = any(_is_deterministic(r) for r in a_refs if isinstance(r, EvidenceRef))
    b_det = any(_is_deterministic(r) for r in b_refs if isinstance(r, EvidenceRef))
    if a_det != b_det:
        return -1 if a_det else 1

    # Criterion 4: lower tier rank is better.
    a_tiers = [_tier_rank(r) for r in a_refs if isinstance(r, EvidenceRef)]
    b_tiers = [_tier_rank(r) for r in b_refs if isinstance(r, EvidenceRef)]
    a_min_tier = min(a_tiers, default=_UNKNOWN_TIER_RANK)
    b_min_tier = min(b_tiers, default=_UNKNOWN_TIER_RANK)
    if a_min_tier != b_min_tier:
        return -1 if a_min_tier < b_min_tier else 1

    # Criterion 5: lexicographic tiebreak on capability_id.
    a_ids = sorted(r.capability_id for r in a_refs if isinstance(r, EvidenceRef))
    b_ids = sorted(r.capability_id for r in b_refs if isinstance(r, EvidenceRef))
    if a_ids < b_ids:
        return -1
    if a_ids > b_ids:
        return 1
    return 0


def best_candidate_by_evidence(
    candidates: tuple[Candidate, ...],
) -> Candidate | None:
    """Return the candidate with the best evidence quality, or None if empty.

    The comparison is performed pairwise in iteration order; ties
    resolve to the first candidate (deterministic).

    Args:
        candidates: Tuple of :class:`Candidate` to rank.

    Returns:
        The :class:`Candidate` with the best evidence quality, or
        ``None`` if the input is empty.

    Raises:
        TypeError: If any element is not a :class:`Candidate`.
    """
    if not candidates:
        return None
    for c in candidates:
        if not isinstance(c, Candidate):
            raise TypeError(f"all candidates must be Candidate, got {type(c).__name__}")
    best = candidates[0]
    for cand in candidates[1:]:
        cmp = compare_evidence_quality(best.evidence_refs, cand.evidence_refs)
        if cmp < 0:
            # best is still better
            continue
        if cmp > 0:
            # cand is better
            best = cand
        # cmp == 0: keep the first (deterministic tiebreak)
    return best

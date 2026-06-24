"""Candidate merging strategies for the Reconciler.

The :func:`merge_candidates` function combines a field's candidate
set into a single ``(value, evidence, strategy_name)`` triple, using
one of three strategies.

Strategies
----------

- :attr:`MergeStrategy.UNION`: if all candidates agree on the value,
  take the value and union all evidence refs. If they disagree,
  fall back to ``PREFER_BY_EVIDENCE``.
- :attr:`MergeStrategy.INTERSECTION`: only keep values that appear
  in at least 2 candidates. If no value satisfies that, fall back to
  ``PREFER_BY_EVIDENCE``.
- :attr:`MergeStrategy.PREFER_BY_EVIDENCE` (default): pick the
  candidate with the best evidence quality (per
  :func:`paxman.reconciler.evidence_compare.compare_evidence_quality`).

For MONEY fields, the merge delegates to
:func:`paxman.reconciler.money.resolve_money_candidates` for
cross-currency handling.

The function is deterministic: same candidates + same strategy
+ same field → same result. The returned ``strategy_name`` records
which strategy was used (so the artifact can replay the decision).
"""

from __future__ import annotations

import enum
import typing

from paxman.budget import CurrencyPolicy
from paxman.capabilities.result import Candidate, EvidenceRef
from paxman.contract.canonical import CanonicalField, MoneyValue
from paxman.reconciler.evidence_compare import best_candidate_by_evidence
from paxman.reconciler.money import resolve_money_candidates
from paxman.types import FieldType

__all__ = ["MergeStrategy", "merge_candidates"]


@enum.unique
class MergeStrategy(enum.Enum):
    """The V1 set of candidate merging strategies.

    - :attr:`UNION`: take the agreed value + unioned evidence (or
      fall back to PREFER_BY_EVIDENCE on disagreement).
    - :attr:`INTERSECTION`: only values appearing in >= 2 candidates
      (or fall back to PREFER_BY_EVIDENCE).
    - :attr:`PREFER_BY_EVIDENCE`: pick the candidate with the best
      evidence quality. **Default in V1** (per the sprint spec).
    """

    UNION = "UNION"
    INTERSECTION = "INTERSECTION"
    PREFER_BY_EVIDENCE = "PREFER_BY_EVIDENCE"


def _values_equal(a: object, b: object) -> bool:
    """Return True if two candidate values should be considered equal.

    For MoneyValue, compares amount and currency.
    """
    if isinstance(a, MoneyValue) and isinstance(b, MoneyValue):
        return a.amount == b.amount and a.currency == b.currency
    try:
        return bool(a == b)
    except Exception:
        return False


def _union_evidence(refs: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
    """Union a sequence of evidence-ref tuples, preserving first-seen order.

    Duplicates (by (capability_id, capability_version, field_path, span))
    are dropped.
    """
    seen: set[tuple[typing.Any, ...]] = set()
    out: list[EvidenceRef] = []
    for r in refs:
        if not isinstance(r, EvidenceRef):
            continue
        key = (r.capability_id, r.capability_version, r.field_path, r.span)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return tuple(out)


def _all_agree(candidates: tuple[Candidate, ...]) -> bool:
    """Return True if all candidates agree on value (non-None values only)."""
    concrete = [c for c in candidates if isinstance(c, Candidate) and c.value is not None]
    if len(concrete) < 2:
        return True
    first = concrete[0].value
    return all(_values_equal(first, c.value) for c in concrete[1:])


def _most_common_value(
    candidates: tuple[Candidate, ...],
) -> tuple[typing.Any, int] | None:
    """Return the value that appears in the most candidates, and its count.

    Returns ``None`` if all candidates have ``None`` values. Ties
    resolve to the value of the earliest candidate (deterministic).
    """
    values: list[typing.Any] = []
    for c in candidates:
        if not isinstance(c, Candidate) or c.value is None:
            continue
        values.append(c.value)
    if not values:
        return None
    # Count by value equality (not identity) so equal-but-distinct objects
    # from different capabilities are grouped together.
    counts: list[tuple[typing.Any, int]] = []
    for v in values:
        found = False
        for i, (existing_val, n) in enumerate(counts):
            if _values_equal(existing_val, v):
                counts[i] = (existing_val, n + 1)
                found = True
                break
        if not found:
            counts.append((v, 1))
    # Pick the value with the highest count; ties resolve to earliest.
    best: tuple[typing.Any, int] = counts[0]
    for item in counts[1:]:
        if item[1] > best[1]:
            best = item
    return best


def _do_money_merge(
    candidates: tuple[Candidate, ...],
    *,
    policy: CurrencyPolicy,
) -> tuple[MoneyValue, tuple[EvidenceRef, ...], str] | None:
    """Try to merge MONEY candidates via the money module.

    Returns ``(merged_money, evidence, strategy_name)`` or ``None`` if
    the money module rejected the merge (e.g., cross-currency under
    STRICT_MATCH). The caller falls back to PREFER_BY_EVIDENCE in
    that case.
    """
    money_values: list[MoneyValue] = []
    for c in candidates:
        if not isinstance(c, Candidate):
            continue
        if isinstance(c.value, MoneyValue):
            money_values.append(c.value)
    if not money_values:
        return None
    merged = resolve_money_candidates(tuple(money_values), policy=policy)
    if merged is None:
        return None
    # Union evidence from the candidates whose values are MoneyValue.
    refs: list[EvidenceRef] = []
    for c in candidates:
        if isinstance(c, Candidate) and isinstance(c.value, MoneyValue):
            refs.extend(c.evidence_refs)
    return merged, _union_evidence(tuple(refs)), "MONEY_RESOLVE"


def merge_candidates(
    candidates: tuple[Candidate, ...],
    *,
    field: CanonicalField,
    strategy: MergeStrategy = MergeStrategy.PREFER_BY_EVIDENCE,
    currency_policy: CurrencyPolicy = CurrencyPolicy.STRICT_MATCH,
) -> tuple[typing.Any, tuple[EvidenceRef, ...], str]:
    """Merge candidates for one field using the specified strategy.

    For MONEY fields: delegates to the money module first; if the
    money module rejects the merge (e.g., cross-currency under
    STRICT_MATCH), falls back to the requested strategy on the raw
    candidates.

    Args:
        candidates: Tuple of :class:`Candidate` for this field.
        field: The :class:`CanonicalField` being resolved.
        strategy: The :class:`MergeStrategy` to apply. Defaults to
            ``PREFER_BY_EVIDENCE``.
        currency_policy: The :class:`~paxman.budget.CurrencyPolicy`
            to use for MONEY merges. Defaults to ``STRICT_MATCH``.

    Returns:
        A ``(value, evidence_refs, strategy_name)`` triple:

        - ``value``: the merged value (any type), or ``None`` if no
          candidates / no mergeable set.
        - ``evidence_refs``: the unioned (or selected) evidence refs.
        - ``strategy_name``: the name of the strategy actually used
          (one of ``"UNION"``, ``"INTERSECTION"``,
          ``"PREFER_BY_EVIDENCE"``, ``"MONEY_RESOLVE"``,
          ``"NO_CANDIDATES"``).

    Raises:
        TypeError: If inputs are of the wrong type.
        ValueError: If ``candidates`` is empty (caller should use
            :func:`paxman.reconciler.unresolved.apply_fallback` for
            the empty case; this function rejects the call).

    Examples:
        >>> from paxman.capabilities.result import Candidate
        >>> from paxman.contract.canonical import CanonicalField
        >>> from paxman.types import FieldType
        >>> field = CanonicalField(
        ...     id="f1", path="x", name="x", type=FieldType.STRING, required=True
        ... )
        >>> cands = (Candidate(value="ACME"), Candidate(value="ACME"))
        >>> value, ev, strat = merge_candidates(cands, field=field)
        >>> value
        'ACME'
    """
    if not isinstance(candidates, tuple):
        raise TypeError(f"candidates must be a tuple, got {type(candidates).__name__}")
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")
    if not isinstance(strategy, MergeStrategy):
        raise TypeError(f"strategy must be a MergeStrategy, got {type(strategy).__name__}")
    if not isinstance(currency_policy, CurrencyPolicy):
        raise TypeError(
            f"currency_policy must be a CurrencyPolicy, got {type(currency_policy).__name__}"
        )

    if not candidates:
        raise ValueError("merge_candidates requires at least one candidate")

    # Filter to Candidates only (defensive; tuple of Candidate is the contract).
    valid: list[Candidate] = [c for c in candidates if isinstance(c, Candidate)]
    if not valid:
        return None, (), "NO_CANDIDATES"

    # MONEY fast path: delegate to the money module.
    if field.type is FieldType.MONEY:
        result = _do_money_merge(tuple(valid), policy=currency_policy)
        if result is not None:
            return result

    # Strategy dispatch.
    if strategy is MergeStrategy.UNION:
        if _all_agree(tuple(valid)):
            # Use the first concrete value; union all evidence.
            first = next(
                (c for c in valid if c.value is not None),
                valid[0],
            )
            all_refs: list[EvidenceRef] = []
            for c in valid:
                all_refs.extend(c.evidence_refs)
            return first.value, _union_evidence(tuple(all_refs)), "UNION"
        # Fall back to PREFER_BY_EVIDENCE on disagreement.
        best = best_candidate_by_evidence(tuple(valid))
        if best is None:
            return None, (), "PREFER_BY_EVIDENCE"
        return best.value, best.evidence_refs, "PREFER_BY_EVIDENCE"

    if strategy is MergeStrategy.INTERSECTION:
        # Pick the value appearing in the most candidates (must be >= 2).
        common = _most_common_value(tuple(valid))
        if common is not None and common[1] >= 2:
            value, _n = common
            # Union evidence of the candidates that share this value.
            shared: list[EvidenceRef] = []
            for c in valid:
                if c.value is not None and _values_equal(c.value, value):
                    shared.extend(c.evidence_refs)
            return value, _union_evidence(tuple(shared)), "INTERSECTION"
        # Fall back to PREFER_BY_EVIDENCE.
        best = best_candidate_by_evidence(tuple(valid))
        if best is None:
            return None, (), "PREFER_BY_EVIDENCE"
        return best.value, best.evidence_refs, "PREFER_BY_EVIDENCE"

    # Default: PREFER_BY_EVIDENCE.
    best = best_candidate_by_evidence(tuple(valid))
    if best is None:
        return None, (), "PREFER_BY_EVIDENCE"
    return best.value, best.evidence_refs, "PREFER_BY_EVIDENCE"

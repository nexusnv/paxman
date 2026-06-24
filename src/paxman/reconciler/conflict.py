"""Conflict detection between candidates for the same field.

A *conflict* is when two or more candidates for the same field propose
**different values**. For MONEY fields, a conflict is specifically
about **currencies** (not amounts) — the Reconciler can sum same-currency
candidates but cannot combine different currencies under
``STRICT_MATCH`` (per `ADR-0004` and the
:mod:`~paxman.reconciler.money` policy semantics).

The :class:`ConflictInfo` data class is the Reconciler's structured
record of a detected conflict. The Reconciler (in
:mod:`paxman.reconciler.reconciler`) attaches a ``ConflictInfo`` (or
``None``) to the per-field :class:`~paxman.reconciler.truth.ResolvedResult`
to drive the ``conflict_detected`` flag and the
``-0.15`` confidence penalty in :func:`~paxman.reconciler.confidence.assign_confidence`.

Conflict semantics
------------------

- **Single candidate:** no conflict.
- **All candidates agree on value:** no conflict.
- **Candidates disagree on value (non-MONEY):** value-mismatch
  conflict.
- **MONEY candidates with different currencies:** currency-mismatch
  conflict.
- **MONEY candidates with same currency but different amounts:** NOT
  a conflict at the detection layer — amount disagreement is handled
  by the merge strategy (e.g., PREFER_BY_EVIDENCE picks one).
- **``None`` values:** ignored in conflict detection.
"""

from __future__ import annotations

import typing

import attrs

from paxman.capabilities.result import Candidate
from paxman.contract.canonical import CanonicalField, MoneyValue
from paxman.types import FieldType

__all__ = ["ConflictInfo", "detect_conflicts"]


class _ConflictTypeKind(typing.Protocol):
    """Protocol marker (no runtime use). Real values are string literals."""


# Use plain string constants for the conflict type field — closed set,
# enumerated here for documentation.
CONFLICT_TYPE_VALUE_MISMATCH: typing.Final[str] = "value_mismatch"
CONFLICT_TYPE_CURRENCY_MISMATCH: typing.Final[str] = "currency_mismatch"


@attrs.frozen(slots=True)
class ConflictInfo:
    """Structured record of a detected conflict between candidates.

    Attributes:
        field_path: The dotted path of the conflicting field.
        candidate_values: Tuple of distinct conflicting values (or
            currencies, for currency-mismatch conflicts).
        conflict_type: One of ``"value_mismatch"`` or
            ``"currency_mismatch"``.
        candidate_count: Total number of candidates considered
            (including those that agreed with the winner).

    Examples:
        >>> ConflictInfo(
        ...     field_path="total_amount",
        ...     candidate_values=("100", "200"),
        ...     conflict_type="value_mismatch",
        ...     candidate_count=2,
        ... )
        ConflictInfo(field_path='total_amount', ...)
    """

    field_path: str = attrs.field()
    candidate_values: tuple[typing.Any, ...] = ()
    conflict_type: str = CONFLICT_TYPE_VALUE_MISMATCH
    candidate_count: int = 0

    def __attrs_post_init__(self) -> None:
        """Validate invariants.

        Raises:
            ValueError: If ``field_path`` is empty, ``conflict_type`` is
                not a known value, or ``candidate_count`` is negative.
            TypeError: If any field has the wrong type.
        """
        if not isinstance(self.field_path, str) or not self.field_path:
            raise ValueError(f"field_path must be a non-empty string, got {self.field_path!r}")
        if not isinstance(self.candidate_values, tuple):
            raise TypeError(
                f"candidate_values must be a tuple, got {type(self.candidate_values).__name__}"
            )
        if self.conflict_type not in (
            CONFLICT_TYPE_VALUE_MISMATCH,
            CONFLICT_TYPE_CURRENCY_MISMATCH,
        ):
            raise ValueError(
                f"conflict_type must be {CONFLICT_TYPE_VALUE_MISMATCH!r} or "
                f"{CONFLICT_TYPE_CURRENCY_MISMATCH!r}, got {self.conflict_type!r}"
            )
        if not isinstance(self.candidate_count, int) or isinstance(self.candidate_count, bool):
            raise TypeError(
                f"candidate_count must be an int, got {type(self.candidate_count).__name__}"
            )
        if self.candidate_count < 0:
            raise ValueError(f"candidate_count must be non-negative, got {self.candidate_count}")


def _values_equal(a: object, b: object) -> bool:
    """Return True if two candidate values should be considered equal.

    For MoneyValue, compares both amount and currency (not just equality).
    For other types, uses ``==``.
    """
    if isinstance(a, MoneyValue) and isinstance(b, MoneyValue):
        return a.amount == b.amount and a.currency == b.currency
    try:
        return bool(a == b)
    except Exception:
        return False


def detect_conflicts(
    candidates: tuple[Candidate, ...],
    *,
    field: CanonicalField,
) -> ConflictInfo | None:
    """Detect conflicts between candidates for a field.

    A conflict exists when:

    - Two or more candidates have different non-``None`` values
      (``value_mismatch``), OR
    - For MONEY fields, two or more candidates have different currency
      codes (``currency_mismatch`` — even if amounts happen to agree).

    Returns ``None`` if there is no conflict (single candidate, all
    agree, or only ``None`` values).

    Args:
        candidates: Tuple of :class:`Candidate` to inspect.
        field: The :class:`CanonicalField` being resolved. Used to
            determine whether the field is MONEY-typed.

    Returns:
        A :class:`ConflictInfo` if a conflict is detected, else ``None``.

    Raises:
        TypeError: If ``candidates`` is not a tuple or ``field`` is not
            a ``CanonicalField``.
    """
    if not isinstance(candidates, tuple):
        raise TypeError(f"candidates must be a tuple, got {type(candidates).__name__}")
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")

    # Filter out None values; only compare concrete candidate values.
    concrete = [c for c in candidates if isinstance(c, Candidate) and c.value is not None]
    if len(concrete) < 2:
        return None

    if field.type is FieldType.MONEY:
        # Currency-mismatch detection for MONEY fields.
        currencies: list[str] = []
        for c in concrete:
            val = c.value
            if isinstance(val, MoneyValue):
                currencies.append(val.currency)
            elif isinstance(val, str) and len(val) == 3 and val.isascii() and val.isupper():
                # Tolerate a bare currency-code string.
                currencies.append(val)
        distinct = sorted(set(currencies))
        if len(distinct) >= 2:
            return ConflictInfo(
                field_path=field.path,
                candidate_values=tuple(distinct),
                conflict_type=CONFLICT_TYPE_CURRENCY_MISMATCH,
                candidate_count=len(concrete),
            )
        # All MONEY values share a currency: no currency conflict. The
        # amount differences are handled by the merge strategy, not here.
        return None

    # Generic value-mismatch detection.
    values: list[typing.Any] = [c.value for c in concrete]
    # Find the first value; count distinct values.
    first = values[0]
    if all(_values_equal(first, v) for v in values[1:]):
        return None
    # Conflict: collect distinct values (dedup by value equality, not identity)
    # so equal-but-distinct objects from different capabilities are merged.
    distinct_values: list[typing.Any] = []
    for v in values:
        if not any(_values_equal(v, existing) for existing in distinct_values):
            distinct_values.append(v)
    # Sanity: a value conflict requires >= 2 distinct values.
    if len(distinct_values) < 2:
        return None
    return ConflictInfo(
        field_path=field.path,
        candidate_values=tuple(distinct_values),
        conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
        candidate_count=len(concrete),
    )

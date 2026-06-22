"""Internal primitives for the contract subsystem.

This module defines the **structural primitives** used by
:class:`~paxman.contract.canonical.CanonicalContract` and
:class:`~paxman.contract.canonical.CanonicalField`:

- :class:`Constraint` — a per-field validation rule (min_length, pattern,
  min_value, enum, etc.).
- :class:`ResolutionPolicy` — per-field fallback behavior when the planner's
  heuristic chain is exhausted.
- :class:`ContractPolicy` — per-contract overrides of the call-site
  :class:`~paxman.budget.Policy`.
- :class:`EnumValue` / :class:`EnumValueSet` — typed wrappers for ENUM fields
  with stable ordering and a closed-alphabet validator.

The :class:`paxman.types.FieldType` enum is the single source of truth for
the 9 V1 field types and is **re-exported** from :mod:`paxman.types`, not
redefined here. The contract layer uses it but does not own it.

All data models are :func:`attrs.frozen` with ``slots=True`` and an explicit
``__hash__`` (frozen attrs classes are hashable by default; ``slots`` is
required per ``DEPENDENCIES.md`` §3.2).

Every public symbol is listed in :data:`__all__`. Docstring coverage on the
public surface is enforced at 100 % by ``interrogate`` (``pyproject.toml``).
"""

from __future__ import annotations

import enum
import typing

import attrs

# FieldType is owned by paxman.types; re-export for convenience of the
# ``from paxman.contract._types import FieldType`` import path. This avoids
# a circular dependency (paxman.types is a leaf module) and keeps
# ``_types.py`` a self-contained, single-source module.
from paxman.types import FieldType

__all__ = [
    "Constraint",
    "ConstraintKind",
    "ContractPolicy",
    "EnumValue",
    "EnumValueSet",
    "FieldType",
    "ResolutionPolicy",
    "ResolutionStrategy",
]


# ---------------------------------------------------------------------------
# Constraint
# ---------------------------------------------------------------------------


@enum.unique
class ConstraintKind(enum.Enum):
    """The 7 V1 constraint kinds per ``docs/specs/dict-dsl-spec.md`` §3.2.

    Each kind maps to a specific validation rule. The V1 set is closed;
    adding a kind requires a new ADR per ``PACKAGE_STRUCTURE.md`` §3.4.

    Values:
        MIN_LENGTH: STRING/ARRAY minimum length. Params: ``{"min": int >= 0}``.
        MAX_LENGTH: STRING/ARRAY maximum length. Params: ``{"max": int >= 0}``.
        PATTERN: STRING regex. Params: ``{"regex": str}`` (Python ``re`` syntax).
        MIN_VALUE: INTEGER/DECIMAL/MONEY minimum numeric value.
            Params: ``{"min": number}``.
        MAX_VALUE: INTEGER/DECIMAL/MONEY maximum numeric value.
            Params: ``{"max": number}``.
        ENUM: closed-set membership. Params: ``{"values": list}``.
        ISO_4217: ISO-4217 currency code. Params: ``{}``.
    """

    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    ENUM = "enum"
    ISO_4217 = "iso_4217"


@attrs.frozen(slots=True)
class Constraint:
    """A single validation rule attached to a :class:`CanonicalField`.

    Constraints are produced by adapters (e.g., a Pydantic ``Field(min_length=2)``
    becomes a :class:`Constraint` of kind ``MIN_LENGTH`` with ``params={"min": 2}``).
    The Reconciler enforces them on candidate values during Sprint 5+.

    Attributes:
        kind: The :class:`ConstraintKind` identifying the rule.
        params: Kind-specific parameters. The keys and value types depend on
            ``kind``; see :class:`ConstraintKind` for the per-kind contract.
            Defaults to an empty dict (e.g., for ``ISO_4217``).
        message: Optional human-readable error message override. The
            Reconciler may use this when a candidate fails the constraint.
            Defaults to ``None`` (Reconciler uses the default message).

    Examples:
        >>> Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 2})
        Constraint(kind=<ConstraintKind.MIN_LENGTH: 'min_length'>, params={'min': 2}, message=None)
    """

    kind: ConstraintKind = attrs.field()
    params: dict[str, typing.Any] = attrs.field(factory=dict)
    message: str | None = None

    def __attrs_post_init__(self) -> None:
        """Validate invariant: ``kind`` is a :class:`ConstraintKind` instance.

        Raises:
            TypeError: If ``kind`` is not a :class:`ConstraintKind` member.
        """
        if not isinstance(self.kind, ConstraintKind):
            raise TypeError(
                f"kind must be a ConstraintKind, got {type(self.kind).__name__}: {self.kind!r}"
            )


# ---------------------------------------------------------------------------
# ResolutionPolicy
# ---------------------------------------------------------------------------


@enum.unique
class ResolutionStrategy(enum.Enum):
    """Per-field fallback behavior when the planner's heuristic chain is exhausted.

    Values:
        UNRESOLVED: Default. Field is marked ``UNRESOLVED`` and surfaced in
            ``ExecutionArtifact.unresolved_fields``.
        USE_DEFAULT: If the field has a default, the default value is used.
            Otherwise, the field is ``UNRESOLVED`` (defensive).
        REQUIRE_HUMAN: Field is flagged as needing human review (post-V1).
            In V1, this behaves like ``UNRESOLVED`` but carries an additional
            diagnostic.
    """

    UNRESOLVED = "UNRESOLVED"
    USE_DEFAULT = "USE_DEFAULT"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"


@attrs.frozen(slots=True)
class ResolutionPolicy:
    """Per-field fallback policy.

    A field's :class:`ResolutionPolicy` is consulted by the Reconciler when
    no candidate meets the field's :attr:`CanonicalField.confidence_threshold`.
    The default is :attr:`ResolutionStrategy.UNRESOLVED` (the safe behavior).

    Attributes:
        strategy: The :class:`ResolutionStrategy` to apply.
        require_human_review: When ``True``, the field is flagged as needing
            human review regardless of the strategy. Defaults to ``False``.

    Examples:
        >>> ResolutionPolicy()
        ResolutionPolicy(strategy=<ResolutionStrategy.UNRESOLVED: 'UNRESOLVED'>, require_human_review=False)
    """

    strategy: ResolutionStrategy = ResolutionStrategy.UNRESOLVED
    require_human_review: bool = False

    def __attrs_post_init__(self) -> None:
        """Validate ``strategy`` is a :class:`ResolutionStrategy` instance."""
        if not isinstance(self.strategy, ResolutionStrategy):
            raise TypeError(
                f"strategy must be a ResolutionStrategy, got {type(self.strategy).__name__}: "
                f"{self.strategy!r}"
            )


# ---------------------------------------------------------------------------
# EnumValue / EnumValueSet
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class EnumValue:
    """A single value in a closed enum.

    Wraps a Python value (typically ``str`` or ``int``) so adapters can
    represent enum values with explicit, hashable, and ordered membership.
    The same underlying value must compare equal to its Python equivalent
    (so ``EnumValue("active") == "active"`` is ``True``).

    Attributes:
        value: The underlying value.

    Examples:
        >>> EnumValue("active")
        EnumValue(value='active')
        >>> EnumValue("active") == "active"
        True
    """

    value: typing.Any = attrs.field()

    def __eq__(self, other: object) -> bool:
        """Compare to another :class:`EnumValue` or to a raw Python value."""
        if isinstance(other, EnumValue):
            return bool(self.value == other.value)
        return bool(self.value == other)

    def __hash__(self) -> int:
        """Hash by underlying value (so ``EnumValue("x")`` and ``"x"`` are interchangeable)."""
        return hash(self.value)

    def __str__(self) -> str:
        """Return the string form of the underlying value."""
        return str(self.value)

    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"EnumValue(value={self.value!r})"


@attrs.frozen(slots=True)
class EnumValueSet:
    """A closed set of allowed values for an ENUM field.

    The set is deduplicated at construction (no duplicates) and preserves
    insertion order for deterministic serialization. Membership is checked
    with ``value in enum_value_set`` and returns ``True`` for either an
    :class:`EnumValue` or the raw value.

    Attributes:
        values: The ordered, deduplicated list of allowed values.

    Raises:
        ValueError: If ``values`` is empty (a closed enum must have at
            least one value).

    Examples:
        >>> s = EnumValueSet(["active", "inactive"])
        >>> "active" in s
        True
        >>> "missing" in s
        False
    """

    values: tuple[typing.Any, ...] = attrs.field(converter=tuple)

    def __attrs_post_init__(self) -> None:
        """Validate and deduplicate the input values.

        Raises:
            ValueError: If ``values`` is empty.
        """
        if not self.values:
            raise ValueError("EnumValueSet must contain at least one value")
        # Deduplicate while preserving order; this also catches duplicates
        # supplied by callers.
        seen: set[typing.Any] = set()
        deduped: list[typing.Any] = []
        for v in self.values:
            if v not in seen:
                seen.add(v)
                deduped.append(v)
        object.__setattr__(self, "values", tuple(deduped))

    def __contains__(self, item: object) -> bool:
        """Test membership by raw value or :class:`EnumValue`."""
        if isinstance(item, EnumValue):
            return item.value in self.values
        return item in self.values

    def __iter__(self) -> typing.Iterator[typing.Any]:
        """Iterate over the underlying values in deterministic order."""
        return iter(self.values)

    def __len__(self) -> int:
        """Return the number of values in the set."""
        return len(self.values)

    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"EnumValueSet(values={self.values!r})"


# ---------------------------------------------------------------------------
# ContractPolicy
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class ContractPolicy:
    """Per-contract overrides of the call-site :class:`~paxman.budget.Policy`.

    A :class:`CanonicalContract` may carry a :class:`ContractPolicy` that
    overrides specific policy keys for fields in this contract only. The
    call-site :class:`~paxman.budget.Policy` is the global default; a
    :class:`ContractPolicy` is the local refinement.

    Attributes:
        confidence_floor: Minimum confidence to mark a field ``SUCCESS``
            instead of ``PARTIAL_SUCCESS``. Range: ``[0.0, 1.0]``. Defaults
            to ``None`` (inherit the call-site default).
        unresolved_acceptable: If ``True``, an unresolved required field
            yields ``PARTIAL_SUCCESS`` instead of ``UNRESOLVED``. Defaults
            to ``None``.
        stop_on_first_unresolved: If ``True``, the executor halts on the
            first unresolved required field. Defaults to ``None``.

    Examples:
        >>> ContractPolicy(confidence_floor=0.85)
        ContractPolicy(confidence_floor=0.85, unresolved_acceptable=None, stop_on_first_unresolved=None)
    """

    confidence_floor: float | None = None
    unresolved_acceptable: bool | None = None
    stop_on_first_unresolved: bool | None = None

    def __attrs_post_init__(self) -> None:
        """Validate field types and ``confidence_floor`` range.

        Raises:
            TypeError: If a field has the wrong Python type.
            ValueError: If ``confidence_floor`` is outside the valid range.
        """
        # Type validation (Oracle review F2): reject non-bool / non-float
        # values that would otherwise be silently accepted due to Python's
        # permissive type coercion (e.g., ``True`` being treated as ``1.0``).
        if self.unresolved_acceptable is not None and not isinstance(
            self.unresolved_acceptable, bool
        ):
            raise TypeError(
                f"unresolved_acceptable must be a bool, got {type(self.unresolved_acceptable).__name__}: "
                f"{self.unresolved_acceptable!r}"
            )
        if self.stop_on_first_unresolved is not None and not isinstance(
            self.stop_on_first_unresolved, bool
        ):
            raise TypeError(
                f"stop_on_first_unresolved must be a bool, got {type(self.stop_on_first_unresolved).__name__}: "
                f"{self.stop_on_first_unresolved!r}"
            )
        if self.confidence_floor is not None and not isinstance(self.confidence_floor, float):
            raise TypeError(
                f"confidence_floor must be a float, got {type(self.confidence_floor).__name__}: "
                f"{self.confidence_floor!r}"
            )
        if self.confidence_floor is not None and not 0.0 <= self.confidence_floor <= 1.0:
            raise ValueError(f"confidence_floor must be in [0.0, 1.0], got {self.confidence_floor}")

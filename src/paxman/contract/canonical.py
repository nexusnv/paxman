"""Canonical contract and canonical field — the V1 canonical contract model.

This module is the **heart of the contract subsystem**. It defines the
language-agnostic representation that every adapter translates to and from:

- :class:`MoneyValue` — the first-class monetary value (per ADR-0004).
- :class:`CanonicalField` — a single property in a canonical contract.
- :class:`CanonicalContract` — the full canonical contract (id, version,
  fields, constraints, policies).

Invariants (per ``PACKAGE_STRUCTURE.md`` §3.4):

1. **9 V1 field types** — ``STRING``, ``INTEGER``, ``DECIMAL``, ``BOOLEAN``,
   ``DATE``, ``ENUM``, ``OBJECT``, ``ARRAY``, ``MONEY``. Any new type
   requires an ADR.
2. **``MONEY`` is first-class** — :class:`MoneyValue` carries
   ``amount: Decimal``, ``currency: str`` (ISO-4217), and ``precision: int | None``.
3. **Validation is mandatory** — :func:`validate_canonical_contract` (in
   :mod:`paxman.contract.validator`) is called by every adapter before
   producing a :class:`CanonicalContract`.
4. **Same input always produces the same output** — these classes are
   frozen and slot-typed; there is no mutable state.

Design notes
------------

All data classes use :func:`attrs.frozen` with ``slots=True`` per
``DEPENDENCIES.md`` §3.2. Validation lives in ``__attrs_post_init__`` to
play nicely with mypy --strict (which is incompatible with ``@validators``-decorated methods).
"""

from __future__ import annotations

import decimal
import re
import typing

import attrs

from paxman.contract._format_hint import FormatHint
from paxman.contract._types import Constraint, ContractPolicy, EnumValueSet, ResolutionPolicy
from paxman.types import FieldType

__all__ = [
    "CanonicalContract",
    "CanonicalField",
    "MoneyValue",
]


# ---------------------------------------------------------------------------
# MONEY (first-class; ADR-0004)
# ---------------------------------------------------------------------------

#: Default precision when none is specified. ``2`` matches ISO 4217 minor
#: unit convention for most fiat currencies. ``JPY`` uses ``0``, but precision
#: here is the field-level "expected decimal places" hint; the actual
#: arithmetic is governed by the :class:`~paxman.budget.CurrencyPolicy`.
_DEFAULT_MONEY_PRECISION: typing.Final[int] = 2

#: ISO-4217 currency code pattern. Three uppercase ASCII letters.
_ISO_4217_PATTERN: typing.Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}$")


@attrs.frozen(slots=True)
class MoneyValue:
    """A monetary value: amount + ISO-4217 currency + optional precision.

    First-class per ADR-0004. **Not** a tagged ``DECIMAL``. The Reconciler
    uses :class:`MoneyValue` for currency-matching and arithmetic; floats
    are never used for monetary math.

    Attributes:
        amount: The numeric amount. Must be a :class:`decimal.Decimal` (no
            :class:`float` to preserve exact precision). Negative amounts
            are allowed (e.g., refunds, credits).
        currency: The ISO-4217 currency code (three uppercase ASCII letters,
            e.g., ``"USD"``, ``"EUR"``, ``"JPY"``). Validated against the
            ISO-4217 pattern at construction.
        precision: Optional expected decimal places. ``None`` means "inferred
            from amount" (count of digits after the decimal point). The
            default of ``2`` matches most fiat currencies.

    Raises:
        TypeError: If ``amount`` is not a :class:`decimal.Decimal`.
        ValueError: If ``currency`` does not match the ISO-4217 pattern, or
            if ``precision`` is negative.

    Examples:
        >>> from decimal import Decimal
        >>> MoneyValue(amount=Decimal("19.99"), currency="USD")
        MoneyValue(amount=Decimal('19.99'), currency='USD', precision=2)
        >>> MoneyValue(amount=Decimal("1000"), currency="JPY", precision=0)
        MoneyValue(amount=Decimal('1000'), currency='JPY', precision=0)
    """

    amount: decimal.Decimal = attrs.field()
    currency: str = attrs.field()
    precision: int | None = _DEFAULT_MONEY_PRECISION

    def __attrs_post_init__(self) -> None:
        """Validate amount, currency, and precision invariants.

        Raises:
            TypeError: If ``amount`` is not a :class:`decimal.Decimal`.
            ValueError: If ``currency`` is not a valid ISO-4217 code or if
                ``precision`` is negative.
        """
        if not isinstance(self.amount, decimal.Decimal):
            raise TypeError(
                f"amount must be a Decimal, got {type(self.amount).__name__}: {self.amount!r}"
            )
        if not isinstance(self.currency, str) or not _ISO_4217_PATTERN.match(self.currency):
            raise ValueError(
                f"currency must be a 3-letter uppercase ISO-4217 code, got {self.currency!r}"
            )
        if self.precision is not None:
            if not isinstance(self.precision, int) or isinstance(self.precision, bool):
                raise TypeError(
                    f"precision must be an int or None, got {type(self.precision).__name__}"
                )
            if self.precision < 0:
                raise ValueError(f"precision must be non-negative, got {self.precision}")


# ---------------------------------------------------------------------------
# CanonicalField
# ---------------------------------------------------------------------------


#: Path-pattern for valid field paths. Top-level fields use ``name``; nested
#: fields use ``name.subname`` and arrays use ``name[].subname`` (brackets
#: may follow a field name directly without a dot). This is a minimal
#: JSON-Path-like subset — full JSON-Path is V2.
#:
#: Oracle review F12: the previous pattern required a dot before ``[]``,
#: which rejected documented paths like ``line_items[].price``. The new
#: pattern correctly accepts:
#:   - ``a`` / ``a.b`` / ``a.b.c`` (dotted)
#:   - ``a[]`` / ``a[].b`` / ``a.b[].c.d`` (with array segments)
#: and rejects malformed forms like ``a.[].b``, ``a[]b``, ``.a``.
_FIELD_PATH_PATTERN: typing.Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\[\])?(?:\.(?:[A-Za-z_][A-Za-z0-9_]*(?:\[\])?))*$"
)


@attrs.frozen(slots=True)
class CanonicalField:
    """A single property in a canonical contract.

    A :class:`CanonicalContract` is an ordered collection of
    :class:`CanonicalField` objects. Fields are immutable and slot-typed;
    adapters produce them and downstream consumers (planner, executor,
    reconciler) only read.

    Attributes:
        id: Stable, prefixed identifier (e.g., ``field_a1b2c3d4e5f6``).
            Generated by the adapter; the contract layer does not generate
            IDs itself (determinism is the adapter's responsibility).
        path: Dotted JSON-Path-like identifier within the contract
            (e.g., ``"supplier_name"``, ``"line_items[].price"``).
        name: Human-readable field name (typically the last path segment,
            without ``[]`` or ``.``).
        type: The :class:`~paxman.types.FieldType`.
        required: If ``True``, an unresolved status prevents ``SUCCESS``.
        critical: If ``True``, the field is flagged as high-stakes. The
            planner may use this to raise ``target_confidence`` for the
            field. Defaults to ``False``.
        nullable: If ``True``, the field accepts ``None`` as a value.
            Defaults to ``False``.
        description: Optional human-readable description. Defaults to ``None``.
        confidence_threshold: Minimum confidence required for the field
            to be considered resolved. Range: ``[0.0, 1.0]``. Defaults to
            ``0.80`` (the V1 default per ``budget.Policy.confidence_floor``).
        evidence_required: If ``True``, the field must carry at least one
            evidence reference in its resolved result. Defaults to ``False``.
        semantic_tags: Tuple of semantic tags (e.g., ``"pii"``,
            ``"currency-sensitive"``). Untrusted by the contract layer
            (validated in :mod:`paxman.contract.semantics`). Defaults to
            an empty tuple.
        fallback_policy: The :class:`~paxman.contract._types.ResolutionPolicy`
            to apply when no candidate meets the threshold. Defaults to
            ``UNRESOLVED``.
        enum_values: For ``ENUM`` fields, the closed set of allowed values.
            Must be ``None`` for non-ENUM fields. Validated post-init.
        default: Optional default value. Must match ``type`` if set
            (validated in :class:`CanonicalContract` construction). The
            field's :attr:`required` flag and ``default`` are independent.
        constraints: Tuple of :class:`~paxman.contract._types.Constraint`
            rules. Defaults to an empty tuple.
        format_hints: Wire-format hints for input-format-aware
            tier-1 extractors. Tuple of :class:`FormatHint` members
            (``CSV`` / ``JSON`` / ``XML`` in V1.1.0; future members
            are additive). Empty tuple means "no format preference" —
            the planner falls back to the existing tier-1 selection
            logic. See `ADR-0015
            <../adr/0015-format-aware-executor-auto-dispatch.md>`_
            and `issue #73
            <https://github.com/nexusnv/paxman/issues/73>`_.

    Raises:
        TypeError: If any field has the wrong type.
        ValueError: If a field's invariants are violated (e.g., empty name,
            confidence_threshold out of range, enum_values for non-ENUM
            type, default that doesn't match the type).

    Examples:
        >>> from paxman.contract._types import ResolutionPolicy
        >>> from paxman.types import FieldType
        >>> CanonicalField(
        ...     id="field_a1b2c3d4e5f6",
        ...     path="supplier_name",
        ...     name="supplier_name",
        ...     type=FieldType.STRING,
        ...     required=True,
        ... )
        CanonicalField(id='field_a1b2c3d4e5f6', path='supplier_name', name='supplier_name', type=<FieldType.STRING: 'STRING'>, required=True, critical=False, nullable=False, description=None, confidence_threshold=0.8, evidence_required=False, semantic_tags=(), fallback_policy=ResolutionPolicy(strategy=<ResolutionStrategy.UNRESOLVED: 'UNRESOLVED'>, require_human_review=False), enum_values=None, default=None, constraints=(), format_hints=())
    """

    id: str = attrs.field()
    path: str = attrs.field()
    name: str = attrs.field()
    type: FieldType = attrs.field()
    required: bool = attrs.field()
    # Optional / derived attributes
    critical: bool = False
    nullable: bool = False
    description: str | None = None
    confidence_threshold: float = 0.80
    evidence_required: bool = False
    semantic_tags: tuple[str, ...] = ()
    fallback_policy: ResolutionPolicy = attrs.field(default=attrs.Factory(ResolutionPolicy))
    enum_values: EnumValueSet | None = None
    default: typing.Any = None
    constraints: tuple[Constraint, ...] = ()
    format_hints: tuple[FormatHint, ...] = ()

    def __attrs_post_init__(self) -> None:
        """Validate all field invariants.

        Raises:
            TypeError: If a field has the wrong type.
            ValueError: If an invariant is violated.
        """
        # --- id ---
        if not isinstance(self.id, str) or not self.id:
            raise ValueError(f"id must be a non-empty string, got {self.id!r}")
        # --- path ---
        if not isinstance(self.path, str) or not self.path:
            raise ValueError(f"path must be a non-empty string, got {self.path!r}")
        if not _FIELD_PATH_PATTERN.match(self.path):
            raise ValueError(
                f"path must match the JSON-Path-like pattern "
                f"([A-Za-z_][A-Za-z0-9_]*(?:\\[\\])?(?:\\.[A-Za-z_][A-Za-z0-9_]*(?:\\[\\])?)*), got {self.path!r}"
            )
        # --- name ---
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"name must be a non-empty string, got {self.name!r}")
        if "." in self.name or "[" in self.name or "]" in self.name:
            raise ValueError(
                f"name must not contain '.' or '[]' (use path for nested access), got {self.name!r}"
            )
        # --- type ---
        if not isinstance(self.type, FieldType):
            raise TypeError(
                f"type must be a FieldType, got {type(self.type).__name__}: {self.type!r}"
            )
        # --- required (bool, not int; rejected explicitly) ---
        if not isinstance(self.required, bool):
            raise TypeError(f"required must be a bool, got {type(self.required).__name__}")
        # --- confidence_threshold ---
        if not isinstance(self.confidence_threshold, (int, float)) or isinstance(
            self.confidence_threshold, bool
        ):
            raise TypeError(
                f"confidence_threshold must be a number, got {type(self.confidence_threshold).__name__}"
            )
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be in [0.0, 1.0], got {self.confidence_threshold}"
            )
        # --- fallback_policy ---
        if not isinstance(self.fallback_policy, ResolutionPolicy):
            raise TypeError(
                f"fallback_policy must be a ResolutionPolicy, got {type(self.fallback_policy).__name__}"
            )
        # --- enum_values / type coupling ---
        if self.type is FieldType.ENUM:
            if self.enum_values is None:
                raise ValueError(f"ENUM field {self.name!r} must have non-None enum_values")
            if not isinstance(self.enum_values, EnumValueSet):
                raise TypeError(
                    f"enum_values must be an EnumValueSet for ENUM field, "
                    f"got {type(self.enum_values).__name__}"
                )
        else:
            if self.enum_values is not None:
                raise ValueError(
                    f"enum_values is only allowed for ENUM fields, "
                    f"not {self.type.name}, on field {self.name!r}"
                )
        # --- format_hints ---
        if not isinstance(self.format_hints, tuple):
            raise TypeError(
                f"format_hints must be a tuple of FormatHint, "
                f"got {type(self.format_hints).__name__}"
            )
        bad = [v for v in self.format_hints if not isinstance(v, FormatHint)]
        if bad:
            raise TypeError(
                f"format_hints must be a tuple of FormatHint, got non-FormatHint values: {bad!r}"
            )
        # --- default / type coupling (best-effort) ---
        self._validate_default()

    def _validate_default(self) -> None:
        """Validate the ``default`` value matches the field's ``type``.

        A ``None`` default is allowed regardless of ``type`` (callers may
        use it to indicate "no default"). A non-None default must be
        type-compatible.

        Raises:
            ValueError: If the default value is incompatible with ``type``.
        """
        if self.default is None:
            return
        if self.type is FieldType.STRING and not isinstance(self.default, str):
            raise ValueError(
                f"STRING field {self.name!r} default must be str, got {type(self.default).__name__}"
            )
        # Oracle review F13: use exact type for INTEGER (bool is a subclass of int
        # in Python; without this, ``True``/``False`` would be silently accepted).
        if self.type is FieldType.INTEGER and (type(self.default) is not int):
            raise ValueError(
                f"INTEGER field {self.name!r} default must be int, got {type(self.default).__name__}"
            )
        if self.type is FieldType.BOOLEAN and not isinstance(self.default, bool):
            raise ValueError(
                f"BOOLEAN field {self.name!r} default must be bool, got {type(self.default).__name__}"
            )
        if self.type is FieldType.MONEY and not isinstance(self.default, MoneyValue):
            raise ValueError(
                f"MONEY field {self.name!r} default must be MoneyValue, got {type(self.default).__name__}"
            )
        if self.type is FieldType.OBJECT and not isinstance(self.default, (dict, type(None))):
            raise ValueError(
                f"OBJECT field {self.name!r} default must be a dict, got {type(self.default).__name__}"
            )
        if self.type is FieldType.ARRAY and not isinstance(self.default, (list, tuple)):
            raise ValueError(
                f"ARRAY field {self.name!r} default must be a list, got {type(self.default).__name__}"
            )
        # Oracle review F13: add missing DECIMAL and ENUM validations.
        if self.type is FieldType.DECIMAL and (
            not isinstance(self.default, (int, float, decimal.Decimal))
            or isinstance(self.default, bool)
        ):
            raise ValueError(
                f"DECIMAL field {self.name!r} default must be a number, "
                f"got {type(self.default).__name__}"
            )
        if self.type is FieldType.ENUM:
            if self.enum_values is None or self.default not in self.enum_values:
                raise ValueError(
                    f"ENUM field {self.name!r} default must be a valid enum value, "
                    f"got {self.default!r}"
                )


# ---------------------------------------------------------------------------
# CanonicalContract
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class CanonicalContract:
    """The canonical, language-agnostic contract.

    A :class:`CanonicalContract` is the single internal representation that
    the planner, executor, and reconciler read. It is produced by an
    adapter and is never mutated thereafter.

    Attributes:
        id: Stable contract identifier (e.g., ``"invoice-v1"``). The caller
            owns this string; the adapter carries it through.
        version: The contract format version (e.g., ``"1"``). Defaults to
            :data:`paxman.versioning.CONTRACT_FORMAT_VERSION`.
        fields: Ordered tuple of :class:`CanonicalField`. Must be non-empty
            (an empty contract is meaningless and likely indicates a bug).
        constraints: Tuple of contract-level :class:`Constraint` rules
            (cross-field constraints; V2 feature). Defaults to empty.
        policies: Optional :class:`ContractPolicy` of per-contract
            overrides. Defaults to ``None``.

    Raises:
        TypeError: If a field has the wrong type.
        ValueError: If a contract invariant is violated (empty fields,
            duplicate field IDs, duplicate field paths, invalid MONEY
            default).

    Examples:
        >>> from paxman.types import FieldType
        >>> CanonicalContract(
        ...     id="invoice-v1",
        ...     version="1",
        ...     fields=(
        ...         CanonicalField(
        ...             id="field_1",
        ...             path="supplier_name",
        ...             name="supplier_name",
        ...             type=FieldType.STRING,
        ...             required=True,
        ...         ),
        ...     ),
        ... )
        CanonicalContract(id='invoice-v1', version='1', fields=(CanonicalField(id='field_1', ...),), constraints=(), policies=None)
    """

    # IMPORTANT: in attrs, mandatory attributes must come BEFORE any
    # attribute with a default. The order below is: id (mandatory),
    # fields (mandatory), then version/constraints/policies (defaulted).
    id: str = attrs.field()
    fields: tuple[CanonicalField, ...] = attrs.field()
    version: str = "1"
    constraints: tuple[Constraint, ...] = ()
    policies: ContractPolicy | None = None

    def __attrs_post_init__(self) -> None:
        """Validate contract-level invariants.

        Raises:
            TypeError: If a field has the wrong type.
            ValueError: If a contract invariant is violated.
        """
        if not isinstance(self.id, str) or not self.id:
            raise ValueError(f"id must be a non-empty string, got {self.id!r}")
        if not isinstance(self.version, str) or not self.version:
            raise ValueError(f"version must be a non-empty string, got {self.version!r}")
        if not self.fields:
            raise ValueError("CanonicalContract must have at least one field")
        for f in self.fields:
            if not isinstance(f, CanonicalField):
                raise TypeError(f"fields must be CanonicalField, got {type(f).__name__}: {f!r}")
        # Uniqueness: ids and paths must be unique within the contract.
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        for f in self.fields:
            if f.id in seen_ids:
                raise ValueError(f"duplicate field id: {f.id!r}")
            seen_ids.add(f.id)
            if f.path in seen_paths:
                raise ValueError(f"duplicate field path: {f.path!r}")
            seen_paths.add(f.path)
        # MONEY defaults: must carry a valid MoneyValue.
        for f in self.fields:
            if f.type is FieldType.MONEY and f.default is not None:
                if not isinstance(f.default, MoneyValue):
                    raise ValueError(
                        f"MONEY field {f.name!r} default must be a MoneyValue, "
                        f"got {type(f.default).__name__}"
                    )

    # --- Convenience helpers (pure) ---

    def field_by_path(self, path: str) -> CanonicalField | None:
        """Return the field with the given path, or ``None`` if not found.

        Args:
            path: The field's dotted path (e.g., ``"line_items[].price"``).

        Returns:
            The matching :class:`CanonicalField` or ``None``.

        Examples:
            >>> from paxman.types import FieldType
            >>> c = CanonicalContract(
            ...     id="x",
            ...     fields=(
            ...         CanonicalField(id="f1", path="a", name="a",
            ...                       type=FieldType.STRING, required=True),
            ...     ),
            ... )
            >>> c.field_by_path("a").name
            'a'
            >>> c.field_by_path("missing")
        """
        for f in self.fields:
            if f.path == path:
                return f
        return None

    def field_by_id(self, fid: str) -> CanonicalField | None:
        """Return the field with the given ID, or ``None`` if not found.

        Args:
            fid: The field's prefixed ID (e.g., ``"field_a1b2c3d4e5f6"``).

        Returns:
            The matching :class:`CanonicalField` or ``None``.
        """
        for f in self.fields:
            if f.id == fid:
                return f
        return None

    def required_fields(self) -> tuple[CanonicalField, ...]:
        """Return all fields with ``required=True``.

        Returns:
            A tuple of :class:`CanonicalField` (in declaration order).
        """
        return tuple(f for f in self.fields if f.required)

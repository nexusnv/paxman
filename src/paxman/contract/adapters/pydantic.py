"""Pydantic v2 adapter — ``pydantic.BaseModel`` ↔ :class:`CanonicalContract`.

The adapter is pure: it inspects a Pydantic v2 ``BaseModel`` subclass via
``model_fields`` and produces a :class:`CanonicalContract` whose
:class:`CanonicalField` objects carry every constraint that Pydantic
expresses (length, range, pattern, default, description, alias).

Mappings
--------

Type mapping (Pydantic annotation → ``FieldType``):

- ``str``  → ``STRING``
- ``int``  → ``INTEGER``
- ``float`` → ``DECIMAL`` (no MONEY; Pydantic has no native MONEY type)
- ``bool`` → ``BOOLEAN``
- ``datetime.date`` / ``datetime.datetime`` → ``DATE``
- ``enum.Enum`` / ``enum.StrEnum`` / ``typing.Literal`` → ``ENUM``
- ``dict`` / ``BaseModel`` → ``OBJECT``
- ``list`` / ``tuple`` / ``set`` → ``ARRAY``
- ``pydantic.Json`` → ``STRING`` (Pydantic v2's "arbitrary JSON" type)

A Pydantic model with a ``Decimal`` + ``str`` currency pair is **not**
auto-detected as MONEY; callers must opt in via a custom subclass of
``pydantic.BaseModel`` named ``Money`` (see ``adapt_money_class`` below)
or a tagged field with ``Annotated[Decimal, Field(description="amount in
USD")]`` — V1 adapter does **not** auto-infer MONEY; the Dict DSL
explicitly names ``MONEY``, and Pydantic authors can use the dedicated
:class:`MoneyValue` payload via JSON.

Constraint mapping (Pydantic ``Field`` → ``Constraint``):

- ``min_length`` → ``MIN_LENGTH`` (string / array)
- ``max_length`` → ``MAX_LENGTH`` (string / array)
- ``pattern`` / ``regex`` → ``PATTERN``
- ``ge`` / ``gt`` → ``MIN_VALUE`` (inclusive/exclusive preserved via ``inclusive`` key)
- ``le`` / ``lt`` → ``MAX_VALUE``
- ``multiple_of`` → not mapped (V2)

Pydantic's ``description`` and ``title`` map to ``CanonicalField.description``;
Pydantic's ``alias`` and ``serialization_alias`` are not yet mapped (V2).

Error model
-----------

Every error raised is :class:`paxman.errors.InvalidContractError` with
one of the following ``error_code`` values:

- ``UNSUPPORTED_FIELD_TYPE`` — the annotation is not expressible in V1
  (e.g., a Pydantic custom type without a known mapping).
- ``INVALID_CONSTRAINT`` — a Pydantic ``Field`` constraint is malformed.
- ``INVALID_FIELD`` — a field is fundamentally malformed (e.g., missing name).
- ``MISSING_FIELD_NAME`` — a Pydantic field has no ``name`` (Pydantic always
  provides one, but defensive).
- ``INVALID_MONEY_PAIR`` — a Pydantic model declared as MONEY (via the
  ``Money`` base class) is malformed (missing ``amount`` or ``currency``).
- ``UNSUPPORTED_PYDANTIC_FEATURE`` — the Pydantic model uses a feature V1
  does not support (e.g., ``discriminated unions``).

V1 explicitly does **not** support:

- ``Union`` types (other than ``Optional[X]`` which is mapped to
  ``nullable=True``).
- ``TypeVar`` / generics.
- ``discriminated unions``.
- ``model_validator`` (Pydantic's runtime cross-field validators; the
  contract layer doesn't enforce them).
"""

from __future__ import annotations

import datetime
import enum
import inspect
import re
import typing
from decimal import Decimal

import attrs
import pydantic
from pydantic_core import PydanticUndefined

from paxman.contract._format_hint import FormatHint, resolve_format_hint
from paxman.contract._types import (
    Constraint,
    ConstraintKind,
    EnumValueSet,
)
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.errors import InvalidContractError
from paxman.types import FieldType

__all__ = ["Money", "PydanticAdapter"]


# ---------------------------------------------------------------------------
# Money base class (optional; opt-in for Pydantic authors)
# ---------------------------------------------------------------------------


class Money(pydantic.BaseModel):
    """A Pydantic-friendly money value.

    Pydantic authors who want a MONEY-typed field in their contract can
    subclass this. The adapter detects subclasses and maps them to
    :class:`MoneyValue` with the corresponding ``FieldType.MONEY``.

    Attributes:
        amount: The numeric amount. ``Decimal`` is required for
            precision; do not use ``float``.
        currency: ISO-4217 currency code (3 uppercase letters).
        precision: Optional expected decimal places.

    Examples:
        >>> from decimal import Decimal
        >>> m = Money(amount=Decimal('19.99'), currency='USD')
        >>> m.amount
        Decimal('19.99')
    """

    model_config = pydantic.ConfigDict(frozen=True)

    amount: Decimal
    currency: str = pydantic.Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    precision: int | None = None


# ---------------------------------------------------------------------------
# Type mapping
# ---------------------------------------------------------------------------


def _is_optional(annotation: typing.Any) -> tuple[bool, typing.Any]:
    """Return ``(True, inner)`` if *annotation* is ``Optional[X]`` or ``X | None``."""
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Union and type(None) in args:  # Optional[X] / Union[X, None]
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return True, non_none[0]
        # Union of multiple non-None types → not supported in V1.
        return False, annotation
    if origin is not None and getattr(origin, "__name__", "") == "UnionType":
        # PEP 604: `int | None`
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return True, non_none[0]
    return False, annotation


def _unwrap_annotated(annotation: typing.Any) -> tuple[typing.Any, list[typing.Any]]:
    """Unwrap ``Annotated[T, ...]`` and return ``(T, [metadata])``."""
    if typing.get_origin(annotation) is typing.Annotated:
        args = typing.get_args(annotation)
        return args[0], list(args[1:])
    return annotation, []


def _python_type_to_field_type(
    annotation: typing.Any,
) -> FieldType | None:
    """Map a Python/Pydantic annotation to a :class:`FieldType`.

    Returns ``None`` if the annotation is not expressible in V1.
    """
    # MONEY subclass check (must be before any generic handling).
    try:
        if inspect.isclass(annotation) and issubclass(annotation, Money):
            return FieldType.MONEY
    except TypeError:
        pass
    # Nested Pydantic BaseModel → OBJECT (matches the docstring mapping;
    # V1 does not flatten nested schemas — the OBJECT type is a passthrough
    # in the Reconciler).
    try:
        if inspect.isclass(annotation) and issubclass(annotation, pydantic.BaseModel):
            return FieldType.OBJECT
    except TypeError:
        pass
    # Literal → ENUM
    if typing.get_origin(annotation) is typing.Literal:
        return FieldType.ENUM
    # Enum subclasses
    if inspect.isclass(annotation) and issubclass(annotation, enum.Enum):
        return FieldType.ENUM
    # Direct class lookups
    if annotation is str:
        return FieldType.STRING
    if annotation is int:
        return FieldType.INTEGER
    if annotation is bool:
        return FieldType.BOOLEAN
    if annotation is float:
        return FieldType.DECIMAL
    if annotation is Decimal:
        return FieldType.DECIMAL
    if annotation is datetime.datetime or annotation is datetime.date:
        return FieldType.DATE
    if annotation is dict:
        return FieldType.OBJECT
    if annotation is list:
        return FieldType.ARRAY
    # Pydantic special types
    if annotation is pydantic.Json:
        return FieldType.STRING
    # Generic origin lookups (list[int], dict[str, int], etc.).
    origin = typing.get_origin(annotation)
    if origin is list or origin is tuple or origin is set or origin is frozenset:
        return FieldType.ARRAY
    if origin is dict:
        return FieldType.OBJECT
    return None


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class PydanticAdapter:
    """Adapter for Pydantic v2 ``BaseModel`` classes.

    The adapter is pure and stateless; the same model class always
    produces the same :class:`CanonicalContract`. No I/O, no clock, no
    random.

    Attributes:
        This class has no fields. All methods are pure functions of their
        arguments.

    Examples:
        >>> from pydantic import BaseModel, Field
        >>> from paxman.contract.adapters.pydantic import PydanticAdapter
        >>> class Invoice(BaseModel):
        ...     supplier_name: str = Field(..., description="Supplier name")
        ...     total: float
        >>> adapter = PydanticAdapter()
        >>> contract = adapter.adapt(Invoice)
        >>> contract.id
        'Invoice'
        >>> len(contract.fields)
        2
    """

    @property
    def format_id(self) -> str:
        """The adapter's format identifier."""
        return "pydantic"

    # ----- adapt ---------------------------------------------------------

    def adapt(self, external: typing.Any) -> CanonicalContract:
        """Translate a Pydantic v2 ``BaseModel`` class into a :class:`CanonicalContract`.

        Args:
            external: A ``pydantic.BaseModel`` subclass.

        Returns:
            The :class:`CanonicalContract` representation.

        Raises:
            InvalidContractError: If *external* is not a Pydantic v2
                ``BaseModel`` subclass or if a field uses an unsupported
                feature.
        """
        if not (inspect.isclass(external) and issubclass(external, pydantic.BaseModel)):
            raise InvalidContractError(
                f"pydantic adapter requires a BaseModel subclass, got {type(external).__name__}",
                error_code="INVALID_FIELD",
                context={"got_type": type(external).__name__},
            )
        fields: list[CanonicalField] = []
        for name, field_info in external.model_fields.items():
            fields.append(self._adapt_field(name, field_info, model_cls=external))
        return CanonicalContract(
            id=external.__name__,
            fields=tuple(fields),
        )

    # ----- export --------------------------------------------------------

    def export(self, canonical: CanonicalContract) -> type[pydantic.BaseModel]:
        """Translate a :class:`CanonicalContract` back into a Pydantic v2 ``BaseModel`` class.

        The output is a fresh ``BaseModel`` subclass. Round-trippable
        within the Pydantic v2 expressible subset:

        - STRING, INTEGER, BOOLEAN, DATE, OBJECT (dict), ARRAY (list), DECIMAL (Decimal)
        - ENUM (Literal)
        - MONEY (Money subclass)

        Args:
            canonical: The :class:`CanonicalContract` to export.

        Returns:
            A new ``pydantic.BaseModel`` subclass.

        Raises:
            InvalidContractError: If *canonical* contains a constraint
                Pydantic v2 cannot represent.
        """
        if not isinstance(canonical, CanonicalContract):
            raise InvalidContractError(
                f"export expects CanonicalContract, got {type(canonical).__name__}",
                error_code="INVALID_FIELD",
                context={"got_type": type(canonical).__name__},
            )
        annotations: dict[str, typing.Any] = {}
        # Pydantic's create_model wants (annotation, default) per field. We
        # build a small dict of name -> (annotation, default). The per-field
        # FieldInfo constraints (min_length, pattern, etc.) are encoded
        # through ``pydantic.Field`` as the default; we therefore call
        # ``_export_field`` to get the (annotation, default) tuple where
        # default is already a pydantic.Field(...) instance.
        for f in canonical.fields:
            annotation, default = self._export_field(f)
            annotations[f.name] = (annotation, default)
        # Build a dynamic model. ``create_model`` returns ``Any`` per mypy;
        # we know it is a ``type[BaseModel]``.
        model: type[pydantic.BaseModel] = pydantic.create_model(canonical.id, **annotations)
        return model

    # =====================================================================
    # Internal: per-field adaptation
    # =====================================================================

    def _adapt_field(
        self,
        name: str,
        field_info: pydantic.fields.FieldInfo,
        *,
        model_cls: type,
    ) -> CanonicalField:
        """Adapt a single Pydantic field to :class:`CanonicalField`."""
        annotation = field_info.annotation
        if annotation is None:
            raise InvalidContractError(
                f"field {name!r} on {model_cls.__name__} has no annotation",
                error_code="INVALID_FIELD",
                context={"model": model_cls.__name__, "field_name": name},
            )
        # Strip ``Annotated[T, ...]`` and capture metadata. Metadata is
        # currently unused because Pydantic v2 stores constraints in
        # ``field_info.metadata`` directly (Pydantic itself unwraps the
        # Annotated when constructing FieldInfo), but we keep the call
        # for forward-compat with future Pydantic versions.
        unwrapped, _metadata = _unwrap_annotated(annotation)
        # Optional handling.
        is_optional, unwrapped = _is_optional(unwrapped)
        # Money subclass detection on the unwrapped type.
        field_type = _python_type_to_field_type(unwrapped)
        if field_type is None:
            raise InvalidContractError(
                f"field {name!r} on {model_cls.__name__} has unsupported type: {annotation!r}",
                error_code="UNSUPPORTED_FIELD_TYPE",
                context={
                    "model": model_cls.__name__,
                    "field_name": name,
                    "annotation": repr(annotation),
                },
            )
        # Determine default. Pydantic v2 has three "no default" forms:
        # ``default=PydanticUndefined`` (no default), ``default=None`` (explicit
        # None default), and ``default_factory=...`` (callable default). We
        # detect the presence of a default via ``is_required()`` (which is
        # ``False`` when either a default value OR a default_factory is set)
        # and prefer the value (when not PydanticUndefined) over the factory
        # for the canonical representation.
        default: typing.Any = None
        has_default_value = not field_info.is_required()
        if has_default_value and field_info.default is not PydanticUndefined:
            default = field_info.default
        # Determine enum_values if ENUM.
        enum_values: EnumValueSet | None = None
        if field_type is FieldType.ENUM:
            enum_values = self._enum_values_from_annotation(unwrapped, name=name, model=model_cls)
        # Build constraints from Field metadata.
        constraints: list[Constraint] = []
        constraints.extend(self._constraints_from_field(name, field_info, field_type, model_cls))
        # Extract format_hints from json_schema_extra (x-paxman-format-hints).
        format_hints = self._extract_format_hints(name, field_info, model_cls)
        # Stable field id.
        fid = f"field_{model_cls.__name__}_{name}"
        return CanonicalField(
            id=fid,
            path=name,
            name=name,
            type=field_type,
            required=not has_default_value and not is_optional,
            nullable=is_optional,
            description=field_info.description,
            default=default,
            constraints=tuple(constraints),
            enum_values=enum_values,
            format_hints=format_hints,
        )

    @staticmethod
    def _enum_values_from_annotation(
        annotation: typing.Any,
        *,
        name: str,
        model: type,
    ) -> EnumValueSet:
        """Build an :class:`EnumValueSet` from a Literal or Enum annotation."""
        origin = typing.get_origin(annotation)
        if origin is typing.Literal:
            values = typing.get_args(annotation)
            return EnumValueSet(values)
        if inspect.isclass(annotation) and issubclass(annotation, enum.Enum):
            return EnumValueSet(tuple(member.value for member in annotation))
        raise InvalidContractError(
            f"ENUM field {name!r} on {model.__name__} is not a Literal or Enum",
            error_code="INVALID_FIELD",
            context={"model": model.__name__, "field_name": name},
        )

    @staticmethod
    def _extract_format_hints(
        name: str,
        field_info: pydantic.fields.FieldInfo,
        model_cls: type,
    ) -> tuple[FormatHint, ...]:
        """Extract ``format_hints`` from a Pydantic ``Field``'s
        ``json_schema_extra`` extension.

        The Pydantic adapter accepts a list of strings (or
        :class:`FormatHint` members) under the
        ``x-paxman-format-hints`` extension key. Strings are
        resolved via :func:`resolve_format_hint`
        (member-agnostic). Duplicate values are deduplicated;
        order is preserved.

        Returns an empty tuple when the extension is absent.

        Raises:
            InvalidContractError: with ``error_code="INVALID_FORMAT_HINT"``
                if the extension value is not a list, or if any
                element is not a known format hint.
        """
        extra = field_info.json_schema_extra
        if extra is None:
            return ()
        if not isinstance(extra, dict):
            return ()
        raw_format_hints = extra.get("x-paxman-format-hints", [])
        if not isinstance(raw_format_hints, list):
            raise InvalidContractError(
                f"field {name!r} 'x-paxman-format-hints' must be a list, "
                f"got {type(raw_format_hints).__name__}",
                error_code="INVALID_FORMAT_HINT",
                context={"model": model_cls.__name__, "field_name": name},
            )
        out: list[FormatHint] = []
        seen: set[FormatHint] = set()
        for raw_h in raw_format_hints:
            try:
                hint = resolve_format_hint(raw_h)
            except (TypeError, ValueError) as exc:
                raise InvalidContractError(
                    f"field {name!r} has invalid format_hint {raw_h!r}: {exc}",
                    error_code="INVALID_FORMAT_HINT",
                    context={
                        "model": model_cls.__name__,
                        "field_name": name,
                        "raw": repr(raw_h),
                    },
                ) from exc
            if hint not in seen:
                seen.add(hint)
                out.append(hint)
        return tuple(out)

    def _constraints_from_field(
        self,
        name: str,
        field_info: pydantic.fields.FieldInfo,
        field_type: FieldType,
        model_cls: type,
    ) -> list[Constraint]:
        """Translate Pydantic ``Field`` metadata into :class:`Constraint` objects.

        Pydantic v2 stores per-field constraints in ``field_info.metadata``
        (a list of constraint objects) plus direct attributes for some
        things. We extract:

        - ``MinLen`` / ``MaxLen`` → ``MIN_LENGTH`` / ``MAX_LENGTH``
        - ``_PydanticGeneralMetadata`` with ``pattern`` → ``PATTERN``
        - direct attributes ``ge``, ``gt``, ``le``, ``lt`` → ``MIN_VALUE`` / ``MAX_VALUE``
        """
        out: list[Constraint] = []
        ctx = {"model": model_cls.__name__, "field_name": name}

        def _err(
            msg: str, code: str = "INVALID_CONSTRAINT", **extra: object
        ) -> InvalidContractError:
            return InvalidContractError(
                msg,
                error_code=code,
                context={**ctx, **extra},
            )

        # Length constraints from metadata.
        for meta in field_info.metadata:
            type_name = type(meta).__name__
            if type_name == "MinLen":
                out.append(
                    Constraint(
                        kind=ConstraintKind.MIN_LENGTH,
                        params={"min": int(meta.min_length)},
                    )
                )
            elif type_name == "MaxLen":
                out.append(
                    Constraint(
                        kind=ConstraintKind.MAX_LENGTH,
                        params={"max": int(meta.max_length)},
                    )
                )
            elif type_name == "_PydanticGeneralMetadata":
                pattern = getattr(meta, "pattern", None)
                if pattern is not None:
                    if not isinstance(pattern, str):
                        raise _err(
                            f"field {name!r} pattern must be a string",
                            code="INVALID_CONSTRAINT",
                            got_type=type(pattern).__name__,
                        )
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        raise _err(
                            f"field {name!r} pattern is invalid: {e}",
                            code="INVALID_REGEX_PATTERN",
                            regex=pattern,
                            parse_error=str(e),
                        ) from e
                    out.append(Constraint(kind=ConstraintKind.PATTERN, params={"regex": pattern}))
        # Numeric range from metadata (Ge, Gt, Le, Lt in Pydantic v2).
        if field_type in (FieldType.INTEGER, FieldType.DECIMAL, FieldType.MONEY):
            for meta in field_info.metadata:
                type_name = type(meta).__name__
                if type_name == "Ge":
                    out.append(
                        Constraint(
                            kind=ConstraintKind.MIN_VALUE,
                            params={"min": meta.ge, "inclusive": True},
                        )
                    )
                elif type_name == "Gt":
                    out.append(
                        Constraint(
                            kind=ConstraintKind.MIN_VALUE,
                            params={"min": meta.gt, "inclusive": False},
                        )
                    )
                elif type_name == "Le":
                    out.append(
                        Constraint(
                            kind=ConstraintKind.MAX_VALUE,
                            params={"max": meta.le, "inclusive": True},
                        )
                    )
                elif type_name == "Lt":
                    out.append(
                        Constraint(
                            kind=ConstraintKind.MAX_VALUE,
                            params={"max": meta.lt, "inclusive": False},
                        )
                    )
        return out

    # =====================================================================
    # Internal: per-field export
    # =====================================================================

    def _export_field(
        self,
        f: CanonicalField,
    ) -> tuple[typing.Any, typing.Any]:
        """Translate a :class:`CanonicalField` into a ``(annotation, default)`` tuple.

        ``default`` is a :class:`pydantic.Field` instance that carries the
        constraint metadata (``min_length``, ``max_length``, ``pattern``,
        ``ge``/``gt``/``le``/``lt``, ``description``). Pydantic's
        :func:`pydantic.create_model` accepts this tuple shape.
        """
        annotation = self._export_annotation(f)
        default: typing.Any = ...
        if f.default is not None:
            default = f.default
        elif f.nullable:
            default = None
        field_kwargs: dict[str, typing.Any] = {}
        if f.description is not None:
            field_kwargs["description"] = f.description
        for c in f.constraints:
            self._export_constraint_to_field(c, field_kwargs)
        if f.enum_values is not None:
            # Override annotation with a Literal of the allowed values.
            annotation = typing.Literal[tuple(f.enum_values)]
        return annotation, pydantic.Field(default=default, **field_kwargs)

    def _export_annotation(self, f: CanonicalField) -> typing.Any:
        """Map a :class:`CanonicalField`'s type back to a Pydantic annotation."""
        if f.nullable:
            base = self._export_annotation_non_optional(f)
            return base | None
        return self._export_annotation_non_optional(f)

    def _export_annotation_non_optional(self, f: CanonicalField) -> typing.Any:
        t = f.type
        if t is FieldType.STRING:
            return str
        if t is FieldType.INTEGER:
            return int
        if t is FieldType.DECIMAL:
            return Decimal
        if t is FieldType.BOOLEAN:
            return bool
        if t is FieldType.DATE:
            return datetime.date
        if t is FieldType.ENUM:
            if f.enum_values is None:
                raise InvalidContractError(
                    f"ENUM field {f.name!r} has no enum_values",
                    error_code="INVALID_FIELD",
                    context={"field_name": f.name},
                )
            return typing.Literal[tuple(f.enum_values)]
        if t is FieldType.OBJECT:
            return dict
        if t is FieldType.ARRAY:
            return list
        if t is FieldType.MONEY:
            return Money
        raise InvalidContractError(
            f"cannot export field {f.name!r} of type {t.name!r}",
            error_code="UNSUPPORTED_FIELD_TYPE",
            context={"field_name": f.name, "field_type": t.name},
        )

    @staticmethod
    def _export_constraint_to_field(c: Constraint, kwargs: dict[str, typing.Any]) -> None:
        """Add a Pydantic Field kwarg for the given constraint."""
        if c.kind is ConstraintKind.MIN_LENGTH:
            kwargs["min_length"] = c.params["min"]
        elif c.kind is ConstraintKind.MAX_LENGTH:
            kwargs["max_length"] = c.params["max"]
        elif c.kind is ConstraintKind.PATTERN:
            kwargs["pattern"] = c.params["regex"]
        elif c.kind is ConstraintKind.MIN_VALUE:
            inclusive = c.params.get("inclusive", True)
            if inclusive:
                kwargs["ge"] = c.params["min"]
            else:
                kwargs["gt"] = c.params["min"]
        elif c.kind is ConstraintKind.MAX_VALUE:
            inclusive = c.params.get("inclusive", True)
            if inclusive:
                kwargs["le"] = c.params["max"]
            else:
                kwargs["lt"] = c.params["max"]
        # ENUM, ISO_4217: not representable as Pydantic Field kwargs; ignored.
        elif c.kind in (ConstraintKind.ENUM, ConstraintKind.ISO_4217):
            pass


# Self-register.
def _register_on_import() -> None:
    from paxman.contract import registry

    registry.register(PydanticAdapter(), replace=True)


_register_on_import()

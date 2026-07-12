"""Canonical parsing for explicitly declared typed parse metadata.

The parse spec declares how a string-extracted candidate value should be
coerced to the field's declared type. It is an optional field-level
declaration that sits between extraction (Sprint 4) and reconciliation.

Only four parse kinds are supported in V1:

- ``integer``: base-10 signed integer text.
- ``decimal``: decimal text parsed without floats (via :class:`decimal.Decimal`).
- ``boolean``: an explicitly supplied, closed true/false token mapping.
- ``date``: an explicitly supplied ``strptime`` format.

No parser is inferred from a field name, description, raw input, locale,
or value shape.
"""

from __future__ import annotations

import types
import typing

import attrs

__all__ = [
    "ParseSpec",
    "ParseValidationError",
    "parse_spec",
]


# ---------------------------------------------------------------------------
# Supported kinds and their type-kind mapping
# ---------------------------------------------------------------------------

#: Map from FieldType name to the set of parse kinds allowed for that type.
_ALLOWED_KINDS: typing.Final[dict[str, frozenset[str]]] = {
    "INTEGER": frozenset({"integer"}),
    "DECIMAL": frozenset({"decimal"}),
    "BOOLEAN": frozenset({"boolean"}),
    "DATE": frozenset({"date"}),
}


class ParseValidationError(ValueError):
    """Raised when a field's parse declaration is invalid."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "INVALID_PARSE",
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.context: dict[str, object] = dict(context) if context else {}


def _freeze_config(config: object) -> types.MappingProxyType[str, object]:
    """Validate and make parse config immutable."""
    if not isinstance(config, typing.Mapping):
        raise TypeError(f"parse config must be a mapping, got {type(config).__name__}")
    if not all(isinstance(key, str) for key in config):
        raise TypeError("parse config keys must be strings")
    return types.MappingProxyType(dict(config))


@attrs.frozen(slots=True)
class ParseSpec:
    """One field-level parse declaration.

    A :class:`ParseSpec` declares how a string candidate value should
    be coerced to the field's declared type. The reconciler reads this
    from the canonical field and applies deterministic candidate
    preparation before eligibility filtering.

    Attributes:
        kind: The parse kind (``"integer"``, ``"decimal"``, ``"boolean"``,
            or ``"date"``).
        config: Kind-specific configuration. For ``boolean``: must contain
            ``true_values`` and ``false_values`` (disjoint lists of strings).
            For ``date``: must contain ``format`` (a ``strptime`` format
            string). For ``integer`` and ``decimal``: empty mapping.

    Examples:
        >>> ParseSpec(kind="decimal", config={})
        ParseSpec(kind='decimal', config={})
        >>> ParseSpec(kind="boolean", config={"true_values": ["yes"], "false_values": ["no"]})
        ParseSpec(kind='boolean', config=...)
    """

    kind: str = attrs.field()
    config: typing.Mapping[str, object] = attrs.field(converter=_freeze_config)

    def to_wire(self) -> dict[str, object]:
        """Return the stable contract wire form."""
        out: dict[str, object] = {"kind": self.kind}
        if self.config:
            out.update(self.config)
        return out


def parse_spec(
    raw: object,
    *,
    field_name: str,
    field_type: typing.Any,  # noqa: ANN401
) -> ParseSpec | None:
    """Parse a field's explicit parse declaration.

    The wire form is a mapping with ``kind`` and optional config keys.

    Args:
        raw: The raw parse declaration (``None``, a dict, or something
            else).
        field_name: The field name (for error messages).
        field_type: The :class:`~paxman.types.FieldType` of the field.

    Returns:
        A :class:`ParseSpec` or ``None`` when *raw* is ``None``.

    Raises:
        ParseValidationError: When the declaration is invalid.
    """
    if raw is None:
        return None

    ctx: dict[str, object] = {"field_name": field_name}

    if not isinstance(raw, typing.Mapping):
        raise ParseValidationError(
            f"field {field_name!r} 'parse' must be a mapping",
            error_code="INVALID_PARSE",
            context={**ctx, "raw_type": type(raw).__name__},
        )

    # --- kind ---
    kind = raw.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ParseValidationError(
            f"field {field_name!r} 'parse' is missing 'kind'",
            error_code="INVALID_PARSE",
            context=ctx,
        )

    # --- type/kind compatibility ---
    field_type_name = getattr(field_type, "name", str(field_type))
    allowed = _ALLOWED_KINDS.get(field_type_name)
    if allowed is None or kind not in allowed:
        raise ParseValidationError(
            f"field {field_name!r}: parse kind {kind!r} is not allowed for "
            f"{field_type_name} fields",
            error_code="INVALID_PARSE",
            context={**ctx, "kind": kind, "field_type": field_type_name},
        )

    # --- kind-specific config ---
    config: dict[str, object] = {}
    if kind == "boolean":
        config = _validate_boolean_config(raw, field_name=field_name)
    elif kind == "date":
        config = _validate_date_config(raw, field_name=field_name)
    # integer and decimal: no config required

    return ParseSpec(kind=kind, config=config)


def _validate_boolean_config(
    raw: typing.Mapping[str, object], *, field_name: str
) -> dict[str, object]:
    """Validate boolean parse config (true_values, false_values, disjoint)."""
    ctx: dict[str, object] = {"field_name": field_name, "kind": "boolean"}

    true_values = raw.get("true_values")
    if not isinstance(true_values, list) or not true_values:
        raise ParseValidationError(
            f"field {field_name!r}: boolean parse requires non-empty 'true_values' list",
            error_code="INVALID_PARSE",
            context=ctx,
        )
    for i, v in enumerate(true_values):
        if not isinstance(v, str) or not v:
            raise ParseValidationError(
                f"field {field_name!r}: true_values[{i}] must be a non-empty string",
                error_code="INVALID_PARSE",
                context={**ctx, "index": i},
            )

    false_values = raw.get("false_values")
    if not isinstance(false_values, list) or not false_values:
        raise ParseValidationError(
            f"field {field_name!r}: boolean parse requires non-empty 'false_values' list",
            error_code="INVALID_PARSE",
            context=ctx,
        )
    for i, v in enumerate(false_values):
        if not isinstance(v, str) or not v:
            raise ParseValidationError(
                f"field {field_name!r}: false_values[{i}] must be a non-empty string",
                error_code="INVALID_PARSE",
                context={**ctx, "index": i},
            )

    # Disjoint check.
    overlap = set(true_values) & set(false_values)
    if overlap:
        raise ParseValidationError(
            f"field {field_name!r}: true_values and false_values must be disjoint, "
            f"overlap: {sorted(overlap)!r}",
            error_code="INVALID_PARSE",
            context={**ctx, "overlap": sorted(overlap)},
        )

    return {"true_values": list(true_values), "false_values": list(false_values)}


def _validate_date_config(
    raw: typing.Mapping[str, object], *, field_name: str
) -> dict[str, object]:
    """Validate date parse config (format is required)."""
    fmt = raw.get("format")
    if not isinstance(fmt, str) or not fmt:
        raise ParseValidationError(
            f"field {field_name!r}: date parse requires a non-empty 'format' string",
            error_code="INVALID_PARSE",
            context={"field_name": field_name, "kind": "date"},
        )
    return {"format": fmt}

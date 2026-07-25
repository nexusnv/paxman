# src/paxman/_capabilities/geolocation/contract.py
"""Geolocation contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The geolocation contract declares the
datum, coordinate order, hemisphere requirement, output format, and precision
of the canonical coordinate form. There is no auto-detection: the caller
declares the policy; the capability applies it (Law 7 — Explicit Over Clever).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, cast

import attrs

from paxman._capabilities._shared.contract import (
    _authority_override_from_spec,
    authority_override_field,
    grammar_selector_converter,
    require_bool,
    require_v1,
    strip_authority_override,
    validate_bool,
    validate_v1,
)
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract

# The only geodetic datum Paxman recognizes in v1. WGS84 is the universal
# standard for GPS and web mapping; other datums (NAD27, GRS80, ...) are out
# of scope and must be declared explicitly by the caller, never guessed.
_DATUMS: frozenset[str] = frozenset({"WGS84"})

# The order in which latitude/longitude appear in the INPUT. This is a
# caller-provided policy declaring how to read the input axes; it does NOT
# affect the output. The canonicalizer always emits the canonical form as
# "latitude,longitude" regardless of coordinate_order.
_COORDINATE_ORDERS: frozenset[str] = frozenset({"lat_lon", "lon_lat"})

# The only output format Paxman emits in v1. Decimal degrees is the canonical
# numeric form; DMS / DMM are out of scope.
_OUTPUT_FORMATS: frozenset[str] = frozenset({"decimal"})

# Precision (decimal places) bounds. 0..12 covers sub-millimeter resolution at
# the equator while staying within float64 string round-trip safety for the
# canonicalizer. Out-of-range precision is a contract error, not a silent clamp.
_PRECISION_MIN: int = 0
_PRECISION_MAX: int = 12


def _make_str_in_validator(allowed: frozenset[str]) -> Callable[[object, object, str], None]:
    """Build an attrs validator that checks `value` is a member of `allowed`."""

    def _validator(inst: object, attr: object, value: str) -> None:
        if not isinstance(value, str) or value not in allowed:
            name = getattr(attr, "name", attr)
            raise ContractError(
                f"contract field {name!r} must be one of {sorted(allowed)}, got {value!r}"
            )

    return _validator


def _validate_precision(inst: object, attr: object, value: object) -> None:
    """Attrs validator: precision must be an int in 0..12 (Law 7 — explicit)."""
    if not isinstance(value, int) or isinstance(value, bool):
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be an int in {_PRECISION_MIN}..{_PRECISION_MAX}, "
            f"got {value!r}"
        )
    if value < _PRECISION_MIN or value > _PRECISION_MAX:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be in {_PRECISION_MIN}..{_PRECISION_MAX}, got {value}"
        )


def _validate_output_format_geolocation(inst: object, attr: object, value: object) -> None:
    """Attrs validator: output_format must be one of the supported formats."""
    _SUPPORTED = frozenset({"decimal"})
    if not isinstance(value, str) or value not in _SUPPORTED:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be one of {sorted(_SUPPORTED)}, got {value!r}"
        )


@attrs.frozen
class CanonicalGeolocationContract:
    """The geolocation contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    There is no `auto_detect`. The caller declares the datum, coordinate order,
    hemisphere requirement, output format, and precision; the capability applies
    them. Validators enforce the invariants on every construction path (factory,
    Dict DSL, and direct instantiation) so a broken contract fails before
    canonicalization.
    """

    datum: str = attrs.field(default="WGS84", validator=_make_str_in_validator(_DATUMS))
    coordinate_order: str = attrs.field(
        default="lat_lon", validator=_make_str_in_validator(_COORDINATE_ORDERS)
    )
    require_hemisphere: bool = attrs.field(default=True, validator=validate_bool)
    output_format: Literal["decimal"] = attrs.field(
        default="decimal", validator=_validate_output_format_geolocation
    )
    precision: int = attrs.field(default=6, validator=_validate_precision)
    kind: str = attrs.field(
        default="canonical_geolocation",
        validator=attrs.validators.matches_re(r"^canonical_geolocation$"),
    )
    version: int = attrs.field(default=1, validator=validate_v1)
    version_field: int = attrs.field(default=1, validator=validate_v1)

    include_grammar: tuple[str, ...] = attrs.field(default=(), converter=grammar_selector_converter)
    exclude_grammar: tuple[str, ...] = attrs.field(default=(), converter=grammar_selector_converter)

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract."""
        return strip_authority_override(
            {
                "kind": self.kind,
                "datum": self.datum,
                "coordinate_order": self.coordinate_order,
                "require_hemisphere": self.require_hemisphere,
                "output_format": self.output_format,
                "precision": self.precision,
                "version": self.version,
                "version_field": self.version_field,
                "include_grammar": self.include_grammar,
                "exclude_grammar": self.exclude_grammar,
            }
        )


def Geolocation(
    *,
    datum: str = "WGS84",
    coordinate_order: str = "lat_lon",
    require_hemisphere: bool = True,
    output_format: Literal["decimal"] = "decimal",
    precision: int = 6,
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalGeolocationContract:
    """Domain-type sugar: declare a geolocation contract in user vocabulary.

    There is NO auto-detection (Law 7 — Explicit Over Clever). Every lever is an
    explicit, declared value; Paxman never infers the datum, coordinate order,
    or hemisphere from the input.

    Args:
        datum: Geodetic datum of the coordinates. Only "WGS84" is supported in
            v1. Default "WGS84".
        coordinate_order: Order of latitude/longitude in the INPUT only. One
            of "lat_lon" or "lon_lat". The canonical output is always emitted as
            "latitude,longitude" regardless of this setting. Default "lat_lon".
        require_hemisphere: Require an explicit hemisphere sign (or N/S/E/W) on
            each coordinate so the canonical form is unambiguous. Default True.
        output_format: Canonical output format. Only "decimal" (decimal degrees)
            is supported in v1. Default "decimal".
        precision: Number of decimal places in the canonical output. Must be an
            int in 0..12. Default 6.

    Returns:
        A frozen CanonicalGeolocationContract instance.

    Raises:
        ContractError: if `datum`, `coordinate_order`, or `output_format` is not
            a recognized value, or if `precision` is not an int in 0..12, or if a
            flag argument is not a bool.
    """
    output_format = cast(
        Literal["decimal"],
        _require_str_in("output_format", output_format, _OUTPUT_FORMATS),
    )
    return CanonicalGeolocationContract(
        datum=_require_str_in("datum", datum, _DATUMS),
        coordinate_order=_require_str_in("coordinate_order", coordinate_order, _COORDINATE_ORDERS),
        require_hemisphere=require_bool("require_hemisphere", require_hemisphere),
        output_format=output_format,
        precision=_require_precision("precision", precision),
        include_grammar=include_grammar,
        exclude_grammar=exclude_grammar,
        authority_override=authority_override,
    )


def _require_str_in(field: str, value: object, allowed: frozenset[str]) -> str:
    """Validate that a contract field is a member of `allowed` (Law 7)."""
    if not isinstance(value, str) or value not in allowed:
        raise ContractError(
            f"contract field {field!r} must be one of {sorted(allowed)}, got {value!r}"
        )
    return value


def _require_precision(field: str, value: object) -> int:
    """Validate that a contract precision field is an int in 0..12 (Law 7)."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractError(
            f"contract field {field!r} must be an int in {_PRECISION_MIN}..{_PRECISION_MAX}, "
            f"got {value!r}"
        )
    if value < _PRECISION_MIN or value > _PRECISION_MAX:
        raise ContractError(
            f"contract field {field!r} must be in {_PRECISION_MIN}..{_PRECISION_MAX}, got {value}"
        )
    return value


def _build_geolocation(spec: dict[str, Any]) -> CanonicalGeolocationContract:
    require_v1("version", spec.get("version", 1))
    require_v1("version_field", spec.get("version_field", 1))
    output_format = cast(
        Literal["decimal"],
        _require_str_in("output_format", spec.get("output_format", "decimal"), _OUTPUT_FORMATS),
    )
    return CanonicalGeolocationContract(
        datum=_require_str_in("datum", spec.get("datum", "WGS84"), _DATUMS),
        coordinate_order=_require_str_in(
            "coordinate_order", spec.get("coordinate_order", "lat_lon"), _COORDINATE_ORDERS
        ),
        require_hemisphere=require_bool("require_hemisphere", spec.get("require_hemisphere", True)),
        output_format=output_format,
        precision=_require_precision("precision", spec.get("precision", 6)),
        include_grammar=spec.get("include_grammar", ()),
        exclude_grammar=spec.get("exclude_grammar", ()),
        authority_override=_authority_override_from_spec(spec),
    )


register_contract("canonical_geolocation", _build_geolocation)

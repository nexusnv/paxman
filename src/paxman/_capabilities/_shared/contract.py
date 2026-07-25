"""Shared contract plumbing for authority-override, validators, and grammar selectors.

The following cross-cutting concerns were verbatim-duplicated across all 10
capability contracts. This module centralizes them so they cannot drift apart:

- :func:`authority_override_field` — the ``attrs.field`` declaration.
- :func:`_authority_override_from_spec` — the DSL ``spec`` read.
- :func:`strip_authority_override` — the ``as_dict`` exclusion.
- :func:`validate_bool` — attrs validator: policy fields must be real bools.
- :func:`validate_v1` — attrs validator: version fields must be int 1.
- :func:`require_bool` — factory helper: validate and return a bool.
- :func:`require_v1` — factory helper: validate and return int 1.
- :func:`make_output_format_validator` — factory for output_format validators.
- :func:`grammar_selector_converter` — converter for include/exclude grammar fields.

All reference the single :data:`_AUTHORITY_OVERRIDE_KEY` constant.
``engine.py`` reads the field as a typed attribute on the ``Contract`` Protocol
(``parsed_contract.authority_override``); no ``getattr`` fallback remains.
"""

from __future__ import annotations

from typing import Any

import attrs

from paxman._errors import ContractError

#: The Dict-DSL key for the authority-override escape hatch. The single source
#: of truth referenced by both :func:`_authority_override_from_spec` (the DSL
#: read) and :func:`strip_authority_override` (the ``as_dict`` exclusion), so
#: the two cannot drift apart across domains.
_AUTHORITY_OVERRIDE_KEY = "authority_override"


# ---------------------------------------------------------------------------
# Authority override (Concern 3)
# ---------------------------------------------------------------------------


def authority_override_field() -> Any:
    """Return the ``attrs.field`` declaration for the ``authority_override`` escape hatch.

    Identical semantics to the previously copy-pasted field: default ``None``,
    excluded from ``repr``/``eq``/``hash`` so the override never affects
    identity or the ``replay_hash``.
    """
    return attrs.field(default=None, repr=False, eq=False, hash=False)


def _authority_override_from_spec(spec: dict[str, Any]) -> Any | None:
    """Read the authority-override from a Dict-DSL ``spec`` (defaults to ``None``).

    Route every contract's ``_build_<kind>`` through this so the key is read
    consistently — this also fixes the ``boolean`` contract, whose builder
    previously dropped the override silently.
    """
    return spec.get(_AUTHORITY_OVERRIDE_KEY, None)


def strip_authority_override(payload: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` without the authority-override escape-hatch key.

    Every contract's ``as_dict()`` routes its dict literal through this helper
    so the override never enters the canonical Dict-DSL form (canonical-form
    parity / replay determinism). Even if a future contract author accidentally
    includes ``authority_override`` in the dict literal, this function strips it
    using :data:`_AUTHORITY_OVERRIDE_KEY` — the exclusion is mechanical, not
    aspirational.

    The input dict is mutated in place (``dict.pop``) and returned; callers pass
    a freshly constructed dict literal so mutation is safe and avoids a copy.
    """
    payload.pop(_AUTHORITY_OVERRIDE_KEY, None)
    return payload


# ---------------------------------------------------------------------------
# Validators (mandate Law 7 — Explicit Over Clever)
# ---------------------------------------------------------------------------


def validate_bool(inst: object, attr: object, value: object) -> None:
    """Attrs validator: policy fields must be real bools (Law 7 — explicit).

    Use as ``validator=validate_bool`` on ``attrs.field`` declarations.
    Non-bool values (including truthy strings) raise ``ContractError``.
    """
    if not isinstance(value, bool):
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be a bool, got {type(value).__name__}")


def validate_v1(inst: object, attr: object, value: object) -> None:
    """Attrs validator: version fields must be int 1 (only v1 is supported).

    Use as ``validator=validate_v1`` on ``attrs.field`` declarations.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be int 1, got {value!r}")


def require_bool(field: str, value: object) -> bool:
    """Validate that a contract field is a real bool (Law 7 — explicit).

    Returns the validated bool. Use in factory functions and ``_build_*``
    helpers where an attrs validator cannot run.
    """
    if not isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be a bool, got {type(value).__name__}")
    return value


def require_v1(field: str, value: object) -> int:
    """Validate that a contract version field is the supported v1 (Law 7).

    Returns the validated int. Use in factory functions and ``_build_*``
    helpers where an attrs validator cannot run.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be int 1, got {type(value).__name__}")
    if value != 1:
        raise ContractError(
            f"contract field {field!r} must be 1 (only v1 is supported), got {value}"
        )
    return value


def make_output_format_validator(allowed: frozenset[str]) -> Any:
    """Build an attrs validator that checks ``value`` is a member of ``allowed``.

    Returns a validator function suitable for ``attrs.field(validator=...)``.
    Each capability defines its own supported formats frozenset and passes it
    here to avoid duplicating the validator boilerplate.
    """

    def _validator(inst: object, attr: object, value: object) -> None:
        if not isinstance(value, str) or value not in allowed:
            name = getattr(attr, "name", attr)
            raise ContractError(
                f"contract field {name!r} must be one of {sorted(allowed)}, got {value!r}"
            )

    return _validator


# ---------------------------------------------------------------------------
# Grammar selector converter (include_grammar / exclude_grammar)
# ---------------------------------------------------------------------------


def grammar_selector_converter(value: tuple[str, ...] | list[str] | str | None) -> tuple[str, ...]:
    """Convert and validate grammar selector input to an immutable tuple of strings.

    Accepts tuples, lists, a single string (treated as one element), or ``None``.
    Raises ``ContractError`` for invalid inputs (non-string elements, non-sequence
    types). Used as an ``attrs.field(converter=...)`` on ``include_grammar`` and
    ``exclude_grammar`` across all 10 capability contracts.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        # A bare string is almost certainly a user mistake — they meant ("string",)
        raise ContractError(
            f"grammar selector must be a sequence of strings, not a bare string: {value!r}; "
            f"use ({value!r},) instead"
        )
    if not isinstance(value, (list, tuple)):
        raise ContractError(
            f"grammar selector must be a sequence of strings, got {type(value).__name__}"
        )
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ContractError(
                f"grammar selector element {i!r} must be a string, got {type(item).__name__}"
            )
    return tuple(value)

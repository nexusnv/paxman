"""Shared contract plumbing for the authority-override escape hatch (Concern 3).

The ``authority_override`` field, its factory param, the DSL ``spec`` read, and
the ``as_dict`` exclusion were verbatim-duplicated across all 10 capability
contracts. The field is a cross-cutting concern with zero domain logic; this
module centralizes all three so they cannot drift apart:

- :func:`authority_override_field` — the ``attrs.field`` declaration.
- :func:`_authority_override_from_spec` — the DSL ``spec`` read.
- :func:`strip_authority_override` — the ``as_dict`` exclusion.

All three reference the single :data:`_AUTHORITY_OVERRIDE_KEY` constant.
``engine.py`` reads the field as a typed attribute on the ``Contract`` Protocol
(``parsed_contract.authority_override``); no ``getattr`` fallback remains.
"""

from __future__ import annotations

from typing import Any

import attrs

#: The Dict-DSL key for the authority-override escape hatch. The single source
#: of truth referenced by both :func:`_authority_override_from_spec` (the DSL
#: read) and :func:`strip_authority_override` (the ``as_dict`` exclusion), so
#: the two cannot drift apart across domains.
_AUTHORITY_OVERRIDE_KEY = "authority_override"


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

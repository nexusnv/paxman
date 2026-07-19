"""Shared contract plumbing for the authority-override escape hatch (Concern 3).

The ``authority_override`` field, its factory param, and the DSL ``spec`` read
were verbatim-duplicated across all 10 capability contracts (41 occurrences).
The field is a cross-cutting concern with zero domain logic; this module
centralizes the field factory and the DSL read so a new contract declares the
field in one line and routes its DSL builder through one helper. The shared
``_AUTHORITY_OVERRIDE_KEY`` constant is the single source of truth that the
per-contract ``as_dict`` exclusion and the DSL read both reference, so they
cannot drift apart. ``engine.py`` still reads the field via ``getattr``
(Candidate 3 will type it); this module only removes the copy-paste.
"""

from __future__ import annotations

from typing import Any

import attrs

#: The Dict-DSL key for the authority-override escape hatch. Centralized so the
#: ``as_dict`` exclusion and the DSL read cannot drift apart across domains.
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

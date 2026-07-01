"""Constraint-checking helper shared by the capabilities v1 package
and the reconciler. This is the canonical location; the previous
private copy in :mod:`paxman.capabilities.v1.validation` is now a
re-export shim.
"""

from __future__ import annotations

import re
import typing

from paxman.contract._types import Constraint, ConstraintKind

__all__ = ["check_constraint"]


#: ISO-4217 currency code pattern. Three uppercase ASCII letters.
_ISO_4217_PATTERN: typing.Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}$")


def _to_float(value: object) -> float | None:
    """Convert *value* to ``float``; return ``None`` on failure.

    Accepts ``int``, ``float``, ``str`` (decimal), and any
    :class:`numbers.Real` (via :func:`float`). Returns ``None``
    for non-numeric values so the caller can produce a clear
    diagnostic.
    """
    if isinstance(value, bool):
        return None  # bool is technically numeric; reject to avoid surprises
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_length(value: object) -> int | None:
    """Return the length of *value*; ``None`` if it has no length.

    Accepts ``str``, ``bytes``, ``list``, ``tuple``, ``dict``, and
    any other :class:`collections.abc.Sized` (via :func:`len`).
    Returns ``None`` for non-sized values so the caller can produce
    a clear diagnostic.
    """
    from collections.abc import Sized

    if isinstance(value, Sized):
        return len(value)
    return None


def check_constraint(c: Constraint, value: object) -> tuple[bool, str]:
    """Run a single constraint check.

    Args:
        c: A :class:`Constraint`.
        value: The value to check.

    Returns:
        ``(True, "")`` on pass, ``(False, reason)`` on fail. For
        kinds with no V1 implementation, returns ``(True, "")``
        (no-op) so the caller does not block on a missing check.

    This function was extracted from
    :mod:`paxman.capabilities.v1.validation._check_constraint` to fix
    issue #64 (reconciler was importing a private name).
    """
    kind = c.kind
    params = c.params

    if kind is ConstraintKind.MIN_LENGTH:
        n = _to_length(value)
        if n is None:
            return False, "value has no length"
        if n < int(params.get("min", 0)):
            return False, f"length {n} < min {params.get('min')}"
        return True, ""

    if kind is ConstraintKind.MAX_LENGTH:
        n = _to_length(value)
        if n is None:
            return False, "value has no length"
        if n > int(params.get("max", 0)):
            return False, f"length {n} > max {params.get('max')}"
        return True, ""

    if kind is ConstraintKind.PATTERN:
        if not isinstance(value, str):
            return False, f"value is not a string (got {type(value).__name__})"
        regex = params.get("regex")
        if not isinstance(regex, str):
            return False, "PATTERN constraint has no 'regex' param"
        try:
            if not re.search(regex, value):
                return False, f"value does not match pattern {regex!r}"
        except re.error as e:
            return False, f"invalid regex {regex!r}: {e}"
        return True, ""

    if kind is ConstraintKind.MIN_VALUE:
        n_f = _to_float(value)
        if n_f is None:
            return False, f"value is not numeric (got {type(value).__name__})"
        min_v = float(params.get("min", 0))
        if n_f < min_v:
            return False, f"value {value!r} < min {params.get('min')}"
        return True, ""

    if kind is ConstraintKind.MAX_VALUE:
        n2 = _to_float(value)
        if n2 is None:
            return False, f"value is not numeric (got {type(value).__name__})"
        max_v = float(params.get("max", 0))
        if n2 > max_v:
            return False, f"value {value!r} > max {params.get('max')}"
        return True, ""

    if kind is ConstraintKind.ENUM:
        values = params.get("values", ())
        if not isinstance(values, (tuple, list)):
            return False, "ENUM constraint has no 'values' list"
        if value not in values:
            return False, f"value {value!r} not in enum {list(values)!r}"
        return True, ""

    if kind is ConstraintKind.ISO_4217:
        if not isinstance(value, str) or not _ISO_4217_PATTERN.match(value):
            return False, f"value {value!r} is not a valid ISO-4217 code"
        return True, ""

    # Unknown constraint kinds: no-op (V1: should not happen; the
    # validator catches unknown kinds at the contract layer).
    return True, ""

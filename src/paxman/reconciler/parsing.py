"""Deterministic candidate preparation (typed parsing) for the Reconciler.

This module sits between candidate extraction (Executor) and eligibility
filtering (Reconciler). It converts string values extracted by
capabilities into their declared types (INTEGER, DECIMAL, BOOLEAN, DATE)
according to the caller's :class:`~paxman.contract._parse.ParseSpec`.

Invariants
----------

- **Never assigns confidence.** That is the Reconciler's exclusive
  responsibility (ADR-0005).
- **Never reads raw input.** It only reads :class:`Candidate` records
  and the canonical field's :class:`ParseSpec`.
- **Deterministic.** Same candidates + same ParseSpec → same output.
- **Pure function.** No side effects, no I/O, no clock reads.

Failure semantics
-----------------

When a candidate's string value cannot be parsed according to the
ParseSpec (e.g., ``"twelve"`` for an INTEGER field), the candidate
is **dropped** (not included in the output). The caller receives an
empty tuple for that field's candidates, which surfaces as
``UNRESOLVED`` in the final artifact.

Non-string values (e.g., an integer already typed by the capability)
are passed through unchanged — the parser only acts on strings.
"""

from __future__ import annotations

import datetime
import typing

from paxman.capabilities.result import Candidate
from paxman.contract._parse import ParseSpec
from paxman.contract.canonical import CanonicalField
from paxman.reconciler.money import parse_decimal

__all__ = ["prepare_candidates"]


def prepare_candidates(
    candidates: tuple[Candidate, ...],
    field: CanonicalField,
) -> tuple[Candidate, ...]:
    """Convert candidate string values to their declared types.

    For each candidate, if the value is a string, parse it according
    to the field's :class:`ParseSpec`. If parsing fails, the candidate
    is dropped. If the value is not a string, it is passed through
    unchanged.

    Args:
        candidates: The candidates extracted by the Executor.
        field: The canonical field with its ``parse_spec``.

    Returns:
        A tuple of candidates with parsed (typed) values. May be
        shorter than the input if some candidates failed parsing.
        If ``field.parse_spec`` is ``None``, all candidates pass
        through unchanged.

    Raises:
        TypeError: If inputs are of the wrong type.
    """
    if not isinstance(candidates, tuple):
        raise TypeError(f"candidates must be a tuple, got {type(candidates).__name__}")
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")

    parse_spec = field.parse_spec
    if parse_spec is None:
        return candidates

    prepared: list[Candidate] = []
    for candidate in candidates:
        value = candidate.value
        # Non-string values pass through unchanged.
        if not isinstance(value, str):
            prepared.append(candidate)
            continue
        parsed = _parse_value(value, parse_spec)
        if parsed is not _SENTINEL:
            prepared.append(
                Candidate(
                    value=parsed,
                    evidence_refs=candidate.evidence_refs,
                    diagnostics=candidate.diagnostics,
                )
            )
    return tuple(prepared)


# Sentinel for failed parsing (distinct from None, which is a valid parsed value).
_SENTINEL: typing.Final[object] = object()


def _parse_value(text: str, spec: ParseSpec) -> typing.Any:
    """Parse a text value according to a ParseSpec.

    Returns ``_SENTINEL`` on failure (so the caller can drop the candidate).
    """
    kind = spec.kind
    config = spec.config

    if kind == "integer":
        return _parse_integer(text)
    if kind == "decimal":
        return _parse_decimal(text)
    if kind == "boolean":
        return _parse_boolean(text, config)
    if kind == "date":
        return _parse_date(text, config)
    # Unknown kind — should not happen (ParseSpec validates), but be defensive.
    return _SENTINEL


def _parse_integer(text: str) -> typing.Any:
    """Parse an integer string."""
    try:
        return int(text)
    except (ValueError, TypeError):
        return _SENTINEL


def _parse_decimal(text: str) -> typing.Any:
    """Parse a decimal string via the reconciler's money module."""
    try:
        return parse_decimal(text)
    except Exception:
        return _SENTINEL


def _parse_boolean(text: str, config: typing.Mapping[str, object]) -> typing.Any:
    """Parse a boolean string using configured true/false values."""
    true_values = config.get("true_values", [])
    false_values = config.get("false_values", [])
    text_lower = text.lower()
    if isinstance(true_values, list) and text_lower in {v.lower() for v in true_values if isinstance(v, str)}:
        return True
    if isinstance(false_values, list) and text_lower in {v.lower() for v in false_values if isinstance(v, str)}:
        return False
    return _SENTINEL


def _parse_date(text: str, config: typing.Mapping[str, object]) -> typing.Any:
    """Parse a date string using the configured strptime format."""
    fmt = config.get("format")
    if not isinstance(fmt, str):
        return _SENTINEL
    try:
        datetime.datetime.strptime(text, fmt)
    except (ValueError, TypeError):
        return _SENTINEL
    return text

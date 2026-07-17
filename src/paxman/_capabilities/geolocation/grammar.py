# src/paxman/_capabilities/geolocation/grammar.py
"""Geolocation grammar recognition layer (Layer 1 of the geolocation architecture).

Recognition classifies the raw (whitespace-trimmed) input into one of a small
set of anchored shapes (geo_decimal_pair / geo_decimal_hemi / geo_dms /
geo_dms_signed). It assigns NO canonical meaning — the resolver
(canonicalizer.generate_interpretations) performs the actual parse and applies
the contract policy. Recognition is a deterministic predicate only (Law 4).

Law 14: every grammar carries a `source` (provenance) for the shape it
recognises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal

import attrs


@attrs.frozen
class Grammar:
    """A single geolocation grammar: a regex pattern plus provenance."""

    id: str
    source: str
    pattern: str
    compiled: re.Pattern[str]
    shape: str | None = None


@attrs.frozen
class RecognizedRep:
    """A single grammar match: raw string captures, no semantic meaning."""

    grammar_id: str
    source: str
    raw: str
    shape: str | None
    captures: Mapping[str, str]


def _make_grammar(id: str, source: str, pattern: str, shape: str | None = None) -> Grammar:
    return Grammar(
        id=id,
        source=source,
        pattern=pattern,
        compiled=re.compile(pattern),
        shape=shape,
    )


_GRAMMAR_SOURCE = "paxman spec/geolocation §3.1 (closed coordinate shape vocabulary)"

# A numeric axis: optional sign, digits, optional decimal point. Tolerant of
# leading/trailing whitespace around each token (handled by the resolver's
# trim step). The resolver is the authority on validity (catches malformed
# input as INVALID, never guessed). The parenthesized pair form wraps the SAME
# _NUM in a balanced "(...)" so the opening and closing delimiters must both be
# present (a single delimiter cannot fullmatch and is rejected).
_NUM = r"(?P<a1>[-+]?\d+(?:\.\d+)?)\s*,\s*(?P<a2>[-+]?\d+(?:\.\d+)?)"

# Anchored shape classifiers. These only ROUTE to the resolver; the resolver
# applies the contract policy (axis order, hemisphere, precision) and validates
# ranges. The patterns are intentionally permissive on the numeric body; the
# resolver rejects malformed input as INVALID.
GRAMMARS: tuple[Grammar, ...] = (
    # geo_decimal_pair has TWO grammars sharing one shape: a bare pair and a
    # fully parenthesized pair. Each defines the a1/a2 groups in its OWN
    # pattern (not an alternation) so the names are not redefined. A single
    # delimiter — "(lat, lon" or "lat, lon)" — matches neither and is rejected.
    _make_grammar(
        "geo_decimal_pair",
        _GRAMMAR_SOURCE,
        r"^\s*" + _NUM + r"\s*$",
        shape="geo_decimal_pair",
    ),
    _make_grammar(
        "geo_decimal_pair_paren",
        _GRAMMAR_SOURCE,
        r"^\(\s*" + _NUM + r"\s*\)$",
        shape="geo_decimal_pair",
    ),
    _make_grammar(
        "geo_decimal_hemi",
        _GRAMMAR_SOURCE,
        r"^(?P<a1>[-+]?\d+(?:\.\d+)?)\s*(?P<h1>[NS])\s*"
        r"(?P<a2>[-+]?\d+(?:\.\d+)?)\s*(?P<h2>[EW])$",
        shape="geo_decimal_hemi",
    ),
    _make_grammar(
        "geo_decimal_hemi_lonlat",
        _GRAMMAR_SOURCE,
        # Longitude-first letter order (E/W then N/S) for coordinate_order="lon_lat".
        # Captures keep h1 = first letter (longitude), h2 = second (latitude) so
        # the resolver's coordinate_order swap maps them correctly.
        r"^(?P<a1>[-+]?\d+(?:\.\d+)?)\s*(?P<h1>[EW])\s*"
        r"(?P<a2>[-+]?\d+(?:\.\d+)?)\s*(?P<h2>[NS])$",
        shape="geo_decimal_hemi",
    ),
    _make_grammar(
        "geo_dms",
        _GRAMMAR_SOURCE,
        r"^(?P<d1>\d+(?:\.\d+)?)\s*[°]\s*(?P<m1>\d+(?:\.\d+)?)\s*[']\s*"
        r'(?P<s1>\d+(?:\.\d+)?)\s*["°]\s*(?P<h1>[NS])\s*'
        r"(?P<d2>\d+(?:\.\d+)?)\s*[°]\s*(?P<m2>\d+(?:\.\d+)?)\s*[']\s*"
        r'(?P<s2>\d+(?:\.\d+)?)\s*["°]\s*(?P<h2>[EW])$',
        shape="geo_dms",
    ),
    _make_grammar(
        "geo_dms_lonlat",
        _GRAMMAR_SOURCE,
        # Longitude-first letter order (E/W then N/S) for coordinate_order="lon_lat".
        # d1/m1/s1/h1 are longitude components; d2/m2/s2/h2 are latitude. The
        # resolver's coordinate_order swap maps h1 (=E/W) to longitude correctly.
        r"^(?P<d1>\d+(?:\.\d+)?)\s*[°]\s*(?P<m1>\d+(?:\.\d+)?)\s*[']\s*"
        r'(?P<s1>\d+(?:\.\d+)?)\s*["°]\s*(?P<h1>[EW])\s*'
        r"(?P<d2>\d+(?:\.\d+)?)\s*[°]\s*(?P<m2>\d+(?:\.\d+)?)\s*[']\s*"
        r'(?P<s2>\d+(?:\.\d+)?)\s*["°]\s*(?P<h2>[NS])$',
        shape="geo_dms",
    ),
    _make_grammar(
        "geo_dms_signed",
        _GRAMMAR_SOURCE,
        r"^(?P<d1>[-+]?\d+(?:\.\d+)?)\s+(?P<m1>\d+(?:\.\d+)?)\s+(?P<s1>[-+]?\d+(?:\.\d+)?)"
        r"\s*,\s*"
        r"(?P<d2>[-+]?\d+(?:\.\d+)?)\s+(?P<m2>\d+(?:\.\d+)?)\s+(?P<s2>[-+]?\d+(?:\.\d+)?)$",
        shape="geo_dms_signed",
    ),
)


def _split_sign(raw: str) -> tuple[str, str]:
    """Strip surrounding parentheses and extract a leading sign.

    Returns a ``(sign, body)`` pair where ``sign`` is ``"-"`` or ``"+"``
    (``"+"`` when no explicit sign is present) and ``body`` is the numeric
    text with any enclosing parentheses removed. Mirrors money's sign
    handling: a parenthesized value ``(40.7128)`` is a negative, and a bare
    ``-74.0060`` keeps its explicit sign.

    Args:
        raw: The raw numeric token (possibly parenthesized, possibly signed).

    Returns:
        A 2-tuple of ``(sign, body)`` strings.
    """
    text = raw.strip()
    sign = "+"
    if text.startswith("(") and text.endswith(")"):
        sign = "-"
        text = text[1:-1].strip()
    if text.startswith("-"):
        sign = "-"
        text = text[1:].strip()
    elif text.startswith("+"):
        sign = "+"
        text = text[1:].strip()
    return sign, text


def _parse_number(text: str) -> Decimal:
    """Parse a numeric token into an exact ``Decimal`` (never ``float``).

    Args:
        text: The numeric text (digits, optional decimal point).

    Returns:
        The exact ``Decimal`` value of ``text``.

    Raises:
        ValueError: if ``text`` is not a finite decimal number.
    """
    value = Decimal(text)
    if not value.is_finite():
        raise ValueError(f"non-finite coordinate value: {text!r}")
    return value


def recognize(value: str) -> RecognizedRep | None:
    """Recognise the geolocation shape the (already-trimmed) input matches.

    Returns the first RecognizedRep whose regex FULLMATCHES the input, or
    ``None`` when the input names no known geolocation shape. Each rep carries
    the grammar's ``source`` (Law 14) and only RAW string captures — no
    semantic meaning is assigned here.

    Args:
        value: The raw (already whitespace-trimmed) input string.

    Returns:
        A RecognizedRep for the first matching shape, or ``None`` when no
        known shape matches.
    """
    for grammar in GRAMMARS:
        match = grammar.compiled.fullmatch(value)
        if match is None:
            continue
        captures = {k: v for k, v in match.groupdict().items() if v is not None}
        return RecognizedRep(
            grammar_id=grammar.id,
            source=grammar.source,
            raw=match.group(0),
            shape=grammar.shape,
            captures=captures,
        )
    return None

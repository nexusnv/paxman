# src/paxman/_capabilities/country/grammar.py
"""Country recognition grammar (Layer 1 of the country architecture).

Recognition classifies the (whitespace-trimmed) raw input into one of a small
closed set of anchored shapes (alpha2 / alpha3 / name). It assigns NO canonical
meaning — the resolver (canonicalizer.generate_interpretations) performs the
table lookup. Recognition is a deterministic predicate only (Law 4).

Law 14: every grammar carries a `source` (provenance) for the shape it
recognises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import attrs


@attrs.frozen
class Grammar:
    """A single country grammar: a regex pattern plus provenance."""

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


_GRAMMAR_SOURCE = "paxman spec/country §3.2 (closed country shape vocabulary)"

GRAMMARS: tuple[Grammar, ...] = (
    _make_grammar("country_alpha2", _GRAMMAR_SOURCE, r"^(?P<tok>[A-Za-z]{2})$", shape="alpha2"),
    _make_grammar("country_alpha3", _GRAMMAR_SOURCE, r"^(?P<tok>[A-Za-z]{3})$", shape="alpha3"),
    # Numeric (ISO 3166-1 M49) shape: 1-3 ASCII digits. Added as its own shape
    # so the resolver routes it to the numeric table. The name grammar below is
    # narrowed to exclude pure-digit strings so a numeric token matches ONLY
    # this grammar (never both numeric and name).
    _make_grammar("country_numeric", _GRAMMAR_SOURCE, r"^(?P<tok>\d{1,3})$", shape="numeric"),
    # Name shape: any non-empty trimmed token that is not exactly 2 or 3 ASCII
    # letters and is not a pure-digit string (so alpha2/alpha3/numeric and name
    # are disjoint shapes).
    _make_grammar(
        "country_name",
        _GRAMMAR_SOURCE,
        r"^(?!(?P<_only>[A-Za-z]{2,3})$)(?!\d+$)(?P<tok>.+)$",
        shape="name",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise the country shape the (already-trimmed) input matches.

    Returns one RecognizedRep per grammar whose regex FULLMATCHES the input.
    Each rep carries the grammar's `source` (Law 14) and only RAW string
    captures — no semantic meaning is assigned here. A `None` or non-country
    contract returns no matches.

    Args:
        value: The raw (already whitespace-trimmed) input string.
        contract: A CanonicalCountryContract (country-contract specific).

    Returns:
        A list of RecognizedRep (possibly empty when the input names no known
        country shape).
    """
    from paxman._capabilities.country.contract import CanonicalCountryContract

    if not isinstance(contract, CanonicalCountryContract):
        return []
    reps: list[RecognizedRep] = []
    # A leading/trailing ASCII whitespace trim is applied before matching
    # (spec §3.2 — deterministic, idempotent).
    value = value.strip(" \t\r\n\f\v")
    for grammar in GRAMMARS:
        match = grammar.compiled.fullmatch(value)
        if match is None:
            continue
        captures = {k: v for k, v in match.groupdict().items() if v is not None}
        reps.append(
            RecognizedRep(
                grammar_id=grammar.id,
                source=grammar.source,
                raw=match.group(0),
                shape=grammar.shape,
                captures=captures,
            )
        )
    return reps

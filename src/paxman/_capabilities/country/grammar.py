# src/paxman/_capabilities/country/grammar.py
"""Country recognition grammar (Layer 1 of the country architecture).

Recognition classifies the (whitespace-trimmed) raw input into one of a small
closed set of anchored shapes (alpha2 / alpha3 / name). It assigns NO canonical
meaning — the resolver (canonicalizer.generate_interpretations) performs the
table lookup. Recognition is a deterministic predicate only (Law 4).

Law 14: every grammar carries a `source` (provenance) for the shape it
recognises.

The recognition scaffold (Grammar, RecognizedRep, make_grammar, the match loop)
now lives in `paxman._capabilities._shared.grammar`; this module owns only the
country grammar set and the contract-typed `recognize` entry point.
"""

from __future__ import annotations

from paxman._capabilities._shared.grammar import (
    Grammar,
    RecognizedRep,
    make_grammar,
    recognize_grammars,
)
from paxman._capabilities.country.contract import CanonicalCountryContract

_GRAMMAR_SOURCE = "paxman spec/country §3.2 (closed country shape vocabulary)"

GRAMMARS: tuple[Grammar, ...] = (
    make_grammar("country_alpha2", _GRAMMAR_SOURCE, r"^(?P<tok>[A-Za-z]{2})$", shape="alpha2"),
    make_grammar("country_alpha3", _GRAMMAR_SOURCE, r"^(?P<tok>[A-Za-z]{3})$", shape="alpha3"),
    # Numeric (ISO 3166-1 M49) shape: 1-3 ASCII digits. Added as its own shape
    # so the resolver routes it to the numeric table. The name grammar below is
    # narrowed to exclude pure-digit strings so a numeric token matches ONLY
    # this grammar (never both numeric and name).
    make_grammar("country_numeric", _GRAMMAR_SOURCE, r"^(?P<tok>[0-9]{1,3})$", shape="numeric"),
    # Name shape: any non-empty trimmed token that is not exactly 2 or 3 ASCII
    # letters and is not a pure-digit string (so alpha2/alpha3/numeric and name
    # are disjoint shapes).
    make_grammar(
        "country_name",
        _GRAMMAR_SOURCE,
        r"^(?!(?P<_only>[A-Za-z]{2,3})$)(?![0-9]+$)(?P<tok>.+)$",
        shape="name",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise the country shape ``value`` full-matches.

    Delegates to the shared scaffold with the country contract type. A leading/
    trailing ASCII-whitespace trim (``" \t\r\n\f\v"``) is applied before matching
    — spec §3.2, deterministic and idempotent. A non-country contract returns no
    matches.

    Args:
        value: The raw input string.
        contract: A CanonicalCountryContract (country-contract specific).

    Returns:
        A list of RecognizedRep (possibly empty when the input names no known
        country shape).
    """
    return recognize_grammars(
        GRAMMARS, value, contract, CanonicalCountryContract, strip=" \t\r\n\f\v"
    )

# src/paxman/_capabilities/ip/grammar.py
"""IP grammar recognition layer (Layer 1 of the ip architecture).

Recognition classifies the raw input into one of a small set of anchored
shapes (ipv4 / ipv6 / ipv6_zone). It assigns NO canonical meaning — the
resolver (canonicalizer.generate_interpretations) delegates the actual parse
to the stdlib `ipaddress` module and formats per RFC 5952 / RFC 4291.
Recognition is a deterministic predicate only (Law 4).

Law 14: every grammar carries a `source` (provenance) for the shape it
recognises.

The scaffold (Grammar, RecognizedRep, make_grammar, the match loop) now lives
in `paxman._capabilities._shared.grammar`; this module owns only the IP
grammar set and the contract-typed `recognize` entry point. IP does NOT strip
input (the resolver trims ASCII whitespace itself), so `recognize_grammars`
is called with the default `strip=False`.
"""

from __future__ import annotations

from paxman._capabilities._shared.grammar import (
    Grammar,
    RecognizedRep,
    make_grammar,
    recognize_grammars,
)
from paxman._capabilities.ip.contract import CanonicalIPContract


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise the IP shape ``value`` full-matches.

    Delegates to the shared scaffold with the IP contract type. IP does not
    strip input (the resolver handles ASCII-whitespace trimming), so the
    default ``strip=False`` is used.

    Returns one RecognizedRep per grammar whose regex FULLMATCHES the input.
    Each rep carries the grammar's `source` (Law 14) and only RAW string
    captures — no semantic meaning is assigned here. A `None` or non-IP
    contract returns no matches.

    Args:
        value: The raw input string.
        contract: A CanonicalIPContract (ip-contract specific).

    Returns:
        A list of RecognizedRep (possibly empty when the input names no
        known IP shape).
    """
    return recognize_grammars(GRAMMARS, value, contract, CanonicalIPContract)


_GRAMMAR_SOURCE = "paxman spec/ip §3.2 (closed IP shape vocabulary)"

# Anchored shape classifiers. These only ROUTE to the resolver; the resolver
# uses `ipaddress` to validate and to produce the canonical form. The ipv6
# pattern is intentionally permissive on hex/colon structure — the resolver is
# the authority on validity (catches malformed input as INVALID).
GRAMMARS: tuple[Grammar, ...] = (
    make_grammar(
        "ip_ipv4",
        _GRAMMAR_SOURCE,
        r"^(?P<addr>\d{1,3}(?:\.\d{1,3}){3})$",
        shape="ipv4",
    ),
    make_grammar(
        "ip_ipv6",
        _GRAMMAR_SOURCE,
        r"^(?P<addr>(?=[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*)[0-9A-Fa-f:.]+)$",
        shape="ipv6",
    ),
    make_grammar(
        "ip_ipv6_zone",
        _GRAMMAR_SOURCE,
        r"^(?P<addr>(?=[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*)[0-9A-Fa-f:.]+)%(?P<zone>[^%\s]+)$",
        shape="ipv6_zone",
    ),
)

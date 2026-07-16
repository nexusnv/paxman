# src/paxman/_capabilities/ip/grammar.py
"""IP grammar recognition layer (Layer 1 of the ip architecture).

Recognition classifies the raw (whitespace-trimmed) input into one of a small
set of anchored shapes (ipv4 / ipv6 / ipv6_zone). It assigns NO canonical
meaning — the resolver (canonicalizer.generate_interpretations) delegates the
actual parse to the stdlib `ipaddress` module and formats per RFC 5952 /
RFC 4291. Recognition is a deterministic predicate only (Law 4).

Law 14: every grammar carries a `source` (provenance) for the shape it
recognises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import attrs


@attrs.frozen
class Grammar:
    """A single IP grammar: a regex pattern plus provenance."""

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


_GRAMMAR_SOURCE = "paxman spec/ip §3.2 (closed IP shape vocabulary)"

# Anchored shape classifiers. These only ROUTE to the resolver; the resolver
# uses `ipaddress` to validate and to produce the canonical form. The ipv6
# pattern is intentionally permissive on hex/colon structure — the resolver is
# the authority on validity (catches malformed input as INVALID).
GRAMMARS: tuple[Grammar, ...] = (
    _make_grammar(
        "ip_ipv4",
        _GRAMMAR_SOURCE,
        r"^(?P<addr>\d{1,3}(?:\.\d{1,3}){3})$",
        shape="ipv4",
    ),
    _make_grammar(
        "ip_ipv6",
        _GRAMMAR_SOURCE,
        r"^(?P<addr>[0-9A-Fa-f:]+)$",
        shape="ipv6",
    ),
    _make_grammar(
        "ip_ipv6_zone",
        _GRAMMAR_SOURCE,
        r"^(?P<addr>[0-9A-Fa-f:]+)%(?P<zone>[^%\s]+)$",
        shape="ipv6_zone",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise the IP shape the (already-trimmed) input matches.

    Returns one RecognizedRep per grammar whose regex FULLMATCHES the input.
    Each rep carries the grammar's `source` (Law 14) and only RAW string
    captures — no semantic meaning is assigned here. A `None` or non-IP
    contract returns no matches.

    Args:
        value: The raw (already whitespace-trimmed) input string.
        contract: A CanonicalIPContract (ip-contract specific).

    Returns:
        A list of RecognizedRep (possibly empty when the input names no
        known IP shape).
    """
    from paxman._capabilities.ip.contract import CanonicalIPContract

    if not isinstance(contract, CanonicalIPContract):
        return []
    reps: list[RecognizedRep] = []
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

"""UUID grammar recognition layer (Layer 1 of the uuid architecture).

This module is the *recognition* layer: it maps a raw input string to the
set of grammar shapes it could name, producing only RAW string captures
(no semantic meaning). The resolver (``canonicalizer.generate_interpretations``)
assigns meaning to those captures and enumerates candidate canonical forms.

The grammars are expressed as anchored regexes; ``recognize`` full-matches
the input against every grammar and returns one ``RecognizedRep`` per match.

MANDATE alignment:
- Law 4: recognition is a deterministic predicate, never a scored guess.
- Law 14: every grammar carries a ``source`` (provenance) for the shape it
  recognises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import attrs


@attrs.frozen
class Grammar:
    """A single uuid grammar: a regex pattern plus provenance.

    Attributes:
        id: Stable grammar identifier (``"canonical_uuid"``).
        source: Provenance string (Law 14) — where this grammar's shape
            originates (e.g. ``"RFC 4122 §3 (the canonical form is 36 chars;
            8-4-4-4-12 grouping; lowercase hex)"``).
        pattern: The regex pattern string.
        compiled: The compiled regex (anchored via ``^``/``$``).
        shape: Optional shape tag.
    """

    id: str
    source: str
    pattern: str
    compiled: re.Pattern[str]
    shape: str | None = None


@attrs.frozen
class RecognizedRep:
    """A single grammar match: raw string captures, no semantic meaning.

    Attributes:
        grammar_id: The id of the matching grammar.
        source: The matching grammar's provenance (Law 14).
        raw: The full matched substring (``match.group(0)``).
        shape: The matching grammar's shape tag (may be ``None``).
        captures: Raw string captures keyed by regex group name
            (``value``). Only groups that participated in the match are
            present — recognition assigns NO meaning.
    """

    grammar_id: str
    source: str
    raw: str
    shape: str | None
    captures: Mapping[str, str]


def _make_grammar(id: str, source: str, pattern: str, shape: str | None = None) -> Grammar:
    """Construct a :class:`Grammar` (compiled, anchored)."""
    return Grammar(
        id=id,
        source=source,
        pattern=pattern,
        compiled=re.compile(pattern),
        shape=shape,
    )


# The canonical grammar set (Layer 1). Order is not significant — ``recognize``
# tries every grammar and returns all full-matches.
GRAMMARS: tuple[Grammar, ...] = (
    _make_grammar(
        "canonical_uuid",
        "RFC 4122 §3 (the canonical form is 36 chars; 8-4-4-4-12 grouping; lowercase hex)",
        r"^(?P<value>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every grammar shape the input full-matches.

    Tries every grammar in :data:`GRAMMARS`, returning one
    ``RecognizedRep`` per grammar whose regex FULLMATCHES the input. Each rep
    carries the grammar's ``source`` (Law 14) and only RAW string captures —
    no semantic meaning is assigned here.

    Args:
        value: The raw input string.
        contract: A
            :class:`~paxman._capabilities.uuid.contract.CanonicalUUIDContract`
            (the recognition layer is uuid-contract specific).

    Returns:
        A list of :class:`RecognizedRep` (possibly empty when the input names
        no known uuid shape).
    """
    from paxman._capabilities.uuid.contract import CanonicalUUIDContract

    if not isinstance(contract, CanonicalUUIDContract):
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

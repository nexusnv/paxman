"""Phone grammar recognition layer (Layer 1 of the phone architecture).

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
    """A single phone grammar: a regex pattern plus provenance.

    Attributes:
        id: Stable grammar identifier (``"e164"`` / ``"national"`` / ``"digits_only"``).
        source: Provenance string (Law 14) — where this grammar's shape originates.
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
        captures: Raw string captures keyed by regex group name. For the ``e164``
            grammar the groups are ``cc_first`` (the first digit of the country
            code) and ``national`` (the remaining digits) — recognition assigns
            NO meaning, so the full country code is not split out here; the
            resolver reassembles ``+{cc_first}{national}`` which reproduces the
            input byte-for-byte. Only groups that participated in the match are
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


# The canonical grammar set (Layer 1). The three grammars are mutually
# exclusive by construction: `e164` requires a leading `+`; `national`
# requires at least one separator character; `digits_only` matches only
# when there is no separator. A plain digits-only national number therefore
# matches exactly one grammar, so the resolver emits exactly one candidate
# and classify returns CANONICALIZED (never AMBIGUOUS for a determinable
# input — Law 1).
GRAMMARS: tuple[Grammar, ...] = (
    _make_grammar(
        "e164",
        "RFC 3966 §3 / ITU-T E.164 (global form: +<cc><national>; ASCII digits only)",
        r"^\+(?P<cc_first>[0-9])(?P<national>[0-9]+)$",
    ),
    _make_grammar(
        "national",
        "ITU-T E.164 national-number pattern (separated form; requires >=7 ASCII digits)",
        r"^(?P<national>(?=(?:[^0-9]*[0-9]){7})[0-9(][0-9 \-().]*[ \-().][0-9 \-().]*[0-9])$",
    ),
    _make_grammar(
        "digits_only",
        "ITU-T E.164 (ASCII digits only, no separators; leading digit 1-9 so "
        "00-prefixed international strings are not matched)",
        r"^(?P<national>[1-9][0-9]{6,14})$",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every grammar shape the input full-matches.

    Tries every grammar in :data:`GRAMMARS`, returning one ``RecognizedRep``
    per grammar whose regex FULLMATCHES the input. Each rep carries the
    grammar's ``source`` (Law 14) and only RAW string captures — no semantic
    meaning is assigned here.

    Args:
        value: The raw input string.
        contract: A ``CanonicalPhoneContract`` (the recognition layer is
            phone-contract specific).

    Returns:
        A list of ``RecognizedRep`` (possibly empty when the input names no
        known phone shape).
    """
    from paxman._capabilities.phone.contract import CanonicalPhoneContract

    if not isinstance(contract, CanonicalPhoneContract):
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

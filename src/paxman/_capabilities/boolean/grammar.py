"""Boolean grammar recognition layer (Layer 1 of the boolean architecture).

Recognition maps a raw input string to the boolean token shape it names,
producing only RAW string captures (no semantic meaning). The resolver
(`canonicalizer.generate_interpretations`) assigns meaning.

MANDATE alignment:
- Law 4: recognition is a deterministic predicate, never a scored guess.
- Law 14: every grammar carries a `source` (provenance) for the shape it
  recognises.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import attrs


@attrs.frozen
class Grammar:
    """A single boolean grammar: a regex pattern plus provenance."""

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


# The canonical token grammar set (Layer 1). Each grammar full-matches one
# group of equivalent boolean tokens. `recognize` tries every grammar and
# returns all full-matches. Order is not significant.
# Provenance: declared Paxman policy (paxman spec/boolean §3.2).
_GRAMMAR_SOURCE = "paxman spec/boolean §3.2 (closed boolean token vocabulary)"

GRAMMARS: tuple[Grammar, ...] = (
    _make_grammar("bool_true_words", _GRAMMAR_SOURCE, r"^(?P<token>true|t|yes|y|on|enabled)$"),
    _make_grammar("bool_false_words", _GRAMMAR_SOURCE, r"^(?P<token>false|f|no|n|off|disabled)$"),
    _make_grammar("bool_numeric_true", _GRAMMAR_SOURCE, r"^(?P<token>1)$"),
    _make_grammar("bool_numeric_false", _GRAMMAR_SOURCE, r"^(?P<token>0)$"),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every grammar shape the (already-trimmed) input full-matches.

    When the contract is not case_sensitive, the input is lower-cased before
    matching (case-insensitivity is a recognition-layer transform, recorded
    by the canonicalizer as `trimmed_whitespace`/`matched_boolean_token`
    evidence). Returns one RecognizedRep per grammar whose regex FULLMATCHES
    the input. Each rep carries the grammar's `source` (Law 14) and only RAW
    string captures — no semantic meaning is assigned here.

    Args:
        value: The raw (already whitespace-trimmed) input string.
        contract: A CanonicalBooleanContract (boolean-contract specific).

    Returns:
        A list of RecognizedRep (possibly empty when the input names no
        known boolean shape).
    """
    from paxman._capabilities.boolean.contract import CanonicalBooleanContract

    if not isinstance(contract, CanonicalBooleanContract):
        return []
    text = value if contract.case_sensitive else value.lower()
    reps: list[RecognizedRep] = []
    for grammar in GRAMMARS:
        match = grammar.compiled.fullmatch(text)
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

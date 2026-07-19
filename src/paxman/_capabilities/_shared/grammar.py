"""Shared Layer-1 recognition scaffold (mandate Law 14).

Paxman capabilities each run a recognition layer that full-matches raw input
against a set of anchored grammars and returns one ``RecognizedRep`` per match,
carrying only RAW string captures and the grammar's Law-14 ``source``. The
scaffold (``Grammar``, ``RecognizedRep``, ``make_grammar``, the match loop) was
verbatim-duplicated across every capability domain; it now lives here so a
recognition-scaffold fix lands once. Domains keep their own ``GRAMMARS`` tuple
and a thin ``recognize(value, contract)`` that delegates to
``recognize_grammars``.

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
    """A single recognition grammar: a regex pattern plus provenance.

    Attributes:
        id: Stable grammar identifier (e.g. ``"addr_spec"``).
        source: Provenance string (Law 14) for the shape this grammar recognises.
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
        captures: Raw string captures keyed by regex group name. Only groups
            that participated in the match are present — recognition assigns
            NO meaning.
    """

    grammar_id: str
    source: str
    raw: str
    shape: str | None
    captures: Mapping[str, str]


def make_grammar(
    id: str, source: str, pattern: str, shape: str | None = None
) -> Grammar:
    """Construct a :class:`Grammar` (compiled, anchored)."""
    return Grammar(
        id=id,
        source=source,
        pattern=pattern,
        compiled=re.compile(pattern),
        shape=shape,
    )


def recognize_grammars(
    grammars: tuple[Grammar, ...],
    value: str,
    contract: object,
    contract_type: type,
    *,
    strip: "bool | str" = False,
) -> list[RecognizedRep]:
    """Recognise every grammar shape ``value`` full-matches.

    Tries every grammar in ``grammars``, returning one ``RecognizedRep`` per
    grammar whose regex FULLMATCHES the input. Each rep carries the grammar's
    ``source`` (Law 14) and only RAW string captures — no semantic meaning is
    assigned here. A ``contract`` whose type is not ``contract_type`` yields no
    reps (the per-domain ``recognize`` guard, centralized). The signature mirrors
    each domain's ``recognize(value, contract)`` exactly: ``value`` is the raw
    string, ``contract`` is the contract instance.

    Args:
        grammars: The domain's compiled grammar set.
        value: The raw input string.
        contract: The contract instance this recogniser was called with.
        contract_type: The exact contract class this recogniser accepts.
        strip: Before matching, trim ``value``. ``True`` uses the full
            ``str.strip()`` (all Unicode whitespace); a non-empty ``str`` is
            passed as the explicit ``chars`` argument to ``str.strip(chars)``
            (preserves country's narrow ASCII-whitespace charset — see
            ``country/grammar.py``). ``False`` (default) matches untrimmed.

    Returns:
        A list of :class:`RecognizedRep` (possibly empty).
    """
    if not isinstance(contract, contract_type):
        return []
    if strip is True:
        matched = value.strip()
    elif strip:
        matched = value.strip(strip)
    else:
        matched = value
    reps: list[RecognizedRep] = []
    for grammar in grammars:
        match = grammar.compiled.fullmatch(matched)
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

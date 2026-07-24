"""Date grammar recognition layer (Layer 1).

Exports the GRAMMARS tuple and the recognize() entry point.
"""

from paxman._capabilities._shared.grammar import (
    Grammar,
    RecognizedRep,
    _select_grammars,
    recognize_grammars,
)
from paxman._capabilities._shared.grammar import (
    Provenance as Provenance,
)

# Sub-module grammar tuples
from paxman._capabilities.date.grammar.iso_8601 import ISO_GRAMMARS
from paxman._capabilities.date.grammar.numeric import NUMERIC_GRAMMARS
from paxman._capabilities.date.grammar.text import _LANGUAGE_STATE, TEXT_GRAMMARS

GRAMMARS: tuple[Grammar, ...] = ISO_GRAMMARS + NUMERIC_GRAMMARS + TEXT_GRAMMARS


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every date grammar shape the input full-matches.

    Contract-type guard lives here (capability layer).
    """
    from paxman._capabilities.date.contract import CanonicalDateContract

    if not isinstance(contract, CanonicalDateContract):
        return []

    effective_grammars = _select_grammars(
        GRAMMARS, contract.include_grammar, contract.exclude_grammar
    )

    # Language-independent grammars: use shared recognize_grammars
    lang_independent = [g for g in effective_grammars if g.id in _LANG_INDEPENDENT_IDS]
    reps = recognize_grammars(tuple(lang_independent), value)

    # Language-dependent grammars: set language via module-level state, then call
    language = contract.language
    for grammar in effective_grammars:
        if grammar.id in _LANG_INDEPENDENT_IDS:
            continue
        _LANGUAGE_STATE[grammar.id] = language
        captures = grammar.recognize_fn(value)
        if captures is not None:
            reps.append(
                RecognizedRep(
                    grammar_id=grammar.id,
                    provenance=grammar.provenance,
                    raw=value.strip(),
                    shape=grammar.shape,
                    captures=captures,
                )
            )
    return reps


# Language-independent grammar IDs
_LANG_INDEPENDENT_IDS = frozenset(
    {
        "iso_date",
        "numeric_slash",
        "numeric_slash_ymd",
    }
)

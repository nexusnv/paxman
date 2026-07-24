"""Date grammar recognition layer (Layer 1).

Exports the GRAMMARS tuple and the recognize() entry point.
"""

from paxman._capabilities._shared.grammar import (
    Grammar,
    RecognizedRep,
    recognize_grammars,
)
from paxman._capabilities._shared.grammar import (
    Provenance as Provenance,
)

# Sub-module grammar tuples
from paxman._capabilities.date.grammar.iso_8601 import ISO_GRAMMARS
from paxman._capabilities.date.grammar.numeric import NUMERIC_GRAMMARS
from paxman._capabilities.date.grammar.text import TEXT_GRAMMARS

GRAMMARS: tuple[Grammar, ...] = ISO_GRAMMARS + NUMERIC_GRAMMARS + TEXT_GRAMMARS


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every date grammar shape the input full-matches.

    Contract-type guard lives here (capability layer).
    """
    from paxman._capabilities.date.contract import CanonicalDateContract

    if not isinstance(contract, CanonicalDateContract):
        return []

    # Language-independent grammars: use shared recognize_grammars
    lang_independent = [g for g in GRAMMARS if g.id in _LANG_INDEPENDENT_IDS]
    reps = recognize_grammars(tuple(lang_independent), value)

    # Language-dependent grammars: set language on closure, then call
    language = contract.language
    for grammar in GRAMMARS:
        if grammar.id in _LANG_INDEPENDENT_IDS:
            continue
        grammar.recognize_fn._language = language  # type: ignore[attr-defined]
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

"""Boolean grammar recognition layer (Layer 1 of the boolean architecture).

Recognition maps a raw input string to the boolean token shape it names,
producing only RAW string captures (no semantic meaning). The scaffold now
lives in ``paxman._capabilities._shared.grammar``; this module owns only the
boolean grammar set and the contract-typed ``recognize`` entry point.

MANDATE alignment:
- Law 4: recognition is a deterministic predicate, never a scored guess.
- Law 14: every grammar carries a ``source`` (provenance) for the shape it
  recognises.
"""

from __future__ import annotations

from paxman._capabilities._shared.grammar import (
    Grammar,
    Provenance,
    RecognizedRep,
    _select_grammars,
    make_grammar,
    recognize_grammars,
)
from paxman._capabilities.boolean.contract import CanonicalBooleanContract

# The canonical token grammar set (Layer 1). Each grammar full-matches one
# group of equivalent boolean tokens. `recognize` tries every grammar and
# returns all full-matches. Order is not significant.
# Provenance: declared Paxman policy (paxman spec/boolean §3.2).
_GRAMMAR_SOURCE = Provenance(
    name="paxman spec/boolean §3.2",
    version="closed boolean token vocabulary",
)

GRAMMARS: tuple[Grammar, ...] = (
    make_grammar("bool_true_words", _GRAMMAR_SOURCE, r"^(?P<token>true|t|yes|y|on|enabled)$"),
    make_grammar("bool_false_words", _GRAMMAR_SOURCE, r"^(?P<token>false|f|no|n|off|disabled)$"),
    make_grammar("bool_numeric_true", _GRAMMAR_SOURCE, r"^(?P<token>1)$"),
    make_grammar("bool_numeric_false", _GRAMMAR_SOURCE, r"^(?P<token>0)$"),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every boolean grammar shape ``value`` full-matches.

    Boolean does NOT strip whitespace (the canonicalizer records
    ``trimmed_whitespace`` evidence when it trims), so ``strip`` is left at
    its default ``False``. When the contract is not case-sensitive, the input
    is lower-cased before matching (case-insensitivity is a recognition-layer
    transform, recorded by the canonicalizer as evidence). Delegates to the
    shared scaffold with the boolean contract type.
    """
    if not isinstance(contract, CanonicalBooleanContract):
        return []
    if not contract.case_sensitive:
        value = value.lower()
    selected = _select_grammars(GRAMMARS, contract.include_grammar, contract.exclude_grammar)
    return recognize_grammars(selected, value)

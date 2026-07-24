"""Shared Layer-1 recognition scaffold (mandate Law 14).

Exports the Provenance, Grammar, RecognizedRep types and the
recognize_grammars function. Each capability imports from here and
adds its own contract-type guard in its local ``recognize()`` entry point.
"""

from paxman._capabilities._shared.grammar.grammar import Grammar, make_grammar, parser_grammar
from paxman._capabilities._shared.grammar.provenance import Provenance
from paxman._capabilities._shared.grammar.recognition import recognize_grammars
from paxman._capabilities._shared.grammar.recognized_rep import RecognizedRep

__all__ = [
    "Grammar",
    "Provenance",
    "RecognizedRep",
    "make_grammar",
    "parser_grammar",
    "recognize_grammars",
]

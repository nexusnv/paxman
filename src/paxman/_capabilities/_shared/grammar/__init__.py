"""Shared Layer-1 recognition scaffold (mandate Law 14).

Exports the Provenance, Grammar, RecognizedRep types and the
recognize_grammars function. Each capability imports from here and
adds its own contract-type guard in its local ``recognize()`` entry point.
"""

from paxman._capabilities._shared.grammar.grammar import Grammar, make_grammar, parser_grammar
from paxman._capabilities._shared.grammar.provenance import Provenance
from paxman._capabilities._shared.grammar.recognition import recognize_grammars
from paxman._capabilities._shared.grammar.recognized_rep import RecognizedRep


def _select_grammars(
    grammars: tuple[Grammar, ...],
    include: tuple[str, ...] | None = None,
    exclude: tuple[str, ...] | None = None,
) -> tuple[Grammar, ...]:
    """Filter grammars by include/exclude grammar IDs from the contract.

    ``include`` limits the set to only the listed grammar IDs; ``exclude``
    removes grammars by ID.  When both are provided the include filter
    runs first, then the exclude filter removes from that reduced set.
    Empty or ``None`` tuples are no-ops.

    Args:
        grammars: The full grammar tuple to filter.
        include: Optional grammar IDs to keep.  ``None`` or ``()``
            means "keep all".
        exclude: Optional grammar IDs to remove.  ``None`` or ``()``
            means "remove none".

    Returns:
        A (possibly empty) tuple of Grammar objects.
    """
    result = grammars
    if include:
        result = tuple(g for g in result if g.id in set(include))
    if exclude:
        result = tuple(g for g in result if g.id not in set(exclude))
    return result


__all__ = [
    "Grammar",
    "Provenance",
    "RecognizedRep",
    "_select_grammars",
    "make_grammar",
    "parser_grammar",
    "recognize_grammars",
]

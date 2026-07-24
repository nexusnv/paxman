"""Pure recognize_grammars function — no contract parameter."""

from __future__ import annotations

from paxman._capabilities._shared.grammar.grammar import Grammar
from paxman._capabilities._shared.grammar.recognized_rep import RecognizedRep


def recognize_grammars(
    grammars: tuple[Grammar, ...],
    value: str,
    *,
    strip: bool | str = False,
) -> list[RecognizedRep]:
    """Apply ALL grammar rules to a raw value.

    Returns ``RecognizedRep`` objects for ALL matches (non-exclusive).
    Empty list if no grammars match. This is a **pure function** of
    ``(grammars, value)`` — the contract-type guard belongs to the
    capability layer, not here.

    Args:
        grammars: Tuple of grammar rules to apply.
        value: Raw input string.
        strip: If ``True``, strip whitespace before matching. If a string,
            strip that character set.

    Returns:
        A list of :class:`RecognizedRep` (possibly empty).
    """
    matched = value.strip() if strip is True else value.strip(strip) if strip else value
    reps: list[RecognizedRep] = []
    for grammar in grammars:
        captures = grammar.recognize_fn(matched)
        if captures is not None:
            reps.append(
                RecognizedRep(
                    grammar_id=grammar.id,
                    provenance=grammar.provenance,
                    raw=matched,
                    shape=grammar.shape,
                    captures=captures,
                )
            )
    return reps

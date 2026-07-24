"""UUID grammar recognition layer (Layer 1 of the uuid architecture).

Recognition maps raw input to grammar shapes, producing only RAW string
captures (no semantic meaning). The scaffold now lives in
``paxman._capabilities._shared.grammar``; this module owns only the UUID
grammar set and the contract-typed ``recognize`` entry point.

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
    make_grammar,
    recognize_grammars,
)
from paxman._capabilities.uuid.contract import CanonicalUUIDContract

_CANONICAL_UUID_PROVENANCE = Provenance(
    name="RFC 4122 §3",
    version="the canonical form is 36 chars; 8-4-4-4-12 grouping; lowercase hex",
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every UUID grammar shape ``value`` full-matches.

    Delegates to the shared scaffold with the UUID contract type.
    """
    if not isinstance(contract, CanonicalUUIDContract):
        return []
    return recognize_grammars(GRAMMARS, value)


# The canonical grammar set (Layer 1). Order is not significant.
GRAMMARS: tuple[Grammar, ...] = (
    make_grammar(
        "canonical_uuid",
        _CANONICAL_UUID_PROVENANCE,
        r"^(?P<value>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    ),
)

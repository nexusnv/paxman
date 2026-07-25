"""Email grammar recognition layer (Layer 1 of the email architecture).

Recognition maps raw input to grammar shapes, producing only RAW string
captures (no semantic meaning). The scaffold now lives in
``paxman._capabilities._shared.grammar``; this module owns only the email
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
    _select_grammars,
    make_grammar,
    recognize_grammars,
)
from paxman._capabilities.email.contract import CanonicalEmailContract

# Provenance constants for each grammar's source string.
_ADDR_SPEC_PROVENANCE = Provenance(
    name="RFC 5322 §3.4.1",
    version="addr-spec",
)
_WS_PADDED_PROVENANCE = Provenance(
    name="RFC 5322 §3.4.1 + §1.3/§3.2.2",
    version="CFWS/whitespace tolerated; obfuscation tolerance",
)
_VERBAL_AT_DOT_PROVENANCE = Provenance(
    name="Paxman spoken-form recognition",
    version="Paxman recognition grammar for spoken 'at'/'dot' obfuscation",
)
_QUOTED_LOCAL_PROVENANCE = Provenance(
    name="RFC 5322 §3.2.4",
    version="quoted local part",
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every email grammar shape ``value`` full-matches.

    Delegates to the shared scaffold with the email contract type.
    """
    if not isinstance(contract, CanonicalEmailContract):
        return []
    selected = _select_grammars(GRAMMARS, contract.include_grammar, contract.exclude_grammar)
    return recognize_grammars(selected, value)


# The canonical grammar set (Layer 1). Order is not significant.
GRAMMARS: tuple[Grammar, ...] = (
    make_grammar(
        "addr_spec",
        _ADDR_SPEC_PROVENANCE,
        r"^(?P<local>[A-Za-z0-9._%+\-]+)@(?P<domain>[A-Za-z0-9.\-]+)$",
    ),
    make_grammar(
        "ws_padded_addr_spec",
        _WS_PADDED_PROVENANCE,
        r"^(?P<local>[^ \t\r\n\f\v@]+[ \t\r\n\f\v]*)@"
        r"(?P<domain>[ \t\r\n\f\v]*[^ \t\r\n\f\v@]+"
        r"(?:[ \t\r\n\f\v]*\.[ \t\r\n\f\v]*[^ \t\r\n\f\v@]+)*)$",
    ),
    make_grammar(
        "verbal_at_dot_addr_spec",
        _VERBAL_AT_DOT_PROVENANCE,
        r"^(?P<local>[A-Za-z0-9._%+\-]+)[ \t\r\n\f\v\-]+at[ \t\r\n\f\v\-]+"
        r"(?P<mid>[A-Za-z0-9.\-]+)[ \t\r\n\f\v\-]+dot[ \t\r\n\f\v\-]+"
        r"(?P<tld>[A-Za-z]{2,})$",
    ),
    make_grammar(
        "quoted_local_addr_spec",
        _QUOTED_LOCAL_PROVENANCE,
        r'^(?P<local>"[^"]*")@(?P<domain>[A-Za-z0-9.\-]+)$',
    ),
)

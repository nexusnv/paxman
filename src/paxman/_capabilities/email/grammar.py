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
    RecognizedRep,
    make_grammar,
    recognize_grammars,
)
from paxman._capabilities.email.contract import CanonicalEmailContract


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every email grammar shape ``value`` full-matches.

    Delegates to the shared scaffold with the email contract type.
    """
    return recognize_grammars(GRAMMARS, value, contract, CanonicalEmailContract)


# The canonical grammar set (Layer 1). Order is not significant.
GRAMMARS: tuple[Grammar, ...] = (
    make_grammar(
        "addr_spec",
        "RFC 5322 §3.4.1 (addr-spec)",
        r"^(?P<local>[A-Za-z0-9._%+\-]+)@(?P<domain>[A-Za-z0-9.\-]+)$",
    ),
    make_grammar(
        "ws_padded_addr_spec",
        "RFC 5322 §3.4.1 + §1.3/§3.2.2 (CFWS/whitespace tolerated; obfuscation tolerance)",
        r"^(?P<local>[^ \t\r\n\f\v@]+[ \t\r\n\f\v]*)@"
        r"(?P<domain>[ \t\r\n\f\v]*[^ \t\r\n\f\v@]+"
        r"(?:[ \t\r\n\f\v]*\.[ \t\r\n\f\v]*[^ \t\r\n\f\v@]+)*)$",
    ),
    make_grammar(
        "verbal_at_dot_addr_spec",
        "RFC 5322 §3.4.1 (addr-spec is the canonical target) — Paxman "
        "recognition grammar for spoken 'at'/'dot' obfuscation",
        r"^(?P<local>[A-Za-z0-9._%+\-]+)[ \t\r\n\f\v\-]+at[ \t\r\n\f\v\-]+"
        r"(?P<mid>[A-Za-z0-9.\-]+)[ \t\r\n\f\v\-]+dot[ \t\r\n\f\v\-]+"
        r"(?P<tld>[A-Za-z]{2,})$",
    ),
    make_grammar(
        "quoted_local_addr_spec",
        "RFC 5322 §3.2.4 (quoted local part)",
        r'^(?P<local>"[^"]*")@(?P<domain>[A-Za-z0-9.\-]+)$',
    ),
)

"""URL grammar recognition layer (Layer 1 of the url architecture).

Recognition maps raw input to grammar shapes, producing only RAW string
captures (no semantic meaning). The scaffold now lives in
``paxman._capabilities._shared.grammar``; this module owns only the URL
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
from paxman._capabilities.url.contract import CanonicalURLContract

# Disjoint by construction:
#   absolute            requires a `scheme://` prefix
#   authority_relative  requires a leading `//` and no scheme
#   path_relative       negative-lookahead rejects both `//` and `scheme:`
# So recognize() returns at most one RecognizedRep per input.
GRAMMARS: tuple[Grammar, ...] = (
    make_grammar(
        "absolute",
        "RFC 3986 §3 (scheme '[A-Za-z][A-Za-z0-9+.-]*://' then hier-part)",
        r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*)://(?P<authority>[^/?#]*)(?P<pathqf>.*)$",
    ),
    make_grammar(
        "authority_relative",
        "RFC 3986 §3 (scheme-relative '//' authority form, no scheme)",
        r"^//(?P<authority>[^/?#]*)(?P<pathqf>.*)$",
    ),
    make_grammar(
        "path_relative",
        "RFC 3986 §3 (relative reference: no authority, path begins)",
        r"^(?!//)(?![A-Za-z][A-Za-z0-9+.\-]*:)(?P<pathqf>.*)$",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every URL grammar shape ``value`` full-matches.

    Delegates to the shared scaffold with the URL contract type. Recognition is
    shape-only; the resolver applies contract policy. Matching uses
    ``re.fullmatch`` so a trailing newline or any unconsumed tail is rejected
    (§3.2.3 form is preserved whole, never partially consumed).
    """
    return recognize_grammars(GRAMMARS, value, contract, CanonicalURLContract)

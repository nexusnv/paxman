"""Phone grammar recognition layer (Layer 1 of the phone architecture).

This module is the *recognition* layer: it maps a raw input string to the
set of grammar shapes it could name, producing only RAW string captures
(no semantic meaning). The scaffold now lives in
``paxman._capabilities._shared.grammar``; this module owns only the phone
grammar set and the contract-typed ``recognize`` entry point.

The grammars are expressed as anchored regexes; ``recognize`` full-matches
the input against every grammar and returns one ``RecognizedRep`` per match.

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
from paxman._capabilities.phone.contract import CanonicalPhoneContract

_E164_PROVENANCE = Provenance(
    name="RFC 3966 §3 / ITU-T E.164",
    version="global form: +<cc><national>; ASCII digits only",
)
_NATIONAL_PROVENANCE = Provenance(
    name="ITU-T E.164",
    version="national-number pattern (separated form; requires >=7 ASCII digits)",
)
_DIGITS_ONLY_PROVENANCE = Provenance(
    name="ITU-T E.164",
    version="ASCII digits only, no separators; leading digit 1-9",
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every phone grammar shape ``value`` full-matches.

    Delegates to the shared scaffold with the phone contract type. The input
    is matched untrimmed — phone recognition does not strip or lowercase
    before matching (preserving the original semantics).
    """
    if not isinstance(contract, CanonicalPhoneContract):
        return []
    return recognize_grammars(GRAMMARS, value)


# The canonical grammar set (Layer 1). The three grammars are mutually
# exclusive by construction: `e164` requires a leading `+`; `national`
# requires at least one separator character; `digits_only` matches only
# when there is no separator. A plain digits-only national number therefore
# matches exactly one grammar, so the resolver emits exactly one candidate
# and classify returns CANONICALIZED (never AMBIGUOUS for a determinable
# input — Law 1).
GRAMMARS: tuple[Grammar, ...] = (
    make_grammar(
        "e164",
        _E164_PROVENANCE,
        r"^\+(?P<cc_first>[0-9])(?P<national>[0-9]+)$",
    ),
    make_grammar(
        "national",
        _NATIONAL_PROVENANCE,
        r"^(?P<national>(?=(?:[^0-9]*[0-9]){7})[0-9(][0-9 \-().]*[ \-().][0-9 \-().]*[0-9])$",
    ),
    make_grammar(
        "digits_only",
        _DIGITS_ONLY_PROVENANCE,
        r"^(?P<national>[1-9][0-9]{6,14})$",
    ),
)

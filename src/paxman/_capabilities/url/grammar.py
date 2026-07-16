from __future__ import annotations

import re

import attrs


@attrs.frozen
class Grammar:
    id: str
    source: str
    pattern: str
    shape: str | None = None
    _compiled: re.Pattern[str] = attrs.field()

    @_compiled.default
    def _compile(self) -> re.Pattern[str]:
        return re.compile(self.pattern)

    @property
    def compiled(self) -> re.Pattern[str]:
        return self._compiled


@attrs.frozen
class RecognizedRep:
    grammar_id: str
    source: str
    raw: str
    shape: str | None = None
    captures: dict[str, str] = attrs.field(factory=dict)


def _make_grammar(id: str, source: str, pattern: str, shape: str | None = None) -> Grammar:
    return Grammar(id=id, source=source, pattern=pattern, shape=shape)


# Disjoint by construction:
#   absolute            requires a `scheme://` prefix
#   authority_relative  requires a leading `//` and no scheme
#   path_relative       negative-lookahead rejects both `//` and `scheme:`
# So recognize() returns at most one RecognizedRep per input.
GRAMMARS = (
    _make_grammar(
        "absolute",
        "RFC 3986 §3 (scheme '[A-Za-z][A-Za-z0-9+.-]*://' then hier-part)",
        r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*)://(?P<authority>[^/?#]*)(?P<pathqf>.*)$",
    ),
    _make_grammar(
        "authority_relative",
        "RFC 3986 §3 (scheme-relative '//' authority form, no scheme)",
        r"^//(?P<authority>[^/?#]*)(?P<pathqf>.*)$",
    ),
    _make_grammar(
        "path_relative",
        "RFC 3986 §3 (relative reference: no authority, path begins)",
        r"^(?!//)(?![A-Za-z][A-Za-z0-9+.\-]*:)(?P<pathqf>.*)$",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Layer-1 recognition — raw captures only, NO meaning assigned.

    Returns [] if contract is not a CanonicalURLContract. Recognition is
    shape-only; the resolver applies contract policy.

    Mandate laws touched:
    - Law 1 (Determinism): recognition is a pure function of (value, contract);
      identical inputs yield identical captures.
    - Law 3 (Never Guess): recognition assigns shape only, never a meaning or a
      canonical form — it upholds the no-guessing boundary by construction.
    - Law 14 (Provenance): every grammar cites its RFC 3986 §3 source in
      GRAMMARS; no rule fires without an authority.
    Matching uses ``re.fullmatch`` so a trailing newline or any unconsumed
    tail is rejected (§3.2.3 form is preserved whole, never partially consumed).
    """
    from paxman._capabilities.url.contract import CanonicalURLContract

    if not isinstance(contract, CanonicalURLContract):
        return []
    reps: list[RecognizedRep] = []
    for g in GRAMMARS:
        m = g.compiled.fullmatch(value)
        if m:
            reps.append(
                RecognizedRep(
                    grammar_id=g.id,
                    source=g.source,
                    raw=value,
                    captures={k: v for k, v in m.groupdict().items() if v is not None},
                )
            )
    return reps

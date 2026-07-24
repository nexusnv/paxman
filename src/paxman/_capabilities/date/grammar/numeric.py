"""Numeric slash date grammars."""

import re
from collections.abc import Mapping
from types import MappingProxyType

from paxman._capabilities._shared.grammar import Grammar, Provenance, parser_grammar

_PAXMAN_DATE_SPEC = Provenance(
    name="paxman spec/date",
    version="numeric slash; RFC 5545 §3.3.10 ordering rule; ambiguous when both orderings parse",
)
_ISO_8601_SLASH = Provenance(name="ISO 8601", version="slash ordering")

# Numeric slash: N1/N2/N3
_NUMERIC_TRIPLE_RE = re.compile(
    r"\s*(?P<n1>\d{1,2})/(?P<n2>\d{1,2})/(?P<n3>\d{2}(?:\d{2})?)\s*",
    re.IGNORECASE,
)


def _recognize_numeric_slash(value: str) -> Mapping[str, str] | None:
    match = _NUMERIC_TRIPLE_RE.fullmatch(value)
    if match is None:
        return None
    return MappingProxyType({k: v for k, v in match.groupdict().items() if v is not None})


# Year-first slash: YYYY/MM/DD
_YMD_RE = re.compile(
    r"\s*(?P<year>\d{4})\s*/\s*(?P<month>\d{1,2})\s*/\s*(?P<day>\d{1,2})\s*",
    re.IGNORECASE,
)


def _recognize_ymd(value: str) -> Mapping[str, str] | None:
    match = _YMD_RE.fullmatch(value)
    if match is None:
        return None
    return MappingProxyType({k: v for k, v in match.groupdict().items() if v is not None})


NUMERIC_SLASH = parser_grammar(
    "numeric_slash", _PAXMAN_DATE_SPEC, _recognize_numeric_slash, shape="numeric_triple"
)
NUMERIC_SLASH_YMD = parser_grammar("numeric_slash_ymd", _ISO_8601_SLASH, _recognize_ymd)

NUMERIC_GRAMMARS: tuple[Grammar, ...] = (NUMERIC_SLASH, NUMERIC_SLASH_YMD)

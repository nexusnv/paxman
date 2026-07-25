"""Text month grammars (language-dependent)."""

import re
from collections.abc import Callable, Mapping
from types import MappingProxyType

from paxman._capabilities._shared.grammar import Grammar, Provenance, parser_grammar
from paxman._capabilities.date.i18n import MONTH_NAMES, WEEKDAY_NAMES

CLDR = Provenance(name="CLDR month names")
RFC_2822 = Provenance(name="RFC 2822 §3.3")
PAXMAN_ORDINAL = Provenance(name="paxman spec/date", version="ordinal day form, natural language")

_ORDINAL_WORDS: Mapping[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
}
_ORDINAL_RE = r"\d{1,2}(?:st|nd|rd|th)|" + "|".join(re.escape(w) for w in _ORDINAL_WORDS)


def _month_alternation(language: str) -> str:
    names = sorted(MONTH_NAMES[language], key=len, reverse=True)
    return "|".join(re.escape(name) for name in names)


def _weekday_alternation(language: str) -> str:
    names = sorted(WEEKDAY_NAMES[language], key=len, reverse=True)
    return "|".join(re.escape(name) for name in names)


# Module-level language state keyed by grammar id.  The caller
# (date/grammar/__init__.py) writes the contract language here before
# invoking ``recognize_fn``; the closure reads it back.  Shared mutable
# state is acceptable for single-threaded use (same constraint as the
# previous closure-attribute approach).
_LANGUAGE_STATE: dict[str, str] = {}


def _make_language_grammar(
    grammar_id: str,
    provenance: Provenance,
    pattern_fn: Callable[[str], str],
    shape: str | None = None,
) -> Grammar:
    """Create a grammar whose recognize_fn recompiles per contract.language."""
    _cache: dict[str, re.Pattern[str]] = {}

    def recognize_fn(value: str) -> Mapping[str, str] | None:
        language = _LANGUAGE_STATE.get(grammar_id, "en")
        if language not in _cache:
            try:
                _cache[language] = re.compile(pattern_fn(language), re.IGNORECASE)
            except KeyError:
                return None
        match = _cache[language].fullmatch(value)
        if match is None:
            return None
        return MappingProxyType({k: v for k, v in match.groupdict().items() if v is not None})

    return parser_grammar(grammar_id, provenance, recognize_fn, shape=shape)


# ---------------------------------------------------------------------------
# Pattern factories — each returns a full-match regex for the given language
# ---------------------------------------------------------------------------


def _p_dmy(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<day>\d{{1,2}})\s+(?P<month>{ma})\s+(?P<year>\d{{2,4}})\s*"


def _p_dmy_dot(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<day>\d{{1,2}})\s*\.\s*(?P<month>{ma})\s+(?P<year>\d{{2,4}})\s*"


def _p_cm(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<month>{ma})\s*,\s*(?P<day>\d{{1,2}})\s+(?P<year>\d{{2,4}})\s*"


def _p_dash(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<day>\d{{1,2}})\s*-\s*(?P<month>{ma})\s*-\s*(?P<year>\d{{2,4}})\s*"


def _p_mdy_comma(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<month>{ma})\s+(?P<day>\d{{1,2}})\s*,\s*(?P<year>\d{{2,4}})\s*"


def _p_dmy_era(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<day>\d{{1,2}})\s+(?P<month>{ma})\s+(?P<year>\d{{2,4}})\s+AD\s*"


def _p_mdy_ord(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<month>{ma})\s+(?P<ordinal>{_ORDINAL_RE})\s*,\s*(?P<year>\d{{2,4}})\s*"


def _p_dmy_mixedsep(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<day>\d{{1,2}})\s*-\s*(?P<month>{ma})\s+(?P<year>\d{{2,4}})\s*"


def _p_mdy_slash(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<month>{ma})\s*/\s*(?P<day>\d{{1,2}})\s+(?P<year>\d{{2,4}})\s*"


def _p_dmy_ord(lang: str) -> str:
    ma = _month_alternation(lang)
    return rf"\s*(?P<ordinal>{_ORDINAL_RE})\s+(?P<month>{ma})\s+(?P<year>\d{{2,4}})\s*"


def _p_ordinal_weekday(lang: str) -> str:
    wa = _weekday_alternation(lang)
    ma = _month_alternation(lang)
    return (
        rf"\s*(?:(?P<weekday>{wa})\s*)?,\s*the\s+(?P<ordinal>{_ORDINAL_RE})"
        rf"\s+of\s+(?P<month>{ma})\s*,\s*(?P<year>\d{{2,4}})\s*"
    )


def _p_ordinal_nowkday(lang: str) -> str:
    ma = _month_alternation(lang)
    return (
        rf"\s*the\s+(?P<ordinal>{_ORDINAL_RE})"
        rf"\s+of\s+(?P<month>{ma})\s*,\s*(?P<year>\d{{2,4}})\s*"
    )


def _p_rfc2822(lang: str) -> str:
    """RFC 2822 pattern — always English regardless of contract language."""
    wa = _weekday_alternation("en")
    ma = _month_alternation("en")
    return (
        rf"\s*(?:(?P<weekday>{wa})\s*,?\s*)?"
        rf"(?P<day>\d{{1,2}})\s+(?P<month>{ma})\s+(?P<year>\d{{2,4}})\s*"
    )


TEXT_GRAMMARS: tuple[Grammar, ...] = (
    _make_language_grammar("text_month_dmy", CLDR, _p_dmy),
    _make_language_grammar("text_month_dmy_dot", CLDR, _p_dmy_dot),
    _make_language_grammar("text_month_cm", CLDR, _p_cm),
    _make_language_grammar("text_month_dash", CLDR, _p_dash),
    _make_language_grammar("text_month_mdy_comma", CLDR, _p_mdy_comma),
    _make_language_grammar("text_month_dmy_era", CLDR, _p_dmy_era),
    _make_language_grammar("text_month_mdy_ord", CLDR, _p_mdy_ord),
    _make_language_grammar("text_month_dmy_mixedsep", CLDR, _p_dmy_mixedsep),
    _make_language_grammar("text_month_mdy_slash", CLDR, _p_mdy_slash),
    _make_language_grammar("text_month_dmy_ord", CLDR, _p_dmy_ord),
    _make_language_grammar("ordinal_of_month", PAXMAN_ORDINAL, _p_ordinal_weekday),
    _make_language_grammar("ordinal_of_month_nowkday", PAXMAN_ORDINAL, _p_ordinal_nowkday),
    _make_language_grammar("rfc2822_date", RFC_2822, _p_rfc2822),
)

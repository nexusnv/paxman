"""Date grammar recognition layer (Layer 1 of the date architecture).

This module is the *recognition* layer: it maps a raw input string to the
set of grammar shapes it could name, producing only RAW string captures
(no semantic meaning). The resolver (``canonicalizer.generate_interpretations``)
assigns meaning to those captures and enumerates candidate calendar days.

The grammars are expressed in a small **bracket notation** so the shapes are
declarative and auditable (Law 14 — every grammar carries a ``source``). A
compiler turns the bracket notation into an anchored regex; ``recognize``
full-matches the input against every grammar and returns one ``RecognizedRep``
per match.

MANDATE alignment:
- Law 7: the month/weekday reading language is taken ONLY from
  ``contract.language``; the grammar compiler never infers a language.
- Law 14: every grammar carries a ``source`` (provenance) for the shape it
  recognises.
- Law 4: recognition is a deterministic predicate, never a scored guess.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import attrs

from paxman._capabilities.date.i18n import MONTH_NAMES, WEEKDAY_NAMES


@attrs.frozen
class Grammar:
    """A single date grammar: a bracket-notation pattern plus provenance.

    Attributes:
        id: Stable grammar identifier (e.g. ``"iso_date"``).
        source: Provenance string (Law 14) — where this grammar's shape
            originates (e.g. ``"ISO 8601"``, ``"CLDR month names"``).
        pattern: The bracket-notation pattern (e.g.
            ``"[DAY] [MONTH(lang)] [YEAR]"``).
        compiled: The compiled regex (built by :func:`compile_grammar` for the
            default language ``"en"``; :func:`recognize` recompiles per
            ``contract.language`` where a ``(lang)`` token appears).
        field_roles: Maps each bracket token to its regex group name
            (e.g. ``{"DAY": "day", "MONTH(lang)": "month", "YEAR": "year"}``).
        shape: Optional shape tag (e.g. ``"numeric_triple"``).
    """

    id: str
    source: str
    pattern: str
    compiled: re.Pattern[str]
    field_roles: Mapping[str, str]
    shape: str | None = None


@attrs.frozen
class RecognizedRep:
    """A single grammar match: raw string captures, no semantic meaning.

    Attributes:
        grammar_id: The id of the matching grammar.
        source: The matching grammar's provenance (Law 14).
        captures: Raw string captures keyed by regex group name
            (``year``, ``month``, ``day``, ``weekday``, ``ordinal``,
            ``n1``, ``n2``, ``n3``). Only groups that participated in the
            match are present — recognition assigns NO meaning.
    """

    grammar_id: str
    source: str
    captures: Mapping[str, str]


# ---------------------------------------------------------------------------
# Bracket-notation token vocabulary
# ---------------------------------------------------------------------------

# The combined numeric triple token (slash-separated). Handled as a unit so
# the three numeric groups are named n1/n2/n3 and tagged shape="numeric_triple".
_NUMERIC_TRIPLE = "[N1]/[N2]/[N3]"
_NUMERIC_TRIPLE_RE = r"(?P<n1>\d{1,2})/(?P<n2>\d{1,2})/(?P<n3>\d{2}(?:\d{2})?)"

# Ordinal day words -> int. This dict is the single source of truth: the
# resolver maps these words to their integer day (see _ordinal_to_int), and
# _ORDINAL_RE below is derived from its keys so the grammar regex never
# duplicates the word list. The numeric ordinal form ``\d{1,2}(?:st|nd|rd|th)``
# is also accepted and resolved by the resolver.
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

_ORDINAL_RE = r"\d{1,2}(?:st|nd|rd|th)|" + "|".join(re.escape(word) for word in _ORDINAL_WORDS)


def _month_alternation(language: str) -> str:
    """Build a case-insensitive alternation over the language's month names.

    Longest names first so ``june`` wins over ``jun`` (no partial-word bleed).
    """
    names = sorted(MONTH_NAMES[language], key=len, reverse=True)
    return "|".join(re.escape(name) for name in names)


def _weekday_alternation(language: str) -> str:
    """Build a case-insensitive alternation over the language's weekday names."""
    names = sorted(WEEKDAY_NAMES[language], key=len, reverse=True)
    return "|".join(re.escape(name) for name in names)


# Matches a bracket token carrying an explicit or placeholder language spec,
# e.g. "MONTH(lang)" or "DAY_OF_THE_WEEK(en)".
_TOKEN_LANG_RE = re.compile(r"^([A-Z_]+)\(([^)]+)\)$")


def _resolve_langspec(langspec: str, language: str) -> str:
    """Resolve a ``(lang)`` placeholder to the contract language, else passthrough."""
    return language if langspec == "lang" else langspec


def _compile_token(token: str, language: str) -> tuple[str, str, str]:
    """Compile one bracket token to ``(group_name, regex, role_key)``.

    Args:
        token: The inside of a ``[...]`` token, e.g. ``"YEAR"``,
            ``"MONTH(lang)"`` (use the contract language) or
            ``"MONTH(en)"`` (use the explicit language ``en``).
        language: The declared reading language (used for ``(lang)`` tokens).

    Returns:
        A 3-tuple of (regex group name, regex fragment, role key).

    Raises:
        ValueError: If the token is not part of the vocabulary.
    """
    lang_match = _TOKEN_LANG_RE.match(token)
    if lang_match is not None:
        base = lang_match.group(1)
        resolved = _resolve_langspec(lang_match.group(2), language)
        if base == "MONTH":
            return ("month", rf"(?P<month>{_month_alternation(resolved)})", token)
        if base == "DAY_OF_THE_WEEK":
            return (
                "weekday",
                rf"(?P<weekday>{_weekday_alternation(resolved)})",
                token,
            )
        raise ValueError(f"unknown grammar token: [{token}]")
    if token == "YEAR":
        return ("year", r"(?P<year>\d{2,4})", "YEAR")
    if token == "YEAR4":
        # Exactly four digits — used by the year-first slash grammar so it
        # cannot be confused with a 2-digit leading group (e.g. "16/07/26").
        return ("year", r"(?P<year>\d{4})", "YEAR4")
    if token == "MONTH":
        return ("month", r"(?P<month>\d{1,2})", "MONTH")
    if token == "DAY":
        return ("day", r"(?P<day>\d{1,2})", "DAY")
    if token == "DAY_IN_ORDINAL":
        return ("ordinal", rf"(?P<ordinal>{_ORDINAL_RE})", "DAY_IN_ORDINAL")
    raise ValueError(f"unknown grammar token: [{token}]")


# Regex-special characters that must be escaped inside literal separator runs.
# ``?`` and ``*`` are deliberately excluded: the bracket notation uses ``?`` as
# a regex-style "optional" quantifier inside literals (e.g. the ``,?`` optional
# comma in ``rfc2822_date``), so it must remain a live quantifier, not a
# literal character.
_ESCAPE_SPECIAL = set(".+()[]{}|^$\\")


def _escape_literal(literal: str, flexible_ws: bool = False) -> str:
    """Escape a literal separator run.

    Whitespace explicitly present in the pattern becomes a *required* ``\\s+``
    separator by default, so adjacent grammar fields cannot run together
    (e.g. ``[DAY] [MONTH]`` will not match ``16July2026``). When ``flexible_ws``
    is True (used where the preceding grammar token is optional, so the field
    may be absent), the whitespace is a flexible ``\\s*`` instead — otherwise a
    required gap would demand a separator even when the field is missing (e.g.
    the optional weekday in ``rfc2822_date`` would reject ``"16 July 2026"``).

    Non-whitespace atoms are escaped (regex-special chars except ``?``/``*``)
    and wrapped with flexible ``\\s*`` so punctuation separators tolerate
    variable surrounding whitespace — a literal ``.`` becomes ``\\s*\\.\\s*``
    (matching ``". "`` or ``"."``) and ``,?`` becomes ``\\s*,?\\s*`` (an
    optional comma). The ``?`` quantifier is left live (see
    ``_ESCAPE_SPECIAL``).
    """
    if not literal:
        return ""
    out: list[str] = []
    ws = r"\s*" if flexible_ws else r"\s+"
    i = 0
    n = len(literal)
    while i < n:
        if literal[i].isspace():
            out.append(ws)
            while i < n and literal[i].isspace():
                i += 1
            continue
        j = i
        while j < n and not literal[j].isspace():
            j += 1
        atom = literal[i:j]
        if atom == ",?":
            # Optional comma separator with flexible whitespace.
            out.append(r"\s*,?\s*")
        else:
            escaped = "".join("\\" + ch if ch in _ESCAPE_SPECIAL else ch for ch in atom)
            out.append(r"\s*" + escaped + r"\s*")
        i = j
    return "".join(out)


def _field_roles(pattern: str) -> dict[str, str]:
    """Compute the ``field_roles`` mapping for a bracket-notation pattern."""
    roles: dict[str, str] = {}
    if _NUMERIC_TRIPLE in pattern:
        return {"N1": "n1", "N2": "n2", "N3": "n3"}
    token_re = re.compile(r"\[([^\]]+)\]")
    for match in token_re.finditer(pattern):
        _group_name, _regex, role_key = _compile_token(match.group(1), "en")
        roles[role_key] = _group_name
    return roles


def compile_grammar(pattern: str, language: str) -> re.Pattern[str]:
    """Compile a bracket-notation grammar pattern into an anchored regex.

    The returned pattern is compiled WITHOUT ``^``/``$`` anchors; callers use
    :meth:`re.Pattern.fullmatch` so the entire input must be consumed. The
    pattern is compiled case-insensitively (month/weekday names and the
    literal words ``the``/``of`` are case-insensitive).

    Args:
        pattern: The bracket-notation pattern, e.g.
            ``"[DAY] [MONTH(lang)] [YEAR]"``.
        language: The declared reading language. Used to expand ``(lang)``
            tokens into the language's month/weekday-name alternation. Must be
            a supported language (``i18n.SUPPORTED_LANGUAGES``); an unsupported
            language raises so the caller can skip the grammar (no match).

    Returns:
        A compiled :class:`re.Pattern` that full-matches inputs of this shape.

    Raises:
        ValueError: If ``language`` is not a supported language, or the pattern
            contains an unknown token.
    """
    if language not in MONTH_NAMES:
        raise ValueError(f"unsupported language for grammar compilation: {language!r}")

    if _NUMERIC_TRIPLE in pattern:
        # The numeric triple is a single slash-separated token; no literals.
        # Leading/trailing whitespace is tolerated (fullmatch still requires
        # the whole string to be consumed).
        return re.compile(r"\s*" + _NUMERIC_TRIPLE_RE + r"\s*", re.IGNORECASE)

    parts: list[str] = []
    token_re = re.compile(r"\[([^\]]+)\](\?)?")
    pos = 0
    prev_optional: bool | None = None  # None = no preceding token yet
    for match in token_re.finditer(pattern):
        literal = pattern[pos : match.start()]
        if literal:
            # A required separator (\\s+) only makes sense between two fields
            # that are both present. If the preceding token is optional (or
            # there is no preceding token), the gap stays flexible (\\s*) so the
            # separator is not demanded when the field is absent.
            flexible = prev_optional is not False
            parts.append(_escape_literal(literal, flexible_ws=flexible))
        token = match.group(1)
        optional = match.group(2)
        _group_name, group_re, _role_key = _compile_token(token, language)
        parts.append(rf"(?:{group_re})?" if optional else group_re)
        prev_optional = optional is not None
        pos = match.end()
    trailing = pattern[pos:]
    if trailing:
        flexible = prev_optional is not False
        parts.append(_escape_literal(trailing, flexible_ws=flexible))
    # Leading/trailing whitespace is tolerated; fullmatch still requires the
    # whole string to be consumed.
    return re.compile(r"\s*" + "".join(parts) + r"\s*", re.IGNORECASE)


def _make_grammar(id: str, source: str, pattern: str, shape: str | None = None) -> Grammar:
    """Construct a :class:`Grammar` (compiled for the default language ``en``)."""
    return Grammar(
        id=id,
        source=source,
        pattern=pattern,
        compiled=compile_grammar(pattern, "en"),
        field_roles=_field_roles(pattern),
        shape=shape,
    )


# The canonical grammar set (Layer 1). Order is not significant — ``recognize``
# tries every grammar and returns all full-matches.
GRAMMARS: tuple[Grammar, ...] = (
    _make_grammar("iso_date", "ISO 8601", "[YEAR]-[MONTH]-[DAY]"),
    _make_grammar("text_month_dmy", "CLDR month names", "[DAY] [MONTH(lang)] [YEAR]"),
    _make_grammar("text_month_dmy_dot", "CLDR month names", "[DAY].[MONTH(lang)] [YEAR]"),
    _make_grammar("text_month_cm", "CLDR month names", "[MONTH(lang)], [DAY] [YEAR]"),
    _make_grammar("text_month_dash", "CLDR month names", "[DAY]-[MONTH(lang)]-[YEAR]"),
    _make_grammar(
        "numeric_slash",
        "paxman spec/date (numeric slash; RFC 5545 §3.3.10 order heuristic; "
        "ambiguous when both orderings parse)",
        "[N1]/[N2]/[N3]",
        shape="numeric_triple",
    ),
    _make_grammar(
        "rfc2822_date",
        "RFC 2822 §3.3",
        "[DAY_OF_THE_WEEK(en)]?,? [DAY] [MONTH(en)] [YEAR]",
    ),
    _make_grammar(
        "ordinal_of_month",
        "paxman spec/date (ordinal day form, natural language)",
        "[DAY_OF_THE_WEEK(lang)]?, the [DAY_IN_ORDINAL] of [MONTH(lang)], [YEAR]",
    ),
    # --- Coverage-gap closures (7 new productions) ---
    _make_grammar(
        "text_month_mdy_comma",
        "CLDR month names",
        "[MONTH(lang)] [DAY], [YEAR]",
    ),
    _make_grammar(
        "ordinal_of_month_nowkday",
        "paxman spec/date (ordinal day form, natural language)",
        "the [DAY_IN_ORDINAL] of [MONTH(lang)], [YEAR]",
    ),
    _make_grammar(
        "text_month_dmy_ord",
        "CLDR month names",
        "[DAY_IN_ORDINAL] [MONTH(lang)] [YEAR]",
    ),
    _make_grammar(
        "numeric_slash_ymd",
        "ISO 8601 (slash ordering)",
        "[YEAR4]/[MONTH]/[DAY]",
    ),
    _make_grammar(
        "text_month_dmy_era",
        "CLDR month names",
        "[DAY] [MONTH(lang)] [YEAR] AD",
    ),
    _make_grammar(
        "text_month_mdy_ord",
        "CLDR month names",
        "[MONTH(lang)] [DAY_IN_ORDINAL], [YEAR]",
    ),
    _make_grammar(
        "text_month_dmy_mixedsep",
        "CLDR month names",
        "[DAY]-[MONTH(lang)] [YEAR]",
    ),
    _make_grammar(
        "text_month_mdy_slash",
        "CLDR month names",
        "[MONTH(lang)]/[DAY] [YEAR]",
    ),
)


def recognize(value: str, contract: object) -> list[RecognizedRep]:
    """Recognise every grammar shape the input full-matches.

    Tries every grammar in :data:`GRAMMARS`, compiling per
    ``contract.language`` where a ``(lang)`` token appears. Returns one
    ``RecognizedRep`` per grammar whose regex FULLMATCHES the input. Each rep
    carries the grammar's ``source`` (Law 14) and only RAW string captures —
    no semantic meaning is assigned here.

    Args:
        value: The raw input string.
        contract: A :class:`~paxman._capabilities.date.contract.CanonicalDateContract`
            supplying the declared ``language`` (Law 7 — never inferred).

    Returns:
        A list of :class:`RecognizedRep` (possibly empty when the input names
        no known date shape).
    """
    from paxman._capabilities.date.contract import CanonicalDateContract

    if not isinstance(contract, CanonicalDateContract):
        return []
    language = contract.language
    reps: list[RecognizedRep] = []
    for grammar in GRAMMARS:
        try:
            rx = compile_grammar(grammar.pattern, language)
        except ValueError:
            # Unsupported language for this grammar's (lang) tokens -> no match.
            continue
        match = rx.fullmatch(value)
        if match is None:
            continue
        captures = {k: v for k, v in match.groupdict().items() if v is not None}
        reps.append(RecognizedRep(grammar_id=grammar.id, source=grammar.source, captures=captures))
    return reps

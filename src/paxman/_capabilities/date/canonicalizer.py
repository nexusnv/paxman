"""DateCapability: a built-in capability of Paxman v2.

Mandate alignment:
- Law 4: rewrites known representations (ISO 8601, US/EU numeric, RFC 2822,
  Unix epoch) of a date/datetime into one canonical form. Never guesses.
- Law 7: ``locale`` is required on the contract; no auto_detect.
- Law 8a: pure function of (value, contract). No network, no time.now(),
  no filesystem.
- Law 11: SPI litmus — two implementations produce the same canonical form.
- Law 14: every rule cites a source via ``_RULE_PROVENANCE``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import attrs

from paxman._capabilities.date.calendar import _valid_calendar_date
from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._capabilities.date.grammar import _ORDINAL_WORDS, RecognizedRep, recognize
from paxman._capabilities.date.i18n import MONTH_NAMES, WEEKDAY_NAMES
from paxman._capabilities.date.parser import (
    _ISO_DATE_RE,
    _ISO_DATETIME_RE,
    _ISO_NAIVE_DATETIME_RE,
    _NUMERIC_2YEAR_RE,
    _NUMERIC_4YEAR_RE,
    _RFC2822_RE,
    _RFC2822_TIME_RE,
    _is_epoch,
)
from paxman._capabilities.date.rules import _evidence
from paxman._capabilities.date.value import _render_date, _render_datetime
from paxman._core.contracts import Contract
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

# RFC 2822 §3.3 month abbreviations are always English; we map them
# explicitly instead of `datetime.strptime("%b")` because `%b` is
# locale-dependent (mandate Law 7: locale must not leak into
# canonicalization). This keeps the date-only RFC 2822 path
# deterministic regardless of the process locale.
_RFC2822_MONTHS: dict[str, int] = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _parse_rfc2822_date_only(date_part: str) -> datetime | None:
    """Locale-independent parse of the RFC 2822 date-only ``D Mon YYYY`` form.

    Returns a ``datetime`` on success or ``None`` when the form is
    malformed, the month is unknown, or the calendar date is invalid
    (the caller maps ``None`` to ``Status.INVALID``).
    """
    match = re.match(r"^\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s*$", date_part)
    if match is None:
        return None
    day = int(match.group(1))
    month = _RFC2822_MONTHS.get(match.group(2).lower())
    year = int(match.group(3))
    if month is None or not _valid_calendar_date(year, month, day):
        return None
    return datetime(year, month, day)


@attrs.frozen
class _Candidate:
    """A single enumerated reading of a date-shaped input.

    ``year`` is the resolved 4-digit year (``None`` when the year is a 2-digit
    value whose century is still ambiguous). ``yy`` is the raw 2-digit year
    (``None`` for 4-digit years). ``century_ambiguous`` marks 2-digit years
    with no declared ``two_digit_year`` policy. ``ordering`` is ``"MD"`` or
    ``"DM"`` for numeric slash forms and ``None`` for text-month forms.
    """

    year: int | None
    yy: int | None
    month: int
    day: int
    century_ambiguous: bool
    rule: str
    ordering: str | None
    weekday: int | None = None


@attrs.frozen
class _Survivor:
    """A candidate that survived validation: a concrete calendar day."""

    year: int
    month: int
    day: int
    rule: str
    ordering: str | None
    century_ambiguous: bool


# Text-month grammar ids recognised by the grammar layer (Layer 1). All of
# these carry a 4-digit-or-2-digit year in the ``year`` capture group and a
# numeric ``day`` capture; the resolver distinguishes them by length (spec §5
# + §8). ``text_month_mdy_comma`` / ``text_month_dmy_era`` / ``text_month_dmy_mixedsep``
# are coverage-gap closures that share the same (day, month, year) capture shape.
_TEXT_MONTH_GRAMMARS = frozenset(
    {
        "text_month_dmy",
        "text_month_dmy_dot",
        "text_month_cm",
        "text_month_dash",
        "rfc2822_date",
        "text_month_mdy_comma",
        "text_month_dmy_era",
        "text_month_dmy_mixedsep",
        "text_month_mdy_slash",
    }
)

# Text-month grammar ids whose day arrives as a ``[DAY_IN_ORDINAL]`` capture
# (numeric-with-suffix or word form) rather than a bare ``[DAY]``. The resolver
# maps the ordinal capture to an integer day before the usual year-length
# handling (spec §5 + §8).
_TEXT_MONTH_ORDINAL_GRAMMARS = frozenset(
    {"text_month_dmy_ord", "text_month_mdy_ord", "ordinal_of_month_nowkday"}
)


def _ordinal_to_int(token: str) -> int:
    """Map a ``[DAY_IN_ORDINAL]`` capture to its day-of-month integer."""
    lowered = token.lower()
    if lowered in _ORDINAL_WORDS:
        return _ORDINAL_WORDS[lowered]
    # Numeric ordinal form, e.g. "3rd" / "21st".
    match = re.match(r"(\d{1,2})", lowered)
    assert match is not None
    return int(match.group(1))


def _orderings_for(locale: str) -> tuple[str, ...]:
    """Numeric slash orderings permitted by the locale policy (spec §3.3)."""
    if locale == "US":
        return ("MD",)
    if locale == "EU":
        return ("DM",)
    return ("MD", "DM")  # ISO enumerates both orderings


def _interpretations_from_reps(
    reps: list[RecognizedRep], contract: CanonicalDateContract
) -> list[_Candidate]:
    """Map grammar recognitions to candidate semantic values (resolver).

    This is the resolver (Layer 2): it assigns meaning to the raw captures
    produced by :func:`grammar.recognize` and enumerates every candidate
    calendar day the declared policies permit. It preserves the existing
    resolver semantics: month-name lookup via ``i18n.MONTH_NAMES[language]``
    (no cross-language guess, Law 7), 2-digit-year day/year swap enumeration
    for text-month forms, and locale-ordered numeric enumeration.
    """
    candidates: list[_Candidate] = []
    table = MONTH_NAMES[contract.language]
    weekday_table = WEEKDAY_NAMES[contract.language]
    for rep in reps:
        caps = rep.captures
        gid = rep.grammar_id
        if gid in _TEXT_MONTH_GRAMMARS:
            day = int(caps["day"])
            month = table.get(caps["month"].lower())
            if month is None:
                # Month name not in the declared language -> no cross-language
                # guess (Law 7). This recognition yields no candidate.
                continue
            weekday = (
                weekday_table.get(caps["weekday"].lower()) if "weekday" in caps else None
            )
            year_str = caps["year"]
            if len(year_str) == 2:
                # 2-digit year: the day/year assignment is ambiguous, so
                # enumerate both (day=first/year=second and day=second/
                # year=first). Each reading carries the raw 2-digit year and is
                # century-expanded later (spec §5 + §8).
                yy = int(year_str)
                for d, y in ((day, yy), (yy, day)):
                    candidates.append(
                        _Candidate(
                            year=None,
                            yy=y,
                            month=month,
                            day=d,
                            century_ambiguous=True,
                            rule="parsed_text_month_date",
                            ordering=None,
                            weekday=weekday,
                        )
                    )
            else:
                candidates.append(
                    _Candidate(
                        year=int(year_str),
                        yy=None,
                        month=month,
                        day=day,
                        century_ambiguous=False,
                        rule="parsed_text_month_date",
                        ordering=None,
                        weekday=weekday,
                    )
                )
        elif gid == "numeric_slash":
            a = int(caps["n1"])
            b = int(caps["n2"])
            y_str = caps["n3"]
            yy = int(y_str) if len(y_str) == 2 else None
            year = int(y_str) if len(y_str) == 4 else None
            for ordering in _orderings_for(contract.locale):
                month = a if ordering == "MD" else b
                day = b if ordering == "MD" else a
                candidates.append(
                    _Candidate(
                        year=year,
                        yy=yy,
                        month=month,
                        day=day,
                        century_ambiguous=(yy is not None),
                        rule="parsed_numeric_date",
                        ordering=ordering,
                    )
                )
        elif gid == "ordinal_of_month":
            day = _ordinal_to_int(caps["ordinal"])
            month = table.get(caps["month"].lower())
            if month is None:
                continue
            weekday = (
                weekday_table.get(caps["weekday"].lower()) if "weekday" in caps else None
            )
            year_str = caps["year"]
            if len(year_str) == 2:
                # 2-digit year with no century policy -> enumerate the day/year
                # swap (spec §5: Don't Guess). Mirrors the ordinal grammar
                # family so weekday-prefixed forms stay consistent.
                yy = int(year_str)
                for d, y in ((day, yy), (yy, day)):
                    candidates.append(
                        _Candidate(
                            year=None,
                            yy=y,
                            month=month,
                            day=d,
                            century_ambiguous=True,
                            rule="parsed_text_month_date",
                            ordering=None,
                            weekday=weekday,
                        )
                    )
            else:
                candidates.append(
                    _Candidate(
                        year=int(year_str),
                        yy=None,
                        month=month,
                        day=day,
                        century_ambiguous=False,
                        rule="parsed_text_month_date",
                        ordering=None,
                        weekday=weekday,
                    )
                )
        elif gid in _TEXT_MONTH_ORDINAL_GRAMMARS:
            # Ordinal day (numeric-with-suffix or word form) in either dmy or mdy
            # position, with no weekday prefix. Same year-length handling as the
            # text-month family (2-digit year -> day/year swap enumeration).
            day = _ordinal_to_int(caps["ordinal"])
            month = table.get(caps["month"].lower())
            if month is None:
                continue
            year_str = caps["year"]
            if len(year_str) == 2:
                yy = int(year_str)
                for d, y in ((day, yy), (yy, day)):
                    candidates.append(
                        _Candidate(
                            year=None,
                            yy=y,
                            month=month,
                            day=d,
                            century_ambiguous=True,
                            rule="parsed_text_month_date",
                            ordering=None,
                        )
                    )
            else:
                candidates.append(
                    _Candidate(
                        year=int(year_str),
                        yy=None,
                        month=month,
                        day=day,
                        century_ambiguous=False,
                        rule="parsed_text_month_date",
                        ordering=None,
                    )
                )
        elif gid == "numeric_slash_ymd":
            # Year-first slash (ISO 8601 slash ordering): the year capture is
            # exactly four digits (YEAR4 token), so there is no locale ordering
            # enumeration and no century ambiguity — a single fixed Y/M/D
            # reading.
            candidates.append(
                _Candidate(
                    year=int(caps["year"]),
                    yy=None,
                    month=int(caps["month"]),
                    day=int(caps["day"]),
                    century_ambiguous=False,
                    rule="parsed_numeric_ymd_date",
                    ordering=None,
                )
            )
        elif gid == "iso_date":
            candidates.append(
                _Candidate(
                    year=int(caps["year"]),
                    yy=None,
                    month=int(caps["month"]),
                    day=int(caps["day"]),
                    century_ambiguous=False,
                    rule="parsed_iso_date",
                    ordering=None,
                )
            )
    # Recognition is non-exclusive: an input may match several grammars (e.g.
    # "16 July 2026" matches both text_month_dmy and rfc2822_date). Collapse
    # duplicate candidates so identical readings do not masquerade as
    # AMBIGUOUS (spec §2.4 — surface ambiguity only when readings genuinely
    # differ).
    seen: set[tuple[object, ...]] = set()
    unique: list[_Candidate] = []
    for candidate in candidates:
        key = attrs.astuple(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def generate_interpretations(value: str, contract: CanonicalDateContract) -> list[_Candidate]:
    """Enumerate every candidate semantic value the input could name (spec §5).

    The recognition front routes through :func:`grammar.recognize`, which
    returns the raw captures of every grammar shape the input full-matches.
    The resolver (:func:`_interpretations_from_reps`) assigns meaning to those
    captures and enumerates every candidate calendar day the declared policies
    permit.
    """
    reps = recognize(value, contract)
    return _interpretations_from_reps(reps, contract)


def _resolve_pivot_year(yy: int, policy: str) -> int:
    """Apply a ``pivot:YYYY`` policy (spec §3.2 corrected).

    The resolved year is ``(YYYY // 100) * 100 + YY`` — i.e. the century of
    the pivot year, plus the 2-digit year. So ``pivot:2000`` maps ``26`` to
    ``2026`` and ``25`` to ``2025`` (not the classic ``<70`` split).
    """
    pivot = int(policy.split(":", 1)[1])
    return (pivot // 100) * 100 + yy


def resolve_and_validate(
    candidates: list[_Candidate], contract: CanonicalDateContract
) -> tuple[list[_Survivor], set[str]]:
    """Validate each candidate; drop those that name no calendar day (spec §6)."""
    survivors: list[_Survivor] = []
    drop_reasons: set[str] = set()
    for c in candidates:
        if c.century_ambiguous:
            # Basic month/day sanity before century expansion.
            if not (1 <= c.month <= 12) or not (1 <= c.day <= 31):
                drop_reasons.add("invalid_calendar_date")
                continue
            if contract.two_digit_year in ("reject", "require_four_digit_year"):
                drop_reasons.add("rejected_two_digit_year")
                continue
            yy = c.yy
            assert yy is not None
            if contract.two_digit_year is None:
                # No policy -> expand across three centuries (spec §3.2).
                years = [base + yy for base in (1900, 2000, 2100)]
            else:
                # pivot:YYYY -> a single resolved 4-digit year.
                years = [_resolve_pivot_year(yy, contract.two_digit_year)]
            for year in years:
                if not _valid_calendar_date(year, c.month, c.day):
                    continue
                if (
                    c.weekday is not None
                    and datetime(year, c.month, c.day).weekday() != c.weekday
                ):
                    drop_reasons.add("weekday_contradicts_date")
                    continue
                survivors.append(_Survivor(year, c.month, c.day, c.rule, c.ordering, True))
        else:
            if not _valid_calendar_date(c.year, c.month, c.day):
                drop_reasons.add("invalid_calendar_date")
                continue
            if (
                c.weekday is not None
                and datetime(c.year, c.month, c.day).weekday() != c.weekday
            ):
                drop_reasons.add("weekday_contradicts_date")
                continue
            survivors.append(_Survivor(c.year, c.month, c.day, c.rule, c.ordering, False))
    # Collapse survivors that resolve to the same calendar day. Different
    # orderings (MM/DD vs DD/MM) or century readings can yield the identical
    # concrete date (e.g. 07/07/2026); once the day is known, "Don't Guess"
    # is satisfied and the outcome is CANONICALIZED, not AMBIGUOUS (spec §5).
    _seen_days: set[tuple[int, int, int]] = set()
    _deduped: list[_Survivor] = []
    for _s in survivors:
        _day_key = (_s.year, _s.month, _s.day)
        if _day_key not in _seen_days:
            _seen_days.add(_day_key)
            _deduped.append(_s)
    return _deduped, drop_reasons


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: set[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome (spec §7).

    Returns a 4-tuple ``(status, value, evidence, candidates)``. The
    ``candidates`` element is the sorted tuple of every surviving canonical
    form when the outcome is ``AMBIGUOUS`` (spec §2.4 — surface the
    ambiguity instead of guessing), and ``None`` otherwise.
    """
    if not candidates:
        # No interpretation was recognised for this value (the grammar layer
        # returned no shape match). The capability claimed the contract but
        # could not recognise the value, so it is INVALID, not UNSUPPORTED
        # (Decision A — UNSUPPORTED is reserved for non-string / wrong-contract
        # inputs that were never this capability's to claim).
        return Status.INVALID, None, (_evidence("unrecognized_format"),), None
    if not survivors:
        if "rejected_two_digit_year" in drop_reasons:
            return Status.INVALID, None, (_evidence("rejected_two_digit_year"),), None
        if "weekday_contradicts_date" in drop_reasons:
            return Status.INVALID, None, (_evidence("weekday_contradicts_date"),), None
        return Status.INVALID, None, (_evidence("invalid_calendar_date"),), None
    if len(survivors) == 1:
        s = survivors[0]
        return (
            Status.CANONICALIZED,
            _render_date(datetime(s.year, s.month, s.day)),
            (_evidence(s.rule),),
            None,
        )
    # >1 survivor -> AMBIGUOUS (Don't Guess). Surface every candidate.
    rules: list[str] = []
    orderings = {s.ordering for s in survivors if s.ordering is not None}
    if "MD" in orderings and "DM" in orderings:
        rules.append("ambiguous_ordering")
    if any(s.century_ambiguous for s in survivors):
        rules.append("ambiguous_two_digit_year")
    if not rules:
        rules.append("ambiguous_ordering")
    rendered = tuple(
        sorted(_render_date(datetime(s.year, s.month, s.day)) for s in survivors)
    )
    return Status.AMBIGUOUS, None, tuple(_evidence(rule) for rule in rules), rendered


class DateCapability:
    """A pure deterministic transformation that canonicalizes dates.

    Mandate alignment:
    - Law 8a: every method is a pure function of its arguments.
    - Law 14: every rule cites a source via ``_RULE_PROVENANCE``.
    """

    name: str = "date_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        """Return ``True`` when the contract is a date contract and value is a string.

        Args:
            contract: The contract to check.
            value: The input value to check.

        Returns:
            ``True`` if this capability can handle the (contract, value) pair.
        """
        return isinstance(contract, CanonicalDateContract) and isinstance(value, str)

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        """Canonicalize a date string according to the contract's locale policy.

        The capability recognises several input families; each is matched by a
        deterministic predicate — never by guessing (Law 4):

        * ISO 8601 date ``YYYY-MM-DD`` (all locales).
        * ISO 8601 date-time ``YYYY-MM-DDTHH:MM:SS[.ffffff][Z|±HH:MM]``; a
          datetime without a zone is reported ``AMBIGUOUS`` (RFC 3339 §5.6).
        * Multilingual text-month dates, e.g. ``16 July 2026`` (en),
          ``16. Juli 2026`` (de), ``16 Julai 2026`` (ms), ``July 16, 2026``,
          ``the 3rd of July, 2026``, ``16 July 2026 AD`` — full or abbreviated
          month names in the contract's declared ``language``.
        * Ordinal forms (``16th July 2026``) and weekday-prefixed RFC 2822
          forms (``Tue, 01 Jan 2025``).
        * Numeric slash forms: US ``MM/DD/YYYY`` (locale ``"US"``) / EU
          ``DD/MM/YYYY`` (locale ``"EU"``); a 2-digit year is ``AMBIGUOUS``.
          Year-first ``YYYY/MM/DD`` is a fixed Y/M/D reading accepted under
          every locale (ISO 8601 slash ordering).
        * Unix epoch seconds (integer or float, rendered in UTC/Z).

        ``locale="ISO"`` enumerates both MM/DD and DD/MM orderings for
        ambiguous slash forms (so they report ``AMBIGUOUS`` rather than being
        guessed); ``"US"`` and ``"EU"`` accept only their numeric reading. The
        canonical form is ``YYYY-MM-DD`` for dates and
        ``YYYY-MM-DDTHH:MM:SS[.ffffff]Z`` for datetimes (RFC 3339, normalised
        to UTC).

        Args:
            value: The input date string.
            contract: A ``CanonicalDateContract`` declaring the locale policy.

        Returns:
            A ``CapabilityResult`` with the canonicalized value and evidence.
        """
        if not isinstance(contract, CanonicalDateContract):
            # Genuine UNSUPPORTED: the contract was never a date contract, so
            # this capability should not have claimed it (Decision A).
            return CapabilityResult(
                status=Status.UNSUPPORTED,
                evidence=(_evidence("not_a_date_contract"),),
            )
        if not isinstance(value, str):
            # Genuine UNSUPPORTED: a non-string value is not this capability's
            # to claim (Decision A). UNSUPPORTED is reserved for non-string /
            # wrong-contract inputs; a string the grammar cannot recognise is
            # INVALID (see the enumeration fallback below).
            return CapabilityResult(
                status=Status.UNSUPPORTED,
                evidence=(_evidence("not_a_string_value"),),
            )
        if not value.strip():
            return CapabilityResult(
                status=Status.MISSING,
                evidence=(_evidence("empty_value"),),
            )

        # Dispatch order (MANDATE §6.4 / spec §6.1): Unix epoch -> ISO -> numeric
        # -> RFC 2822. The spec lists RFC 2822 before ISO, but the grammars are
        # disjoint (no single input matches two), so the order is not observable
        # in the output. Every branch is a deterministic predicate, never a
        # scored guess.
        # Unix epoch: integer or float seconds since 1970-01-01T00:00:00Z
        if _is_epoch(value):
            ts = float(value)
            try:
                dt = datetime.fromtimestamp(ts, tz=UTC)
            except (ValueError, OverflowError, OSError):
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("invalid_epoch_value"),),
                )
            return CapabilityResult(
                status=Status.CANONICALIZED,
                value=_render_datetime(dt),
                evidence=(
                    _evidence("parsed_unix_timestamp"),
                    _evidence("normalized_to_utc"),
                ),
            )

        # ISO 8601 date: YYYY-MM-DD
        if _ISO_DATE_RE.match(value):
            try:
                dt = datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("invalid_calendar_date"),),
                )
            return CapabilityResult(
                status=Status.CANONICALIZED,
                value=_render_date(dt),
                evidence=(_evidence("parsed_iso_date"),),
            )

        # ISO 8601 datetime with timezone: YYYY-MM-DDTHH:MM:SS[.fff](Z|±HH:MM)
        if _ISO_DATETIME_RE.match(value):
            iso = value.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso)
            except ValueError:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("invalid_iso_format"),),
                )
            already = value == _render_datetime(dt)
            return CapabilityResult(
                status=Status.CANONICALIZED,
                value=_render_datetime(dt),
                evidence=(
                    _evidence("parsed_iso_datetime"),
                    _evidence("normalized_to_utc"),
                )
                if not already
                else (_evidence("no_transformation_needed"),),
            )

        # ISO 8601 naive datetime (no timezone — ambiguous per RFC 3339 §5.6)
        if _ISO_NAIVE_DATETIME_RE.match(value):
            return CapabilityResult(
                status=Status.AMBIGUOUS,
                evidence=(_evidence("ambiguous_naive_datetime"),),
            )

        # US/EU numeric: MM/DD/YYYY or DD/MM/YYYY
        if contract.locale in ("US", "EU"):
            m2 = _NUMERIC_2YEAR_RE.match(value)
            m4 = _NUMERIC_4YEAR_RE.match(value)
            if m2 and not m4:
                a, b, _yy = m2.groups()
                month = int(a) if contract.locale == "US" else int(b)
                day = int(b) if contract.locale == "US" else int(a)
                # Validate the month/day before reporting a century-ambiguous
                # reading: a 2-digit year with an impossible month/day names no
                # calendar day (spec §8, e.g. 16/07/26 under US -> INVALID).
                if not (1 <= month <= 12) or not (1 <= day <= 31):
                    return CapabilityResult(
                        status=Status.INVALID,
                        evidence=(_evidence("invalid_calendar_date"),),
                    )
                # Apply the declared century policy (spec §3.2) before falling
                # back to the century-ambiguous AMBIGUOUS reading.
                if contract.two_digit_year in ("reject", "require_four_digit_year"):
                    return CapabilityResult(
                        status=Status.INVALID,
                        evidence=(_evidence("rejected_two_digit_year"),),
                    )
                if contract.two_digit_year is not None:
                    # pivot:YYYY -> resolve a single century.
                    year = _resolve_pivot_year(int(_yy), contract.two_digit_year)
                    if not _valid_calendar_date(year, month, day):
                        return CapabilityResult(
                            status=Status.INVALID,
                            evidence=(_evidence("invalid_calendar_date"),),
                        )
                    dt = datetime(year, month, day)
                    rule = "parsed_us_numeric" if contract.locale == "US" else "parsed_eu_numeric"
                    return CapabilityResult(
                        status=Status.CANONICALIZED,
                        value=_render_date(dt),
                        evidence=(_evidence(rule),),
                    )
                # No declared policy -> the century is ambiguous. Surface every
                # century-expanded reading as candidates (spec §2.4).
                yy = int(_yy)
                expanded: list[str] = []
                for century in (1900, 2000, 2100):
                    year = century + yy
                    if _valid_calendar_date(year, month, day):
                        expanded.append(_render_date(datetime(year, month, day)))
                return CapabilityResult(
                    status=Status.AMBIGUOUS,
                    evidence=(_evidence("ambiguous_two_digit_year"),),
                    candidates=tuple(sorted(expanded)),
                )
            if m4:
                a, b, y = m4.groups()
                month = int(a) if contract.locale == "US" else int(b)
                day = int(b) if contract.locale == "US" else int(a)
                year = int(y)
                if not _valid_calendar_date(year, month, day):
                    return CapabilityResult(
                        status=Status.INVALID,
                        evidence=(_evidence("invalid_calendar_date"),),
                    )
                dt = datetime(year, month, day)
                rule = "parsed_us_numeric" if contract.locale == "US" else "parsed_eu_numeric"
                return CapabilityResult(
                    status=Status.CANONICALIZED,
                    value=_render_date(dt),
                    evidence=(_evidence(rule),),
                )

        # RFC 2822: "1 Jan 2025", "Tue, 01 Jan 2025 12:00:00 +0000"
        if _RFC2822_RE.match(value):
            has_time = bool(_RFC2822_TIME_RE.search(value))
            if not has_time:
                # Date-only RFC 2822: parsedate_to_datetime requires time,
                # so use the locale-independent helper for the "D Mon YYYY"
                # form. Strip optional day-of-week prefix (e.g. "Tue, ") first.
                date_part = re.sub(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*", "", value.strip())
                parsed = _parse_rfc2822_date_only(date_part)
                if parsed is None:
                    return CapabilityResult(
                        status=Status.INVALID,
                        evidence=(_evidence("invalid_calendar_date"),),
                    )
                return CapabilityResult(
                    status=Status.CANONICALIZED,
                    value=_render_date(parsed),
                    evidence=(_evidence("parsed_rfc2822"),),
                )
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("invalid_calendar_date"),),
                )
            if parsed.tzinfo is None:
                return CapabilityResult(
                    status=Status.AMBIGUOUS,
                    evidence=(_evidence("ambiguous_naive_datetime"),),
                )
            return CapabilityResult(
                status=Status.CANONICALIZED,
                value=_render_datetime(parsed),
                evidence=(
                    _evidence("parsed_rfc2822"),
                    _evidence("normalized_to_utc"),
                ),
            )

        # Enumeration pipeline: text-month + numeric slash forms. This replaces
        # the old UNSUPPORTED fallback for date-shaped inputs (spec §2): every
        # interpretation the declared policies permit is enumerated, validated,
        # and classified (Don't Guess -> AMBIGUOUS when >1 survives).
        #
        # Recognition now routes through the grammar layer
        # (:func:`grammar.recognize`); if it returns no shape match the value
        # was claimed but not recognised, so the outcome is INVALID (Decision A
        # — not UNSUPPORTED, which is reserved for non-string / wrong-contract).
        candidates = generate_interpretations(value, contract)
        if candidates:
            survivors, drop_reasons = resolve_and_validate(candidates, contract)
            status, rendered, evidence, cands = classify(candidates, survivors, drop_reasons)
            return CapabilityResult(
                status=status, value=rendered, evidence=evidence, candidates=cands
            )

        return CapabilityResult(
            status=Status.INVALID,
            evidence=(_evidence("unrecognized_format"),),
        )

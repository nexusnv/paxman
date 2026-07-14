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
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from types import MappingProxyType

from paxman._contracts.contract import CanonicalDateContract, Contract
from paxman._core.types import CapabilityResult, Evidence, Status

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
_ISO_NAIVE_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$")

_NUMERIC_4YEAR_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_NUMERIC_2YEAR_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")

_UNIX_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _is_epoch(value: str) -> bool:
    """A string is a Unix epoch timestamp when it is a negative integer
    (always an epoch, never a compact date), a float (fractional seconds),
    or a positive integer >= 1e9 seconds (year ~2001+). Shorter positive
    bare integers are compact-date shapes (spec §2.2, out of scope) and are
    deliberately NOT treated as epochs (Law 4 — do not guess intent).
    This boundary is a declared Paxman policy (spec §11).
    """
    if not _UNIX_RE.match(value):
        return False
    if value.startswith("-"):
        return True
    if "." in value:
        return True
    return int(value) >= 1_000_000_000

_RFC2822_TIME_RE = re.compile(r"\d{1,2}:\d{2}(:\d{2})?")
_RFC2822_RE = re.compile(
    r"^(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*)?"
    r"\d{1,2}\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"\d{4}"
    r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s+(?:[+-]\d{4}|[A-Z]{1,4}))?"
    r"|\s+\(?[A-Z]{2,4}\)?"
    r"|\s+[A-Z]{1,3})?"
    r"$"
)

_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # dispatch invariants (no provenance — Law 14 §3.6 allow-list)
        "not_a_date_contract": "",
        "not_a_string_value": "",
        "empty_value": "",
        "unrecognized_format": "",
        # rejecting rules
        "numeric_format_requires_us_or_eu_locale": (
            "paxman spec/date (ISO locale rejects slash forms; Law 7)"
        ),
        "invalid_iso_format": "ISO 8601:2004 §5.2.1",
        "invalid_calendar_date": "ISO 8601:2004 (Gregorian calendar validity)",
        "ambiguous_two_digit_year": (
            "ISO 8601:2004 (4-digit year required); Law 4 (century not uniquely determinable)"
        ),
        "ambiguous_naive_datetime": "RFC 3339 §5.6 (unknown local offset convention)",
        # transforming rules (success path)
        "parsed_iso_date": "ISO 8601:2004 §5.2.1",
        "parsed_iso_datetime": "RFC 3339",
        "parsed_us_numeric": "paxman spec/date (US MM/DD/YYYY reading)",
        "parsed_eu_numeric": "paxman spec/date (EU DD/MM/YYYY reading)",
        "parsed_rfc2822": "RFC 2822 §3.3",
        "parsed_unix_timestamp": "POSIX/IEEE 1003.1 (epoch seconds) + RFC 3339",
        "normalized_to_utc": "RFC 3339 §4.1 (instant equivalence) + §4.2 (Z designator)",
        "no_transformation_needed": "ISO 8601:2004 §5.2.1 / RFC 3339 (input already canonical)",
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an Evidence node for the given rule.

    Args:
        rule: The rule name; must be a key in ``_RULE_PROVENANCE``.
        detail: Optional human-readable detail string.

    Returns:
        An ``Evidence`` instance with provenance resolved from the map.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])


def _render_date(dt: datetime) -> str:
    """Render a date-only canonical string ``YYYY-MM-DD``.

    Args:
        dt: A datetime whose date portion is rendered.

    Returns:
        The ISO 8601 date string.
    """
    return dt.strftime("%Y-%m-%d")


def _render_datetime(dt: datetime) -> str:
    """Render a datetime in RFC 3339 UTC canonical form.

    Always normalises to UTC and appends the ``Z`` designator.
    Microseconds are included only when non-zero (RFC 3339 §5.6
    allows optional fractional seconds).

    Args:
        dt: A timezone-aware datetime.

    Returns:
        The RFC 3339 canonical string.
    """
    dt = dt.astimezone(UTC)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    if dt.microsecond:
        base += f".{dt.microsecond:06d}"
    return base + "Z"


def _valid_calendar_date(year: int, month: int, day: int) -> bool:
    """Check that (year, month, day) is a valid Gregorian calendar date.

    Args:
        year: Four-digit year.
        month: 1-12.
        day: 1-31.

    Returns:
        ``True`` if the date exists in the Gregorian calendar.
    """
    if month < 1 or month > 12 or day < 1:
        return False
    try:
        datetime(year, month, day)
        return True
    except ValueError:
        return False


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

        ISO 8601 date strings (``YYYY-MM-DD``) are accepted for all locales.
        US and EU numeric forms (``MM/DD/YYYY`` and ``DD/MM/YYYY``) will be
        added in a subsequent task; this skeleton handles only ISO parsing.

        Args:
            value: The input date string.
            contract: A ``CanonicalDateContract`` declaring the locale policy.

        Returns:
            A ``CapabilityResult`` with the canonicalized value and evidence.
        """
        if not isinstance(contract, CanonicalDateContract):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_date_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_string_value"),),
            )
        if not value.strip():
            return CapabilityResult(
                status=Status.MISSING,
                evidence=(_evidence("empty_value"),),
            )

        # Unix epoch: integer or float seconds since 1970-01-01T00:00:00Z
        if _is_epoch(value):
            ts = float(value)
            dt = datetime.fromtimestamp(ts, tz=UTC)
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
                return CapabilityResult(
                    status=Status.AMBIGUOUS,
                    evidence=(_evidence("ambiguous_two_digit_year"),),
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

        if contract.locale == "ISO" and (
            _NUMERIC_4YEAR_RE.match(value) or _NUMERIC_2YEAR_RE.match(value)
        ):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("numeric_format_requires_us_or_eu_locale"),),
            )

        # RFC 2822: "1 Jan 2025", "Tue, 01 Jan 2025 12:00:00 +0000"
        if _RFC2822_RE.match(value):
            has_time = bool(_RFC2822_TIME_RE.search(value))
            if not has_time:
                # Date-only RFC 2822: parsedate_to_datetime requires time,
                # so fall back to strptime for the "D Mon YYYY" form.
                # Strip optional day-of-week prefix (e.g. "Tue, ") first.
                date_part = re.sub(
                    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*", "", value.strip()
                )
                try:
                    parsed = datetime.strptime(date_part, "%d %b %Y")
                except ValueError:
                    parsed = None
                if parsed is not None:
                    return CapabilityResult(
                        status=Status.CANONICALIZED,
                        value=_render_date(parsed),
                        evidence=(_evidence("parsed_rfc2822"),),
                    )
            else:
                try:
                    parsed = parsedate_to_datetime(value)
                except (TypeError, ValueError):
                    parsed = None
                if parsed is not None:
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

        return CapabilityResult(
            status=Status.UNSUPPORTED,
            evidence=(_evidence("unrecognized_format"),),
        )

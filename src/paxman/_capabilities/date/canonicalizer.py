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

from paxman._capabilities.date.calendar import _valid_calendar_date
from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._capabilities.date.parser import (
    _ISO_DATE_RE,
    _ISO_DATETIME_RE,
    _ISO_NAIVE_DATETIME_RE,
    _NUMERIC_2YEAR_RE,
    _NUMERIC_4YEAR_RE,
    _RFC2822_RE,
    _RFC2822_TIME_RE,
    _SLASH_YEAR_FIRST_RE,
    _is_epoch,
)
from paxman._capabilities.date.rules import _evidence
from paxman._capabilities.date.value import _render_date, _render_datetime
from paxman._core.contracts import Contract
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


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

        The capability recognises five input families (spec §2.1); each is
        matched by a deterministic predicate — never by guessing (Law 4):

        * ISO 8601 date ``YYYY-MM-DD`` (all locales).
        * ISO 8601 date-time ``YYYY-MM-DDTHH:MM:SS[.ffffff][Z|±HH:MM]``; a
          datetime without a zone is reported ``AMBIGUOUS`` (RFC 3339 §5.6).
        * US numeric ``MM/DD/YYYY`` (locale ``"US"``) / EU numeric
          ``DD/MM/YYYY`` (locale ``"EU"``); a 2-digit year is ``AMBIGUOUS``.
        * RFC 2822 date-time (e.g. ``Tue, 01 Jan 2025 12:00:00 +0000``).
        * Unix epoch seconds (integer or float, rendered in UTC/Z).

        ``locale="ISO"`` rejects slash forms with ``Status.INVALID``; ``"US"``
        and ``"EU"`` additionally accept their numeric reading. The canonical
        form is ``YYYY-MM-DD`` for dates and
        ``YYYY-MM-DDTHH:MM:SS[.ffffff]Z`` for datetimes (RFC 3339, normalised
        to UTC).

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
            _NUMERIC_4YEAR_RE.match(value)
            or _NUMERIC_2YEAR_RE.match(value)
            or _SLASH_YEAR_FIRST_RE.match(value)
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
                date_part = re.sub(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*", "", value.strip())
                try:
                    parsed = datetime.strptime(date_part, "%d %b %Y")
                except ValueError:
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

        return CapabilityResult(
            status=Status.UNSUPPORTED,
            evidence=(_evidence("unrecognized_format"),),
        )

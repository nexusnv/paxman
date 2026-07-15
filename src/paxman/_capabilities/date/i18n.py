"""Capability-owned multilingual domain knowledge for date canonicalization.

This module is the date capability's *domain knowledge* (MANDATE Principle 4):
it decides **how** month/weekday names map to numbers. It does **not** decide
**which** language applies — that is the contract's ``language`` policy
(MANDATE Principle 5). No single RFC governs multilingual month names, so the
tables here are a declared Paxman policy (Law 14 source #3).

Keys are stored lower-cased; lookups lower-case the input token before
resolution so matching is case-insensitive and locale-deterministic (Law 7:
the process locale must never leak into canonicalization).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

# Per-language month-name -> month number (1-12).
# Each language carries its **full native name** plus the **3-letter English
# RFC 2822 abbreviation** (e.g. ``jul``) so that both native and RFC 2822
# inputs resolve under the same table.
MONTH_NAMES: Mapping[str, Mapping[str, int]] = MappingProxyType(
    {
        "en": MappingProxyType(
            {
                "january": 1,
                "jan": 1,
                "february": 2,
                "feb": 2,
                "march": 3,
                "mar": 3,
                "april": 4,
                "apr": 4,
                "may": 5,
                "june": 6,
                "jun": 6,
                "july": 7,
                "jul": 7,
                "august": 8,
                "aug": 8,
                "september": 9,
                "sep": 9,
                "sept": 9,
                "october": 10,
                "oct": 10,
                "november": 11,
                "nov": 11,
                "december": 12,
                "dec": 12,
            }
        ),
        "de": MappingProxyType(
            {
                "januar": 1,
                "jan": 1,
                "februar": 2,
                "feb": 2,
                "märz": 3,
                "mar": 3,
                "april": 4,
                "apr": 4,
                "mai": 5,
                "may": 5,
                "juni": 6,
                "jun": 6,
                "juli": 7,
                "jul": 7,
                "august": 8,
                "aug": 8,
                "september": 9,
                "sep": 9,
                "sept": 9,
                "oktober": 10,
                "okt": 10,
                "oct": 10,
                "november": 11,
                "nov": 11,
                "dezember": 12,
                "dez": 12,
                "dec": 12,
            }
        ),
        "ms": MappingProxyType(
            {
                "januari": 1,
                "jan": 1,
                "februari": 2,
                "feb": 2,
                "mac": 3,
                "mar": 3,
                "april": 4,
                "apr": 4,
                "mei": 5,
                "may": 5,
                "jun": 6,
                "julai": 7,
                "jul": 7,
                "ogos": 8,
                "aug": 8,
                "september": 9,
                "sep": 9,
                "sept": 9,
                "oktober": 10,
                "okt": 10,
                "oct": 10,
                "november": 11,
                "nov": 11,
                "disember": 12,
                "dis": 12,
                "dec": 12,
            }
        ),
    }
)

# Per-language weekday-name -> datetime.weekday() index (Monday = 0).
# Each language carries its **full native name** plus the **3-letter English
# RFC 2822 abbreviation** so weekday tokens validate under the declared
# language only (no cross-language guess, Law 7).
WEEKDAY_NAMES: Mapping[str, Mapping[str, int]] = MappingProxyType(
    {
        "en": MappingProxyType(
            {
                "monday": 0,
                "mon": 0,
                "tuesday": 1,
                "tue": 1,
                "tues": 1,
                "wednesday": 2,
                "wed": 2,
                "thursday": 3,
                "thu": 3,
                "thur": 3,
                "thurs": 3,
                "friday": 4,
                "fri": 4,
                "saturday": 5,
                "sat": 5,
                "sunday": 6,
                "sun": 6,
            }
        ),
        "de": MappingProxyType(
            {
                "montag": 0,
                "mon": 0,
                "dienstag": 1,
                "tue": 1,
                "mittwoch": 2,
                "wed": 2,
                "donnerstag": 3,
                "thu": 3,
                "freitag": 4,
                "fri": 4,
                "samstag": 5,
                "sat": 5,
                "sonntag": 6,
                "sun": 6,
            }
        ),
        "ms": MappingProxyType(
            {
                "isnin": 0,
                "mon": 0,
                "selasa": 1,
                "tue": 1,
                "rabu": 2,
                "wed": 2,
                "khamis": 3,
                "thu": 3,
                "jumaat": 4,
                "fri": 4,
                "sabtu": 5,
                "sat": 5,
                "ahad": 6,
                "sun": 6,
            }
        ),
    }
)

# The complete set of languages the date capability can read month/weekday
# names in. Also used by ``_build_date`` to validate the contract's
# ``language`` policy.
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(MONTH_NAMES)

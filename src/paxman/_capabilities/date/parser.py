"""Date parsing predicates and the Unix-epoch helper.

Migrated verbatim from ``paxman._capabilities.builtins.date``.
"""

from __future__ import annotations

import re

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
_ISO_NAIVE_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$")

_NUMERIC_4YEAR_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_NUMERIC_2YEAR_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")
_SLASH_YEAR_FIRST_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")

_UNIX_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _is_epoch(value: str) -> bool:
    """A string is a Unix epoch timestamp when it is a negative integer
    (always an epoch, never a compact date), a float (fractional seconds),
    or a positive integer >= 1e9 seconds (year ~2001+). Shorter positive
    bare integers are compact-date shapes (spec §2.2, out of scope) and are
    deliberately NOT treated as epochs (Law 4 — do not guess intent).
    This boundary is a declared Paxman policy (spec §11).

    Edge case (declared policy, spec §2.2/§11): a 10+ digit bare integer such
    as ``2025010101`` is >= 1e9 and is therefore read as an epoch. Compact-date
    shapes longer than 9 digits are out of scope; this is a deliberate,
    documented boundary rather than a guess.
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

"""Gregorian calendar validity helper.

Migrated verbatim from ``paxman._capabilities.builtins.date``.
"""

from __future__ import annotations

from datetime import datetime


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

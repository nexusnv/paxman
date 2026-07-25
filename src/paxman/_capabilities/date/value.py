"""Date canonical rendering helpers.

Migrated verbatim from ``paxman._capabilities.builtins.date``.
"""

from __future__ import annotations

from datetime import UTC, datetime


def _render_date(dt: datetime) -> str:
    """Render a date-only canonical string ``YYYY-MM-DD``.

    Args:
        dt: A datetime whose date portion is rendered.

    Returns:
        The ISO 8601 date string.

    Note: ``dt.strftime("%Y")`` does NOT zero-pad years below 1000 on
    glibc (it yields ``"1"`` for year 1, not ``"0001"``), which would
    violate the ``YYYY-MM-DD`` canonical form and break idempotence for
    AD 1-999. Format the year explicitly.
    """
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


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
    # Format the year explicitly: strftime("%Y") drops zero-padding below
    # AD 1000 on glibc, which would break the RFC 3339 canonical form.
    base = (
        f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
    )
    if dt.microsecond:
        base += f".{dt.microsecond:06d}"
    return base + "Z"


def _render_date_compact(dt: datetime) -> str:
    """Render a date-only compact string ``YYYYMMDD`` (ISO 8601 basic format).

    Args:
        dt: A datetime whose date portion is rendered.

    Returns:
        The compact ISO 8601 date string without separators.
    """
    return f"{dt.year:04d}{dt.month:02d}{dt.day:02d}"


def _render_datetime_compact(dt: datetime) -> str:
    """Render a datetime in compact RFC 3339 UTC form ``YYYYMMDDTHHMMSSZ``.

    Always normalises to UTC and appends the ``Z`` designator.
    Microseconds are included only when non-zero.

    Args:
        dt: A timezone-aware datetime.

    Returns:
        The compact RFC 3339 canonical string without date/time separators.
    """
    dt = dt.astimezone(UTC)
    base = f"{dt.year:04d}{dt.month:02d}{dt.day:02d}T{dt.hour:02d}{dt.minute:02d}{dt.second:02d}"
    if dt.microsecond:
        base += f".{dt.microsecond:06d}"
    return base + "Z"

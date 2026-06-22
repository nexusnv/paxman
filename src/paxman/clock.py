"""Injectable clock protocol and test fixture.

Production uses :class:`SystemClock`; tests inject :class:`FakeClock` with a
fixed time.  The replay path uses no clock at all.
"""

from __future__ import annotations

import datetime
import time
import typing

import attrs

__all__: list[str] = [
    "Clock",
    "FakeClock",
    "SystemClock",
]


class Clock(typing.Protocol):
    """Injectable time source for deterministic tests.

    Production uses ``SystemClock``; tests inject ``FakeClock`` with a fixed
    time. The replay path uses no clock at all.
    """

    def now(self) -> datetime.datetime:
        """Return the current UTC time as a timezone-aware datetime."""
        ...

    def monotonic(self) -> float:
        """Return a monotonically increasing seconds-since-epoch float.

        Distinct from ``now()`` so tests can fix wall-clock time while
        still advancing the monotonic counter.
        """
        ...


@attrs.frozen(slots=True)
class SystemClock:
    """Production clock. Reads system time."""

    def now(self) -> datetime.datetime:
        """Return current UTC time (timezone-aware).

        Returns:
            The current UTC time as a timezone-aware datetime.
        """
        return datetime.datetime.now(tz=datetime.UTC)

    def monotonic(self) -> float:
        """Return ``time.monotonic()`` seconds.

        Returns:
            Monotonic clock value in fractional seconds.
        """
        return time.monotonic()


@attrs.frozen(slots=True)
class FakeClock:
    """Test clock with a fixed time and a manually-advanced monotonic counter.

    Attributes:
        fixed_now: The wall-clock time returned by ``now()``.
        monotonic_value: The value returned by ``monotonic()``.
    """

    fixed_now: datetime.datetime = attrs.field(
        default=attrs.Factory(lambda: datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC))
    )
    monotonic_value: float = 0.0

    def now(self) -> datetime.datetime:
        """Return ``fixed_now`` (deterministic).

        Returns:
            The fixed wall-clock time set at construction.
        """
        return self.fixed_now

    def monotonic(self) -> float:
        """Return ``monotonic_value`` (deterministic).

        Returns:
            The fixed monotonic value set at construction.
        """
        return self.monotonic_value

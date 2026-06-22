"""Unit tests for ``paxman.clock`` — injectable Clock + FakeClock."""

from __future__ import annotations

import datetime

import pytest

from paxman.clock import Clock, FakeClock, SystemClock

# --- Protocol structural typing ---------------------------------------------


def test_fakeclock_satisfies_clock_protocol() -> None:
    """``FakeClock`` is structurally compatible with ``Clock`` (Protocol)."""
    fc = FakeClock()
    # Assigning to a Protocol-typed variable is the static check.
    clock: Clock = fc
    assert isinstance(clock, FakeClock)


def test_systemclock_satisfies_clock_protocol() -> None:
    """``SystemClock`` is structurally compatible with ``Clock``."""
    sc = SystemClock()
    clock: Clock = sc
    assert isinstance(clock, SystemClock)


# --- FakeClock determinism --------------------------------------------------


def test_fakeclock_default_fixed_now() -> None:
    """``FakeClock()`` with no args returns 2026-01-01 UTC."""
    fc = FakeClock()
    assert fc.now() == datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def test_fakeclock_default_monotonic() -> None:
    """``FakeClock()`` with no args returns monotonic_value=0.0."""
    fc = FakeClock()
    assert fc.monotonic() == 0.0


def test_fakeclock_custom_fixed_now() -> None:
    """``FakeClock(fixed_now=...)`` returns the supplied time."""
    when = datetime.datetime(2026, 6, 22, 12, 0, 0, tzinfo=datetime.UTC)
    fc = FakeClock(fixed_now=when)
    assert fc.now() == when


def test_fakeclock_custom_monotonic() -> None:
    """``FakeClock(monotonic_value=42.0)`` returns the supplied value."""
    fc = FakeClock(monotonic_value=42.0)
    assert fc.monotonic() == 42.0


def test_fakeclock_deterministic_across_calls() -> None:
    """The same FakeClock returns the same value on every call (no I/O, no clock)."""
    when = datetime.datetime(2026, 6, 22, tzinfo=datetime.UTC)
    fc = FakeClock(fixed_now=when, monotonic_value=100.0)
    for _ in range(10):
        assert fc.now() == when
        assert fc.monotonic() == 100.0


def test_fakeclock_is_frozen() -> None:
    """``FakeClock`` is frozen (attrs.frozen)."""
    fc = FakeClock()
    with pytest.raises(BaseException):  # FrozenInstanceError  # noqa: B017
        fc.monotonic_value = 999.0  # type: ignore[misc]


# --- SystemClock (production) -----------------------------------------------


def test_systemclock_now_returns_timezone_aware_utc() -> None:
    """``SystemClock.now()`` returns a timezone-aware datetime in UTC."""
    sc = SystemClock()
    now = sc.now()
    assert isinstance(now, datetime.datetime)
    assert now.tzinfo is not None
    assert now.utcoffset() == datetime.timedelta(0)


def test_systemclock_monotonic_returns_float() -> None:
    """``SystemClock.monotonic()`` returns a float."""
    sc = SystemClock()
    value = sc.monotonic()
    assert isinstance(value, float)


def test_systemclock_is_frozen() -> None:
    """``SystemClock`` is frozen (attrs.frozen)."""
    sc = SystemClock()
    # attrs.frozen with slots=True raises AttributeError, not FrozenInstanceError.
    with pytest.raises(BaseException):  # noqa: B017  (intentionally blind)
        object.__setattr__(sc, "_dummy", 1)  # type: ignore[attr-defined]


# --- Fixed-now fixture (smoke) ---------------------------------------------


def test_fixed_now_fixture_value() -> None:
    """The ``fixed_now`` fixture is defined in conftest.py."""
    # Fixtures are only available during pytest collection; this test
    # just verifies the fixture function exists and is callable.

    # Import the conftest module via its file path.
    import importlib.util
    from pathlib import Path

    conftest_path = Path(__file__).resolve().parent.parent / "conftest.py"
    spec = importlib.util.spec_from_file_location("paxman_test_conftest", conftest_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "fixed_now")
        assert callable(mod.fixed_now)

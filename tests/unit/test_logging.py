"""Unit tests for ``paxman.logging`` — structlog factory."""

from __future__ import annotations

import io
import json
import logging as stdlogging

import pytest

from paxman import logging as paxman_logging

# --- get_logger -------------------------------------------------------------


@pytest.mark.deterministic
def test_get_logger_with_name_returns_bound_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_logger("name")`` returns a BoundLogger."""
    # Reset the configuration state so we can call configure_logging again.
    monkeypatch.setattr(paxman_logging, "_configured", False)
    paxman_logging.configure_logging()
    logger = paxman_logging.get_logger("paxman.test")
    # ``structlog.stdlib.BoundLogger`` is the type.
    assert hasattr(logger, "info")
    assert hasattr(logger, "bind")


@pytest.mark.deterministic
def test_get_logger_with_none_returns_root_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_logger(None)`` returns the root logger."""
    monkeypatch.setattr(paxman_logging, "_configured", False)
    paxman_logging.configure_logging()
    logger = paxman_logging.get_logger(None)
    assert hasattr(logger, "info")


# --- configure_logging: level validation ------------------------------------


@pytest.mark.deterministic
def test_configure_logging_rejects_unknown_level(monkeypatch: pytest.MonkeyPatch) -> None:
    """``configure_logging(level="NOPE")`` raises ValueError."""
    monkeypatch.setattr(paxman_logging, "_configured", False)
    with pytest.raises(ValueError, match="Unknown log level"):
        paxman_logging.configure_logging(level="NOPE")


# --- replay_mode: NO timestamps ---------------------------------------------


@pytest.mark.deterministic
def test_replay_mode_omits_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    """In replay mode, log entries do NOT include a timestamp field (per §12.3)."""
    monkeypatch.setattr(paxman_logging, "_configured", False)
    paxman_logging.configure_logging(replay_mode=True, json_output=True)

    # Capture the stdlib logger output.
    buffer = io.StringIO()
    handler = stdlogging.StreamHandler(buffer)
    handler.setFormatter(stdlogging.Formatter("%(message)s"))
    stdlogging.getLogger().addHandler(handler)
    stdlogging.getLogger().setLevel(stdlogging.INFO)

    try:
        logger = paxman_logging.get_logger("paxman.replay_test")
        logger.info("replay event", key="value")
        handler.flush()
        raw = buffer.getvalue().strip()
    finally:
        stdlogging.getLogger().removeHandler(handler)

    # The JSON output (one record) must NOT contain "timestamp".
    record = json.loads(raw.splitlines()[-1])
    assert "timestamp" not in record
    assert record.get("event") == "replay event"
    assert record.get("key") == "value"


@pytest.mark.deterministic
def test_normal_mode_includes_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    """In normal mode (replay_mode=False), log entries DO include a timestamp."""
    monkeypatch.setattr(paxman_logging, "_configured", False)
    paxman_logging.configure_logging(replay_mode=False, json_output=True)

    buffer = io.StringIO()
    handler = stdlogging.StreamHandler(buffer)
    handler.setFormatter(stdlogging.Formatter("%(message)s"))
    stdlogging.getLogger().addHandler(handler)
    stdlogging.getLogger().setLevel(stdlogging.INFO)

    try:
        logger = paxman_logging.get_logger("paxman.normal_test")
        logger.info("normal event", key="value")
        handler.flush()
        raw = buffer.getvalue().strip()
    finally:
        stdlogging.getLogger().removeHandler(handler)

    record = json.loads(raw.splitlines()[-1])
    assert "timestamp" in record
    assert record.get("event") == "normal event"


# --- Idempotency -----------------------------------------------------------


@pytest.mark.deterministic
def test_configure_logging_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling ``configure_logging`` twice is a no-op (the second call has no effect)."""
    monkeypatch.setattr(paxman_logging, "_configured", False)
    paxman_logging.configure_logging(level="INFO", replay_mode=False)
    # Second call should not raise and should not re-configure.
    paxman_logging.configure_logging(level="DEBUG", replay_mode=True)
    # Verify _configured is still True (we didn't re-raise).
    assert paxman_logging._configured is True

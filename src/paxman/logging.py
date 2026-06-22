"""Structured, deterministic logging factory for the paxman engine.

Provides a thin wrapper around ``structlog`` so every subsystem emits
uniform, structured log entries.  This is a leaf module — it imports
nothing from ``paxman.*`` submodules.

Key constraint (``ARCHITECTURE.md`` §12.3): when *replay_mode* is
active, timestamps are **omitted** so that log output is
deterministic and cannot leak wall-clock information.
"""

from __future__ import annotations

import logging

import structlog
import structlog.contextvars
import structlog.dev
import structlog.processors
import structlog.stdlib
import structlog.types

__all__ = ["configure_logging", "get_logger"]

_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_configured: bool = False


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog bound logger.

    Args:
        name: Optional logger name.  When ``None`` (the default) the
            root paxman logger is returned.  When provided, a child
            logger with that name is returned (e.g. ``"paxman.planner"``).

    Returns:
        A ``structlog.stdlib.BoundLogger`` instance ready for use.
    """
    if name is None:
        return structlog.stdlib.get_logger()
    return structlog.stdlib.get_logger(name)


def configure_logging(
    level: str = "INFO",
    *,
    json_output: bool = False,
    replay_mode: bool = False,
) -> None:
    """Configure the global structlog processor chain.

    This function is idempotent — only the **first** call takes effect.
    Subsequent calls are no-ops so that library users who configure
    logging before calling ``paxman.normalize()`` are not overridden.

    Args:
        level: Log level as a string.  One of ``"DEBUG"``, ``"INFO"``,
            ``"WARNING"``, ``"ERROR"``, or ``"CRITICAL"``.  Defaults to
            ``"INFO"``.
        json_output: If ``True``, render log entries as single-line JSON
            (``structlog.processors.JSONRenderer``).  If ``False``
            (default), use the coloured console renderer
            (``structlog.dev.ConsoleRenderer``).
        replay_mode: If ``True``, timestamps are **excluded** from log
            output so that replay runs are fully deterministic
            (``ARCHITECTURE.md`` §12.3).  Defaults to ``False``.

    Raises:
        ValueError: If *level* is not a recognised log-level name.
    """
    global _configured

    if _configured:
        return

    if level not in _LEVELS:
        raise ValueError(f"Unknown log level: {level!r}")

    numeric_level = _LEVELS[level]
    logging.basicConfig(level=numeric_level, force=True)

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.add_log_level,
    ]

    if not replay_mode:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )
    processors.append(renderer)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True

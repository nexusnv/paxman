"""Structured, deterministic logging factory for the paxman engine.

Provides a thin wrapper around ``structlog`` so every subsystem emits
uniform, structured log entries.  This is a leaf module — it imports
nothing from ``paxman.*`` submodules.

Key constraint (``ARCHITECTURE.md`` §12.3): when *replay_mode* is
active, timestamps are **omitted** so that log output is
deterministic and cannot leak wall-clock information.

Redaction (V1.2.0, design spec #50 §7)
-------------------------------------

Real inference providers carry API keys in HTTP headers and JSON
bodies. To prevent accidental key leakage, every log event is run
through a redact processor (added in V1.2.0) that masks the value of
any key in :data:`REDACT_KEYS`. The match is case-insensitive
(HTTP headers are case-insensitive).

The redact infrastructure is intentionally **additive** — it is
applied to every event regardless of whether the calling code opts
in. The mask sentinel is ``"***"``. The default :data:`REDACT_KEYS`
covers:

- ``"api_key"`` — generic JSON body key
- ``"authorization"`` — HTTP ``Authorization`` header
- ``"bearer"`` — HTTP ``Authorization: Bearer ...`` token fragment
- ``"x-api-key"`` — OpenAI / OpenAI-compatible provider API key header
- ``"x-anthropic-api-key"`` — Anthropic provider API key header

Callers may pass a custom key set to :func:`configure_logging` to
extend (or shrink) the default. The redact processor always runs
*after* the contextvars merge and the log-level filter, so the mask
is present in the rendered output.
"""

from __future__ import annotations

import logging
import typing

import structlog
import structlog.contextvars
import structlog.dev
import structlog.processors
import structlog.stdlib
import structlog.types

__all__ = [
    "REDACT_KEYS",
    "REDACT_SENTINEL",
    "configure_logging",
    "get_logger",
    "make_redact_processor",
    "redact_value",
]

# The default set of redact keys (V1.2.0). Additive — older keys
# (``api_key``, ``authorization``, ``bearer``) are preserved verbatim
# from the design spec #50 §7; the two V1.2.0 additions cover the
# OpenAI-compatible and Anthropic wire formats.
REDACT_KEYS: typing.Final[frozenset[str]] = frozenset(
    {
        "api_key",
        "authorization",
        "bearer",
        "x-api-key",
        "x-anthropic-api-key",
    },
)

# The mask value substituted for any redacted key. A short, recognisable
# sentinel that does not collide with real secret values.
REDACT_SENTINEL: typing.Final[str] = "***"

_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_configured: bool = False


def redact_value(
    event_dict: dict[str, typing.Any],
    keys: typing.Iterable[str] = REDACT_KEYS,
) -> dict[str, typing.Any]:
    """Return a copy of ``event_dict`` with matching-key values masked.

    The match is **case-insensitive and separator-insensitive**
    (HTTP headers are case-insensitive; structlog's
    snake-case-to-header-name convention converts ``x-api-key`` to
    ``x_api_key`` at the call site, so a case-only match would let
    ``"x_api_key"`` slip through). Both the configured keys and the
    event-dict keys are normalized by lowercasing and replacing any
    ``-`` with ``_`` before the O(1) set lookup.

    The helper is pure: it does not mutate its input and is safe to
    call from any thread. Nested ``dict`` and ``list`` values are
    walked recursively; non-collection values are masked in place
    only when the key matches.

    Args:
        event_dict: The event payload to redact.
        keys: The set of key names to mask. Defaults to
            :data:`REDACT_KEYS`.

    Returns:
        A new ``dict`` with redacted values. The original
        ``event_dict`` is not mutated.
    """

    def _normalize(name: str) -> str:
        return name.lower().replace("-", "_")

    # Normalize the configured keys once. ``frozenset.__contains__``
    # is O(1) so this is the fast path for the common case.
    lowered: frozenset[str] = frozenset(_normalize(k) for k in keys)

    def _walk(
        obj: typing.Any,  # noqa: ANN401
    ) -> typing.Any:  # noqa: ANN401
        """Recursively walk a (possibly nested) event value.

        ``typing.Any`` is used here because the value type is
        genuinely unknown at this level — the function dispatches
        by runtime type via ``isinstance``, and the union of
        ``dict``/``list``/``tuple``/scalar would require a complex
        TypeVar. ANN401 is suppressed for this nested helper.
        """
        if isinstance(obj, dict):
            return {
                k: (REDACT_SENTINEL if _normalize(k) in lowered else _walk(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(_walk(v) for v in obj)
        return obj

    return _walk(event_dict)  # type: ignore[no-any-return]


def make_redact_processor(
    keys: typing.Iterable[str] = REDACT_KEYS,
) -> structlog.types.Processor:
    """Return a ``structlog`` processor that redacts ``keys`` in place.

    The returned callable matches the
    :data:`structlog.types.Processor` contract:
    ``(logger, method_name, event_dict) -> event_dict``.

    Args:
        keys: The set of key names to mask. Defaults to
            :data:`REDACT_KEYS`. The match is case-insensitive on
            the key.

    Returns:
        A processor that mutates ``event_dict`` in place and returns
        it. The structlog pipeline calls the processor with the
        logger name, the method name, and the event dict.
    """

    def _processor(
        logger: typing.Any,  # noqa: ANN401
        method_name: str,
        event_dict: dict[str, typing.Any],
    ) -> dict[str, typing.Any]:
        """The structlog processor entry point. The ``logger``
        parameter is unused (the redact filter does not need a
        logger reference); we accept it for protocol conformance.
        """
        del logger  # explicitly unused; satisfies the contract
        del method_name  # explicitly unused; satisfies the contract
        redacted = redact_value(event_dict, keys)
        # Mutate in place to satisfy the structlog contract (the
        # pipeline reuses the dict across processors).
        event_dict.clear()
        event_dict.update(redacted)
        return event_dict

    return _processor  # type: ignore[return-value]


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
    redact_keys: typing.Iterable[str] | None = None,
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
        redact_keys: Optional iterable of additional key names to
            mask in event payloads, beyond the V1.2.0 default
            :data:`REDACT_KEYS`. The match is case-insensitive on the
            key. Pass an empty iterable to disable redaction entirely
            (not recommended in production). Defaults to ``None``
            (use the default :data:`REDACT_KEYS`).

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

    # Build the redact key set: defaults + caller overrides. The
    # caller may extend (default + extras) by passing extras, or
    # disable redaction entirely by passing an empty iterable. The
    # default behaviour is to redact all five V1.2.0 keys.
    if redact_keys is None:
        effective_keys: frozenset[str] = REDACT_KEYS
    else:
        effective_keys = frozenset(REDACT_KEYS) | frozenset(redact_keys)
    redact_processor: structlog.types.Processor = make_redact_processor(effective_keys)

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.add_log_level,
    ]

    # The redact processor runs *before* the renderer so the rendered
    # output never contains a leaked key. It runs in both replay_mode
    # and not — secrets must never appear in logs, replayed or not.
    if effective_keys:
        processors.append(redact_processor)

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

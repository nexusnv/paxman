"""Tests for the V1.2.0 logging REDACT_KEYS extension (spec #50 §7).

The redact infrastructure is introduced in V1.2.0 alongside the
real inference providers. The constant ``REDACT_KEYS`` is a
``frozenset[str]`` of header / field names whose values must be
silently masked in log output. The default set covers:

- ``"api_key"`` — generic JSON body key
- ``"authorization"`` — HTTP ``Authorization`` header (case-sensitive)
- ``"bearer"`` — HTTP ``Authorization: Bearer ...`` token fragment
- ``"x-api-key"`` — OpenAI / OpenAI-compatible provider API key header
- ``"x-anthropic-api-key"`` — Anthropic provider API key header

The test asserts:

1. The constant exists at the documented import path.
2. The five V1.2.0 keys are members.
3. The constant is a ``frozenset`` of strings (immutable + iterable).
4. ``redact_value`` masks the value of any matching key in a dict
   event, recursively, leaving non-matching keys untouched.
5. ``redact_value`` is case-insensitive on the key (HTTP headers are
   case-insensitive; matching them case-sensitively would let a
   leak through ``"X-API-Key"``).
6. The redact helper handles nested dicts and lists.
7. The processor returned by ``make_redact_processor`` is a
   ``structlog.types.Processor`` (callable taking ``logger``,
   ``method_name``, ``event_dict``).
"""

from __future__ import annotations

import pytest

from paxman.logging import (
    REDACT_KEYS,
    make_redact_processor,
    redact_value,
)


class TestRedactKeysV120:
    """V1.2.0 introduces the redact infrastructure for inference providers."""

    def test_redact_keys_constant_is_frozenset(self) -> None:
        assert isinstance(REDACT_KEYS, frozenset)
        for k in REDACT_KEYS:
            assert isinstance(k, str)

    @pytest.mark.parametrize(
        "key",
        [
            "api_key",
            "authorization",
            "bearer",
            "x-api-key",
            "x-anthropic-api-key",
        ],
    )
    def test_redact_keys_contains_required(self, key: str) -> None:
        assert key in REDACT_KEYS, f"REDACT_KEYS must include {key!r}"

    def test_redact_keys_has_at_least_five_members(self) -> None:
        assert len(REDACT_KEYS) >= 5


class TestRedactValue:
    """``redact_value`` is a pure helper that masks the value of any
    matching key (case-insensitive) in a dict, recursively."""

    def test_redacts_matching_key(self) -> None:
        out = redact_value({"x-api-key": "sk-secret-123", "model": "gpt-4o"}, REDACT_KEYS)
        assert out["x-api-key"] == "***"
        assert out["model"] == "gpt-4o"

    def test_leaves_non_matching_key(self) -> None:
        out = redact_value({"foo": "bar", "baz": 42}, REDACT_KEYS)
        assert out == {"foo": "bar", "baz": 42}

    def test_case_insensitive_match(self) -> None:
        out = redact_value(
            {"X-API-Key": "secret", "Authorization": "Bearer abc"},
            REDACT_KEYS,
        )
        assert out["X-API-Key"] == "***"
        assert out["Authorization"] == "***"

    def test_redacts_nested_dict(self) -> None:
        out = redact_value(
            {"outer": {"x-api-key": "secret", "ok": 1}},
            REDACT_KEYS,
        )
        assert out["outer"]["x-api-key"] == "***"
        assert out["outer"]["ok"] == 1

    def test_redacts_list_of_dicts(self) -> None:
        out = redact_value(
            {"items": [{"api_key": "k1"}, {"api_key": "k2"}, {"safe": "v"}]},
            REDACT_KEYS,
        )
        assert out["items"][0]["api_key"] == "***"
        assert out["items"][1]["api_key"] == "***"
        assert out["items"][2]["safe"] == "v"

    def test_empty_dict(self) -> None:
        assert redact_value({}, REDACT_KEYS) == {}


class TestMakeRedactProcessor:
    """``make_redact_processor`` returns a structlog ``Processor``
    (callable ``(logger, method_name, event_dict) -> event_dict``)."""

    def test_returns_callable(self) -> None:
        proc = make_redact_processor(REDACT_KEYS)
        assert callable(proc)

    def test_processor_redacts_event_dict(self) -> None:
        proc = make_redact_processor(REDACT_KEYS)
        event_dict = {"x-api-key": "sk-secret", "model": "gpt-4o"}
        out = proc(None, "info", event_dict)
        assert out["x-api-key"] == "***"
        assert out["model"] == "gpt-4o"

    def test_processor_returns_event_dict(self) -> None:
        proc = make_redact_processor(REDACT_KEYS)
        event_dict = {"foo": "bar"}
        out = proc(None, "info", event_dict)
        assert out == {"foo": "bar"}

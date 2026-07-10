"""Tests for ProviderRegistry (V1.2.0 design spec #50 §4, D10, D11, D18).

Per design spec #50 §4 (D10): ProviderRegistry is a class, not a
global singleton. The class supports ``register``, ``resolve``,
``get``, ``clear``, ``__contains__``, and ``__len__``; all mutating
and read methods are guarded by a re-entrant lock (D18).
"""
from __future__ import annotations

import pytest

from paxman.errors import ConfigurationError
from paxman.providers._model import ModelRef, ProviderRegistry


class _StubProvider:
    """Minimal Provider for testing the registry's structural checks."""

    def __init__(self, name: str = "stub", capabilities: frozenset | None = None) -> None:
        self.name = name
        self.capabilities = capabilities or frozenset({"text"})

    def complete(self, request):  # pragma: no cover - not exercised
        raise NotImplementedError


class TestProviderRegistryBasics:
    """The registry is a class, not a singleton. Each instance has its own state."""

    def test_empty(self) -> None:
        reg = ProviderRegistry()
        assert len(reg) == 0
        assert "anything" not in reg

    def test_register_and_get(self) -> None:
        reg = ProviderRegistry()
        provider = _StubProvider(name="stub")
        reg.register("stub", provider)
        assert len(reg) == 1
        assert "stub" in reg
        assert reg.get("stub") is provider

    def test_register_rejects_duplicate_without_replace(self) -> None:
        reg = ProviderRegistry()
        reg.register("stub", _StubProvider())
        with pytest.raises(ConfigurationError) as exc_info:
            reg.register("stub", _StubProvider())
        assert exc_info.value.error_code == "PROVIDER_ALREADY_REGISTERED"

    def test_register_allows_replace_with_flag(self) -> None:
        reg = ProviderRegistry()
        a = _StubProvider(name="a")
        b = _StubProvider(name="b")
        reg.register("k", a)
        reg.register("k", b, replace=True)
        assert reg.get("k") is b

    def test_get_unknown_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(ConfigurationError) as exc_info:
            reg.get("nope")
        assert exc_info.value.error_code == "INFERENCE_PROVIDER_NOT_REGISTERED"
        assert exc_info.value.context == {"name": "nope"}

    def test_resolve_by_modelref(self) -> None:
        reg = ProviderRegistry()
        provider = _StubProvider(name="openai")
        reg.register("openai", provider)
        ref = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        assert reg.resolve(ref) is provider

    def test_resolve_unknown_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(ConfigurationError) as exc_info:
            reg.resolve(ModelRef(provider="nope", model="x"))
        assert exc_info.value.error_code == "INFERENCE_PROVIDER_NOT_REGISTERED"
        assert exc_info.value.context == {"name": "nope", "model": "x"}

    def test_clear(self) -> None:
        reg = ProviderRegistry()
        reg.register("a", _StubProvider(name="a"))
        reg.register("b", _StubProvider(name="b"))
        assert len(reg) == 2
        reg.clear()
        assert len(reg) == 0
        assert "a" not in reg

    def test_instances_are_independent(self) -> None:
        """D10: each ProviderRegistry is a class instance, not a global."""
        r1 = ProviderRegistry()
        r2 = ProviderRegistry()
        r1.register("x", _StubProvider())
        assert "x" in r1
        assert "x" not in r2

    def test_register_validates_name(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(ValueError, match="name"):
            reg.register("", _StubProvider())
        with pytest.raises(ValueError, match="name"):
            reg.register(123, _StubProvider())  # type: ignore[arg-type]

    def test_register_validates_provider_protocol(self) -> None:
        reg = ProviderRegistry()
        # No name, no capabilities, no complete
        with pytest.raises(TypeError):
            reg.register("x", object())
        # name missing
        with pytest.raises(TypeError):
            reg.register("x", type("NoName", (), {"capabilities": frozenset(), "complete": lambda r: None})())
        # name not a str
        with pytest.raises(TypeError):
            reg.register("x", type("BadName", (), {"name": 42, "capabilities": frozenset(), "complete": lambda r: None})())
        # capabilities missing
        with pytest.raises(TypeError):
            reg.register("x", type("NoCaps", (), {"name": "y", "complete": lambda r: None})())
        # complete missing
        with pytest.raises(TypeError):
            reg.register("x", type("NoComplete", (), {"name": "y", "capabilities": frozenset()})())

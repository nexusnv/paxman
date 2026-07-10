"""Tests for the Provider Protocol (V1.2.0 design spec #50 §4).

Per design spec #50 §11 (D18), the Provider Protocol is structural
(``typing.Protocol``); conformance is checked at registration time
(via :meth:`ProviderRegistry._validate_provider`), not at type-check
time. The Protocol's docstring is the single source of truth for
the thread-safety and determinism contracts.

This test module asserts:

1. The Protocol is importable at the documented path.
2. The docstring explicitly documents thread-safety, the ``name``
   attribute, and the ``capabilities`` attribute (the per-spec
   invariants).
3. A class that structurally conforms to the Protocol is accepted by
   :meth:`ProviderRegistry.register` without raising.
"""
from __future__ import annotations

import pytest

from paxman.capabilities.v1.inference import Completion, CompletionRequest
from paxman.providers._provider import Provider


class _ConformingProvider:
    """A minimal class that conforms to the Provider Protocol structurally."""

    def __init__(self) -> None:
        self.name = "test"
        self.capabilities: frozenset[str] = frozenset({"text", "json_mode"})

    def complete(self, request: CompletionRequest) -> Completion:
        return Completion(text="ok", model="test-model")


class _MissingName:
    def __init__(self) -> None:
        self.capabilities: frozenset[str] = frozenset({"text"})

    def complete(self, request: CompletionRequest) -> Completion:
        return Completion(text="ok", model="x")


class _MissingCapabilities:
    def __init__(self) -> None:
        self.name = "x"

    def complete(self, request: CompletionRequest) -> Completion:
        return Completion(text="ok", model="x")


class _MissingComplete:
    def __init__(self) -> None:
        self.name = "x"
        self.capabilities: frozenset[str] = frozenset({"text"})


class TestProviderProtocol:
    """The Protocol is structural; conformance is checked at registration time
    (see :meth:`ProviderRegistry._validate_provider`), not at type-check time.
    These tests assert the docstring is the single source of truth for the
    thread-safety and surface contracts.
    """

    def test_protocol_docstring_states_thread_safety(self) -> None:
        """D18: the Protocol's docstring must document the thread-safety
        contract. This is the single source of truth."""
        doc = Provider.__doc__ or ""
        assert "thread" in doc.lower(), (
            "Provider Protocol docstring must document thread-safety"
        )

    def test_protocol_docstring_states_name_field(self) -> None:
        doc = Provider.__doc__ or ""
        assert "name" in doc.lower(), (
            "Provider Protocol docstring must mention the 'name' attribute"
        )

    def test_protocol_docstring_states_capabilities_field(self) -> None:
        doc = Provider.__doc__ or ""
        assert "capabilities" in doc.lower(), (
            "Provider Protocol docstring must mention the 'capabilities' attribute"
        )

    def test_protocol_docstring_states_determinism_contract(self) -> None:
        """D18 includes a determinism contract: ``complete()`` is the
        unit of determinism; replay does not re-invoke."""
        doc = Provider.__doc__ or ""
        assert "determin" in doc.lower(), (
            "Provider Protocol docstring must document the determinism contract"
        )

    def test_conforming_provider_passes_registry_validation(self) -> None:
        """The same structural check that the registry uses must accept
        a Provider-conforming class."""
        from paxman.providers._model import ProviderRegistry

        reg = ProviderRegistry()
        provider = _ConformingProvider()
        reg.register(provider.name, provider)  # must not raise
        assert reg.get(provider.name) is provider

    def test_non_conforming_missing_name_rejected(self) -> None:
        from paxman.providers._model import ProviderRegistry

        reg = ProviderRegistry()
        with pytest.raises(TypeError):
            reg.register("x", _MissingName())

    def test_non_conforming_missing_capabilities_rejected(self) -> None:
        from paxman.providers._model import ProviderRegistry

        reg = ProviderRegistry()
        with pytest.raises(TypeError):
            reg.register("x", _MissingCapabilities())

    def test_non_conforming_missing_complete_rejected(self) -> None:
        from paxman.providers._model import ProviderRegistry

        reg = ProviderRegistry()
        with pytest.raises(TypeError):
            reg.register("x", _MissingComplete())

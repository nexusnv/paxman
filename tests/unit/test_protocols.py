"""Unit tests for ``paxman.protocols`` — internal Protocol definitions.

The protocols are stubs (``...`` bodies) with `object` placeholder types.
Sprint 2+ will replace the placeholders with concrete types.

These tests verify:
- The four protocols are importable.
- They have the right methods/properties.
- They are usable as runtime-checkable types where applicable (Protocol structural typing).
"""

from __future__ import annotations

from paxman.protocols import (
    Capability,
    ContractAdapter,
    Heuristic,
    InferenceProvider,
)

# --- Import surface ---------------------------------------------------------


def test_all_four_protocols_importable() -> None:
    """All four protocols are importable from ``paxman.protocols``."""
    assert ContractAdapter is not None
    assert Capability is not None
    assert Heuristic is not None
    assert InferenceProvider is not None


# --- ContractAdapter --------------------------------------------------------


def test_contractadapter_has_format_id() -> None:
    """``ContractAdapter`` declares the ``format_id`` property."""
    assert hasattr(ContractAdapter, "format_id")


def test_contractadapter_has_adapt() -> None:
    """``ContractAdapter`` declares the ``adapt`` method."""
    assert hasattr(ContractAdapter, "adapt")


def test_contractadapter_has_export() -> None:
    """``ContractAdapter`` declares the ``export`` method."""
    assert hasattr(ContractAdapter, "export")


def test_concrete_adapter_satisfies_protocol() -> None:
    """A class with the right structural shape satisfies ``ContractAdapter``."""

    class MyAdapter:
        @property
        def format_id(self) -> str:
            return "my_format"

        def adapt(self, external: object) -> object:
            return external

        def export(self, canonical: object) -> object:
            return canonical

    # Structural typing: the class is assignable to the Protocol type.
    adapter: ContractAdapter = MyAdapter()
    assert adapter.format_id == "my_format"


# --- Capability -------------------------------------------------------------


def test_capability_has_spec_property() -> None:
    assert hasattr(Capability, "spec")


def test_capability_has_invoke_method() -> None:
    assert hasattr(Capability, "invoke")


def test_concrete_capability_satisfies_protocol() -> None:
    """A class with the right structural shape satisfies ``Capability``."""

    class MyCapability:
        @property
        def spec(self) -> object:
            return {"id": "my_cap"}

        def invoke(self, ctx: object) -> object:
            return {"candidates": []}

    cap: Capability = MyCapability()
    assert cap.spec == {"id": "my_cap"}


# --- Heuristic --------------------------------------------------------------


def test_heuristic_has_select_method() -> None:
    assert hasattr(Heuristic, "select")


def test_concrete_heuristic_satisfies_protocol() -> None:
    class MyHeuristic:
        def select(self, field: object, ctx: object) -> list[object]:
            return []

    h: Heuristic = MyHeuristic()
    assert h.select(None, None) == []


# --- InferenceProvider ------------------------------------------------------


def test_inferenceprovider_has_complete() -> None:
    assert hasattr(InferenceProvider, "complete")


def test_concrete_provider_satisfies_protocol() -> None:
    class MyProvider:
        def complete(self, request: object) -> object:
            return {"text": "response"}

    p: InferenceProvider = MyProvider()
    assert p.complete(None) == {"text": "response"}


# --- Protocol bodies are stubs (no runtime check beyond structure) -----------


def test_protocol_method_bodies_are_ellipsis() -> None:
    """The Protocol methods have ``...`` bodies (no implementation)."""
    import inspect

    # ContractAdapter.adapt
    src = inspect.getsource(ContractAdapter.adapt)
    assert "..." in src or "raise NotImplementedError" in src or "pass" in src

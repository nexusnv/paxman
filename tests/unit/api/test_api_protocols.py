"""Unit tests for ``paxman.api.protocols`` — public SPI re-exports.

Verifies that the two key extension protocols (``Capability`` and
``ContractAdapter``) are importable and structurally checkable.
"""

from __future__ import annotations

import pytest

from paxman.api.protocols import Capability, ContractAdapter

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Import surface
# ---------------------------------------------------------------------------


class TestProtocolsImportable:
    """Both protocols are importable from ``paxman.api.protocols``."""

    def test_capability_importable(self) -> None:
        assert Capability is not None

    def test_contract_adapter_importable(self) -> None:
        assert ContractAdapter is not None


# ---------------------------------------------------------------------------
# Capability protocol
# ---------------------------------------------------------------------------


class MockCapability:
    """A concrete class that structurally satisfies the ``Capability`` protocol."""

    @property
    def spec(self) -> object:
        return {"id": "test_cap", "version": "1.0"}

    def invoke(self, ctx: object) -> object:
        return {"candidates": []}


class TestCapabilityProtocol:
    """Structural protocol checks for ``Capability``."""

    def test_capability_has_spec_property(self) -> None:
        assert hasattr(Capability, "spec")

    def test_capability_has_invoke_method(self) -> None:
        assert hasattr(Capability, "invoke")

    def test_concrete_satisfies_protocol(self) -> None:
        cap: Capability = MockCapability()
        assert isinstance(cap.spec, dict)
        assert cap.spec == {"id": "test_cap", "version": "1.0"}

    def test_invoke_returns_result(self) -> None:
        cap: Capability = MockCapability()
        result = cap.invoke(None)
        assert result == {"candidates": []}

    def test_mock_isinstance_check(self) -> None:
        """MockCapability structurally conforms to the protocol."""
        cap = MockCapability()
        # ``isinstance`` works with ``@runtime_checkable`` protocols (PEP 544).
        # The base ``typing.Protocol`` is not runtime-checkable by default;
        # this test verifies structural compatibility at the type-check level.
        assert hasattr(cap, "spec")
        assert hasattr(cap, "invoke")


# ---------------------------------------------------------------------------
# ContractAdapter protocol
# ---------------------------------------------------------------------------


class MockAdapter:
    """A concrete class that structurally satisfies the ``ContractAdapter`` protocol."""

    format_id = "test_format"

    def adapt(self, external: object) -> object:
        return external

    def export(self, canonical: object) -> object:
        return canonical


class TestContractAdapterProtocol:
    """Structural protocol checks for ``ContractAdapter``."""

    def test_adapter_has_format_id(self) -> None:
        assert hasattr(ContractAdapter, "format_id")

    def test_adapter_has_adapt_method(self) -> None:
        assert hasattr(ContractAdapter, "adapt")

    def test_adapter_has_export_method(self) -> None:
        assert hasattr(ContractAdapter, "export")

    def test_concrete_satisfies_protocol(self) -> None:
        adapter: ContractAdapter = MockAdapter()
        assert adapter.format_id == "test_format"

    def test_adapt_round_trip(self) -> None:
        adapter: ContractAdapter = MockAdapter()
        result = adapter.adapt({"foo": "bar"})
        assert result == {"foo": "bar"}

    def test_export_round_trip(self) -> None:
        adapter: ContractAdapter = MockAdapter()
        result = adapter.export({"foo": "bar"})
        assert result == {"foo": "bar"}

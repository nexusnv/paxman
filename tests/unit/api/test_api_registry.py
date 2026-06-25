"""Unit tests for ``paxman.api.registry`` — adapter and capability registration.

These tests verify the public ``register_adapter`` / ``get_adapter`` /
``register_capability`` / ``get_capability`` functions using mocking to
avoid polluting the process-local global registries.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from paxman.api.registry import get_adapter, get_capability, register_adapter, register_capability
from paxman.errors import InvalidContractError

pytestmark = pytest.mark.deterministic


# ---------------------------------------------------------------------------
# Mock adapter and capability helpers
# ---------------------------------------------------------------------------


class _MockAdapter:
    """Minimal adapter for registry round-trip tests."""

    format_id = "mock_format"

    def adapt(self, external: object) -> object:
        return external

    def export(self, canonical: object) -> object:
        return canonical


class _MockCapability:
    """Minimal capability for registry round-trip tests."""

    _spec: object = None

    @property
    def spec(self) -> object:
        if self._spec is None:
            # Lazy import to avoid circular dependency at class definition time.
            from paxman.capabilities.spec import CapabilitySpec

            self._spec = CapabilitySpec(id="mock_cap", version="1.0", input_types=("STRING",))
        return self._spec

    def invoke(self, ctx: object) -> object:
        return {"candidates": []}


# ---------------------------------------------------------------------------
# register_adapter / get_adapter
# ---------------------------------------------------------------------------


class TestRegisterAndGetAdapter:
    """Round-trip and error-path tests for adapter registration."""

    def test_register_adapter_calls_internal(self) -> None:
        """``register_adapter`` delegates to the internal registry."""
        adapter = _MockAdapter()
        with patch("paxman.api.registry._register_adapter") as mock_reg:
            register_adapter(adapter)
            mock_reg.assert_called_once_with(adapter)

    def test_get_adapter_returns_adapter_when_found(self) -> None:
        """``get_adapter`` returns the adapter when the internal lookup succeeds."""
        adapter = _MockAdapter()
        with patch("paxman.api.registry._get_adapter", return_value=adapter) as mock_get:
            result = get_adapter("mock_format")
            assert result is adapter
            mock_get.assert_called_once_with("mock_format")

    def test_get_adapter_returns_none_when_not_found(self) -> None:
        """``get_adapter`` returns ``None`` when the internal lookup raises ``InvalidContractError``."""
        with patch(
            "paxman.api.registry._get_adapter",
            side_effect=InvalidContractError("not found"),
        ):
            result = get_adapter("nonexistent")
            assert result is None

    def test_get_adapter_passes_through_unexpected_errors(self) -> None:
        """``get_adapter`` does not swallow non-``InvalidContractError`` exceptions.

        Note: the current implementation only catches ``InvalidContractError``,
        so other exception types propagate.
        """
        with patch(
            "paxman.api.registry._get_adapter",
            side_effect=ValueError("unexpected"),
        ):
            with pytest.raises(ValueError):
                get_adapter("broken")


# ---------------------------------------------------------------------------
# register_capability / get_capability
# ---------------------------------------------------------------------------


class TestRegisterAndGetCapability:
    """Round-trip and error-path tests for capability registration."""

    def test_register_capability_calls_internal(self) -> None:
        """``register_capability`` delegates to the internal registry."""
        capability = _MockCapability()
        with patch("paxman.api.registry._register_capability") as mock_reg:
            register_capability(capability)
            mock_reg.assert_called_once_with(capability)

    def test_get_capability_returns_capability_when_found(self) -> None:
        """``get_capability`` returns the capability when the internal lookup succeeds."""
        capability = _MockCapability()
        with patch(
            "paxman.api.registry._get_latest_capability", return_value=capability
        ) as mock_get:
            result = get_capability("mock_cap")
            assert result is capability
            mock_get.assert_called_once_with("mock_cap")

    def test_get_capability_returns_none_when_not_found(self) -> None:
        """``get_capability`` returns ``None`` when the internal lookup raises ``InvalidContractError``."""
        with patch(
            "paxman.api.registry._get_latest_capability",
            side_effect=InvalidContractError("not found"),
        ):
            result = get_capability("nonexistent")
            assert result is None

    def test_get_capability_passes_through_unexpected_errors(self) -> None:
        """``get_capability`` does not swallow non-``InvalidContractError`` exceptions."""
        with patch(
            "paxman.api.registry._get_latest_capability",
            side_effect=RuntimeError("unexpected"),
        ):
            with pytest.raises(RuntimeError):
                get_capability("broken")


# ---------------------------------------------------------------------------
# Round-trip integration (via mocked internal)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Full round-trip with mocked internal registries."""

    def test_register_and_get_adapter_round_trip(self) -> None:
        """Register an adapter then look it up via mocked internal."""
        adapter = _MockAdapter()
        with (
            patch("paxman.api.registry._register_adapter") as mock_reg,
            patch("paxman.api.registry._get_adapter", return_value=adapter) as mock_get,
        ):
            register_adapter(adapter)
            mock_reg.assert_called_once_with(adapter)

            result = get_adapter("mock_format")
            assert result is adapter
            mock_get.assert_called_once_with("mock_format")

    def test_register_and_get_capability_round_trip(self) -> None:
        """Register a capability then look it up via mocked internal."""
        capability = _MockCapability()
        with (
            patch("paxman.api.registry._register_capability") as mock_reg,
            patch(
                "paxman.api.registry._get_latest_capability", return_value=capability
            ) as mock_get,
        ):
            register_capability(capability)
            mock_reg.assert_called_once_with(capability)

            result = get_capability("mock_cap")
            assert result is capability
            mock_get.assert_called_once_with("mock_cap")

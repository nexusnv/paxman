"""Unit tests for ``paxman.api.replay`` — the ``replay`` entry point helpers.

Tests the private helper ``_detect_and_adapt`` (duplicated from
``paxman.api.normalize``) and verifies the ``replay`` function
orchestrates the replay pipeline correctly.

Note: the full ``replay()`` function is tested via integration/E2E tests.
These unit tests focus on the internal helpers.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from paxman.api.replay import _detect_and_adapt, _GlobalCapabilityRegistry, replay
from paxman.artifact.artifact import ExecutionArtifact
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.errors import InvalidContractError
from paxman.types import FieldType, Status

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _detect_and_adapt (duplicated helper)
# ---------------------------------------------------------------------------


class TestDetectAndAdapt:
    """Format detection + adaptation (same pattern as normalize's helper)."""

    def test_detect_and_adapt_success(self) -> None:
        """When detection and adaptation both succeed, returns the canonical contract."""
        expected = CanonicalContract(
            id="test",
            fields=(
                CanonicalField(
                    id="f1", path="name", name="Name", type=FieldType.STRING, required=True
                ),
            ),
        )
        with (
            patch("paxman.api.replay._detect_format", return_value="pydantic"),
            patch("paxman.api.replay._adapt_contract", return_value=expected),
        ):
            result = _detect_and_adapt({"dummy": "contract"})
            assert result is expected
            assert result.id == "test"

    def test_detect_and_adapt_detection_failure_propagates(self) -> None:
        """When ``_detect_format`` raises, the error propagates as ``InvalidContractError``."""
        with patch(
            "paxman.api.replay._detect_format",
            side_effect=InvalidContractError("unknown format"),
        ):
            with pytest.raises(InvalidContractError, match="unknown format"):
                _detect_and_adapt(42)

    def test_detect_and_adapt_adaptation_failure_propagates(self) -> None:
        """When ``_adapt_contract`` raises, the error propagates."""
        with (
            patch("paxman.api.replay._detect_format", return_value="pydantic"),
            patch(
                "paxman.api.replay._adapt_contract",
                side_effect=InvalidContractError("adapt failed"),
            ),
        ):
            with pytest.raises(InvalidContractError, match="adapt failed"):
                _detect_and_adapt({"dummy": "contract"})


# ---------------------------------------------------------------------------
# _GlobalCapabilityRegistry
# ---------------------------------------------------------------------------


class TestGlobalCapabilityRegistry:
    """Internal wrapper around the capability registry."""

    def test_get_returns_none_on_missing(self) -> None:
        """``_GlobalCapabilityRegistry.get`` returns ``None`` for unregistered capabilities."""
        from paxman.errors import InvalidContractError as CapErr

        registry = _GlobalCapabilityRegistry()
        with patch("paxman.api.replay.get_latest", side_effect=CapErr("not found")):
            result = registry.get("nonexistent_cap")
            assert result is None

    def test_get_returns_capability_when_found(self) -> None:
        """``_GlobalCapabilityRegistry.get`` returns the capability when registered."""
        from paxman.capabilities.spec import CapabilitySpec

        class _MockCap:
            @property
            def spec(self) -> object:
                return CapabilitySpec(id="test_cap", version="1.0", input_types=("STRING",))

            def invoke(self, ctx: object) -> object:
                return {"candidates": []}

        cap = _MockCap()
        registry = _GlobalCapabilityRegistry()
        with patch("paxman.api.replay.get_latest", return_value=cap):
            result = registry.get("test_cap")
            assert result is cap

    def test_get_propagates_non_invalid_errors(self) -> None:
        """Non-``InvalidContractError`` exceptions are propagated."""
        registry = _GlobalCapabilityRegistry()
        with patch("paxman.api.replay.get_latest", side_effect=RuntimeError("unexpected")):
            with pytest.raises(RuntimeError, match="unexpected"):
                registry.get("broken")


# ---------------------------------------------------------------------------
# replay function (via mocked internals)
# ---------------------------------------------------------------------------


class TestReplayFunction:
    """Orchestration of the ``replay`` entry point via mocked internals."""

    def test_replay_success(self) -> None:
        """``replay`` returns the verified artifact when all checks pass."""
        artifact = ExecutionArtifact(
            status=Status.SUCCESS,
            normalized_data={"name": "ACME"},
            field_results={},
            unresolved_fields=[],
            evidence=(),
            diagnostics=(),
            execution_plan=None,
            statistics=None,
            contract_id="test",
        )
        canonical = CanonicalContract(
            id="test",
            fields=(
                CanonicalField(
                    id="f1", path="name", name="Name", type=FieldType.STRING, required=True
                ),
            ),
        )

        with (
            patch("paxman.api.replay._detect_and_adapt", return_value=canonical) as mock_detect,
            patch("paxman.api.replay.replay_artifact", return_value=artifact) as mock_replay,
        ):
            result = replay(artifact, {"type": "object", "properties": {}})

        assert result is artifact
        mock_detect.assert_called_once_with({"type": "object", "properties": {}})
        mock_replay.assert_called_once()

    def test_replay_detection_failure_propagates(self) -> None:
        """When contract detection/adaptation fails, ``InvalidContractError`` propagates."""
        artifact = ExecutionArtifact(
            status=Status.SUCCESS,
            normalized_data={},
            field_results={},
            unresolved_fields=[],
            evidence=(),
            diagnostics=(),
            execution_plan=None,
            statistics=None,
            contract_id="",
        )
        with patch(
            "paxman.api.replay._detect_and_adapt",
            side_effect=InvalidContractError("unknown contract"),
        ):
            with pytest.raises(InvalidContractError, match="unknown contract"):
                replay(artifact, {"type": "object"})

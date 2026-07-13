"""Tests for the replay path (mandate Law 12)."""

from __future__ import annotations

from typing import Any

import pytest

from paxman._contracts.contract import parse_contract
from paxman._core.artifact import ExecutionArtifact
from paxman._core.replay import replay
from paxman._core.types import Evidence, Status, VersionStamp
from paxman._errors import VersionMismatchError

_EMPTY_REGISTRY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _artifact(**overrides: object) -> ExecutionArtifact:
    defaults: dict[str, Any] = dict(
        status=Status.CANONICALIZED,
        value="a@b.c",
        evidence=(Evidence(rule="lowercased_local_part"),),
        contract=parse_contract({"kind": "canonical_email"}),
        version_stamp=VersionStamp(
            paxman_version="0.0.0.dev0",
            contract_version=1,
            capabilities_hash=_EMPTY_REGISTRY_HASH,
            configuration_version="0",
        ),
    )
    defaults.update(overrides)
    return ExecutionArtifact(**defaults)


@pytest.fixture(autouse=True)
def _empty_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    from paxman import _orchestrator_runtime
    from paxman._capabilities.registry import CapabilityRegistry

    r = CapabilityRegistry()
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


class TestReplay:
    def test_replay_returns_same_artifact(self) -> None:
        a = _artifact()
        rehydrated = replay(a, {"kind": "canonical_email"})
        assert rehydrated == a

    def test_replay_byte_equal(self) -> None:
        a = _artifact()
        rehydrated = replay(a, {"kind": "canonical_email"})
        assert rehydrated.canonical_bytes() == a.canonical_bytes()

    def test_replay_paxman_version_mismatch_raises(self) -> None:
        a = _artifact(
            version_stamp=VersionStamp(
                paxman_version="9.9.9",
                contract_version=1,
                capabilities_hash=_EMPTY_REGISTRY_HASH,
                configuration_version="0",
            )
        )
        with pytest.raises(VersionMismatchError):
            replay(a, {"kind": "canonical_email"})

    def test_replay_contract_version_mismatch_raises(self) -> None:
        a = _artifact(
            version_stamp=VersionStamp(
                paxman_version="0.0.0.dev0",
                contract_version=999,
                capabilities_hash=_EMPTY_REGISTRY_HASH,
                configuration_version="0",
            )
        )
        with pytest.raises(VersionMismatchError):
            replay(a, {"kind": "canonical_email"})

    def test_replay_capabilities_hash_mismatch_raises(self) -> None:
        a = _artifact(
            version_stamp=VersionStamp(
                paxman_version="0.0.0.dev0",
                contract_version=1,
                capabilities_hash="bad-hash",
                configuration_version="0",
            )
        )
        with pytest.raises(VersionMismatchError):
            replay(a, {"kind": "canonical_email"})

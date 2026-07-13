"""Tests for the replay path (mandate Law 12)."""
from __future__ import annotations

import pytest

from paxman._core.replay import replay
from paxman._core.types import Evidence, Status, VersionStamp
from paxman._core.artifact import ExecutionArtifact
from paxman._errors import CanonicalizationError, VersionMismatchError
from paxman._contracts.contract import CanonicalEmailContract, parse_contract


def _artifact(**overrides: object) -> ExecutionArtifact:
    defaults: dict[str, object] = dict(
        status=Status.CANONICALIZED,
        value="a@b.c",
        evidence=(Evidence(rule="lowercased_local_part"),),
        contract=parse_contract({"kind": "canonical_email"}),
        version_stamp=VersionStamp(
            paxman_version="0.0.0.dev0",
            contract_version=1,
            capabilities_hash="x",
            configuration_version="0",
        ),
    )
    defaults.update(overrides)
    return ExecutionArtifact(**defaults)  # type: ignore[arg-type]


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
                capabilities_hash="x",
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
                capabilities_hash="x",
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

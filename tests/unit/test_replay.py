"""Tests for the replay path (mandate Law 12)."""

from __future__ import annotations

from typing import Any

import pytest

from paxman._core.artifact import ExecutionArtifact
from paxman._core.provenance import Evidence
from paxman._core.replay import replay
from paxman._core.result import VersionStamp
from paxman._core.status import Status
from paxman._dsl.parser import parse_contract
from paxman._errors import CanonicalizationError, VersionMismatchError

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
    from paxman._registry.capability_registry import CapabilityRegistry

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

    def test_replay_unparseable_contract_raises_version_mismatch(self) -> None:
        a = _artifact()
        # A contract the parser rejects maps to VersionMismatchError (Law 8).
        with pytest.raises(VersionMismatchError):
            replay(a, {"kind": "bogus"})

    def test_replay_hash_mismatch_raises(self) -> None:
        a = _artifact()
        # Tamper the stored hash; replay must detect the forgery (Law 12).
        object.__setattr__(a, "replay_hash", "tampered")
        with pytest.raises(CanonicalizationError):
            replay(a, {"kind": "canonical_email"})

    def test_replay_stale_specification_authority_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from paxman._provenance import registries as _authorities

        # An artifact that cited RFC 5322 at edition "RFC 5322 §3.2.3".
        a = _artifact(
            evidence=(Evidence(rule="lowercased_local_part"),),
            version_stamp=VersionStamp(
                paxman_version="0.0.0.dev0",
                contract_version=1,
                capabilities_hash=_EMPTY_REGISTRY_HASH,
                configuration_version="0",
                spec_versions={"RFC 5322": "RFC 5322 §3.2.3"},
            ),
        )
        # The registry has since advanced that authority's edition.
        monkeypatch.setattr(
            _authorities,
            "current_spec_versions",
            lambda: {"RFC 5322": "RFC 5322 §3.2.3 (revised 2026)"},
        )
        with pytest.raises(VersionMismatchError, match="specification version mismatch"):
            replay(a, {"kind": "canonical_email"})

    def test_replay_stale_data_set_authority_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman._provenance import registries as _authorities

        # An artifact that cited ISO 3166-1 (a data-set authority).
        a = _artifact(
            evidence=(Evidence(rule="lowercased_local_part"),),
            version_stamp=VersionStamp(
                paxman_version="0.0.0.dev0",
                contract_version=1,
                capabilities_hash=_EMPTY_REGISTRY_HASH,
                configuration_version="0",
                registry_versions={"ISO 3166-1": "ISO 3166-1:2020"},
            ),
        )
        monkeypatch.setattr(
            _authorities,
            "current_registry_versions",
            lambda: {"ISO 3166-1": "ISO 3166-1:2025"},
        )
        with pytest.raises(VersionMismatchError, match="data-set version mismatch"):
            replay(a, {"kind": "canonical_email"})

    def test_replay_authority_edition_unchanged_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from paxman._provenance import registries as _authorities

        # The edition matches the live registry exactly → replay succeeds.
        a = _artifact(
            evidence=(Evidence(rule="lowercased_local_part"),),
            version_stamp=VersionStamp(
                paxman_version="0.0.0.dev0",
                contract_version=1,
                capabilities_hash=_EMPTY_REGISTRY_HASH,
                configuration_version="0",
                spec_versions={"RFC 5322": _authorities.RFC_5322.edition},
            ),
        )
        rehydrated = replay(a, {"kind": "canonical_email"})
        assert rehydrated == a
        assert rehydrated.canonical_bytes() == a.canonical_bytes()

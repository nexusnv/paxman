"""End-to-end: paxman.canonicalize + replay byte-equality for dates (Law 12)."""

from __future__ import annotations

import pytest

import paxman
from paxman._capabilities.builtins.date import DateCapability
from paxman._capabilities.registry import CapabilityRegistry


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    from paxman import _orchestrator_runtime

    r = CapabilityRegistry()
    r.register(DateCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


def test_canonicalize_and_replay_byte_equal() -> None:
    contract = paxman.Date(locale="US")
    artifact = paxman.canonicalize("03/04/2025", contract)
    assert artifact.status is paxman.Status.CANONICALIZED
    assert artifact.value == "2025-03-04"
    rehydrated = paxman.replay(artifact, contract)
    assert rehydrated == artifact


def test_iso_datetime_resolves_through_default_registry() -> None:
    contract = paxman.Date(locale="ISO")
    artifact = paxman.canonicalize("2025-01-01T07:00:00-05:00", contract)
    assert artifact.status is paxman.Status.CANONICALIZED
    assert artifact.value == "2025-01-01T12:00:00Z"


def test_date_capability_is_the_only_date_claimant() -> None:
    from paxman import _orchestrator_runtime

    contract = paxman.Date(locale="ISO")
    claimants = _orchestrator_runtime.default_registry.resolve_all(contract, "2025-01-01")
    assert [c.name for c in claimants] == ["date_canonicalization"]

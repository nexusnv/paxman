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
    assert rehydrated.canonical_bytes() == artifact.canonical_bytes()


def test_iso_datetime_resolves_through_default_registry() -> None:
    contract = paxman.Date(locale="ISO")
    artifact = paxman.canonicalize("2025-01-01T07:00:00-05:00", contract)
    assert artifact.status is paxman.Status.CANONICALIZED
    assert artifact.value == "2025-01-01T12:00:00Z"


def test_date_capability_is_the_only_date_claimant() -> None:
    # Spec §5.4 uniqueness invariant: exactly one capability may claim any
    # (CanonicalDateContract, str) pair. Verify against the FULL builtin set
    # (email, uuid, date) -- not an isolated date-only registry -- so we
    # actually prove email/uuid do not erroneously claim a date contract.
    from paxman import Email
    from paxman._capabilities.builtins.discovery import builtin_capabilities
    from paxman._capabilities.registry import CapabilityRegistry

    registry = CapabilityRegistry()
    for cap in builtin_capabilities():
        registry.register(cap)
    registry.freeze()

    date_contract = paxman.Date(locale="ISO")
    claimants = registry.resolve_all(date_contract, "2025-01-01")
    assert [c.name for c in claimants] == ["date_canonicalization"]

    # Symmetric direction: DateCapability must not claim an email contract.
    email_claimants = registry.resolve_all(Email(), "john@example.com")
    assert "date_canonicalization" not in [c.name for c in email_claimants]

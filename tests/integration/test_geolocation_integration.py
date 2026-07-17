"""End-to-end exercise of the public Geolocation canonicalization API.

Mirrors tests/integration/test_money_integration.py: every test drives the
real public surface (paxman.canonicalize / paxman.replay), never the
capability class directly, and asserts both object equality and byte equality
on replay (mandate Law 12).
"""

from __future__ import annotations

import typing

import pytest

import paxman
from paxman import CanonicalGeolocationContract, Geolocation, canonicalize, replay
from paxman._capabilities.discovery import builtin_capabilities
from paxman._core.status import Status


@pytest.mark.integration
def test_full_round_trip() -> None:
    result = canonicalize("40.7128N 74.0060W", Geolocation())
    assert result.status is Status.CANONICALIZED
    assert result.value == "40.712800,-74.006000"
    rehydrated = replay(result, Geolocation())
    # Law 12 (Replayability): strict object AND byte equality.
    assert rehydrated == result
    assert rehydrated.canonical_bytes() == result.canonical_bytes()


@pytest.mark.integration
def test_canonical_form_replay_idempotent() -> None:
    # The canonical string carries no hemisphere signal, so re-canonicalizing
    # it requires require_hemisphere=False to resolve deterministically (the
    # contract policy, not a guess). The canonical form is then idempotent.
    contract = Geolocation(require_hemisphere=False)
    first = canonicalize("40.712800,-74.006000", contract)
    assert first.status is Status.CANONICALIZED
    assert first.value == "40.712800,-74.006000"
    # Re-canonicalize the canonical string itself: same value.
    second = canonicalize("40.712800,-74.006000", contract)
    assert second.status is Status.CANONICALIZED
    assert second.value == first.value
    # Replay again: still byte-equal.
    rehydrated = replay(second, contract)
    assert rehydrated == second
    assert rehydrated.canonical_bytes() == second.canonical_bytes()


@pytest.mark.integration
def test_missing_value() -> None:
    empty = canonicalize("", Geolocation())
    assert empty.status is Status.MISSING
    # Replay of a MISSING artifact is still safe and equal (Law 12).
    replayed_empty = replay(empty, Geolocation())
    assert replayed_empty == empty
    assert replayed_empty.canonical_bytes() == empty.canonical_bytes()

    none_val = canonicalize(None, Geolocation())
    assert none_val.status is Status.MISSING
    replayed_none = replay(none_val, Geolocation())
    assert replayed_none == none_val
    assert replayed_none.canonical_bytes() == none_val.canonical_bytes()


@pytest.mark.integration
def test_ambiguous_hemisphere() -> None:
    # Default require_hemisphere=True: an unsigned decimal pair admits four
    # readings -> AMBIGUOUS (Law 4), never guessed.
    result = canonicalize("40.7128, 74.0060", Geolocation())
    assert result.status is Status.AMBIGUOUS
    assert result.candidates is not None and len(result.candidates) > 0
    # Replay still reproduces the artifact byte-for-byte (Law 12).
    rehydrated = replay(result, Geolocation())
    assert rehydrated == result
    assert rehydrated.canonical_bytes() == result.canonical_bytes()


@pytest.mark.integration
def test_hemisphere_defaulted() -> None:
    result = canonicalize("40.7128, 74.0060", Geolocation(require_hemisphere=False))
    assert result.status is Status.CANONICALIZED
    assert result.value == "40.712800,74.006000"


@pytest.mark.integration
def test_coordinate_order_lon_lat() -> None:
    # The input carries no hemisphere signal, so require_hemisphere=False is
    # needed for a deterministic reading; coordinate_order then swaps the axes.
    result = canonicalize(
        "40.7128, -74.0060",
        Geolocation(coordinate_order="lon_lat", require_hemisphere=False),
    )
    assert result.status is Status.CANONICALIZED
    assert result.value == "-74.006000,40.712800"


@pytest.mark.integration
def test_builtin_registration() -> None:
    # Geolocation is the 9th built-in capability.
    caps = builtin_capabilities()
    assert len(caps) == 9
    names = {c.name for c in caps}
    assert "geolocation_canonicalization" in names


@pytest.mark.integration
def test_contract_in_union() -> None:
    # CanonicalGeolocationContract is part of the public Contract union.
    members = typing.get_args(paxman.Contract)
    assert CanonicalGeolocationContract in members

"""End-to-end test for UUID canonicalization.

Exercises the public API: canonicalize, replay, idempotence, evidence
inspection, and the contract factory.
"""

from __future__ import annotations

import paxman


def test_canonicalize_a_canonical_uuid() -> None:
    result = paxman.canonicalize("550e8400-e29b-41d4-a716-446655440000", paxman.UUID())
    assert result.status is paxman.Status.CANONICALIZED
    assert result.value == "550e8400-e29b-41d4-a716-446655440000"
    assert result.evidence[0].rule == "no_transformation_needed"


def test_canonicalize_then_replay() -> None:
    original = paxman.canonicalize("550e8400-e29b-41d4-a716-446655440000", paxman.UUID())
    rehydrated = paxman.replay(original, paxman.UUID())
    assert rehydrated == original
    assert rehydrated.canonical_bytes() == original.canonical_bytes()


def test_idempotence() -> None:
    """canonicalize(canonicalize(x)) == canonicalize(x)."""
    first = paxman.canonicalize("550e8400-e29b-41d4-a716-446655440000", paxman.UUID())
    second = paxman.canonicalize(first.value, paxman.UUID())
    assert second == first


def test_version_filter_rejects_v1_when_v4_required() -> None:
    result = paxman.canonicalize("e034b584-7d89-11ed-a1eb-0242ac120002", paxman.UUID(version="4"))
    assert result.status is paxman.Status.INVALID
    assert result.evidence[0].rule == "version_mismatch"


def test_email_and_uuid_capabilities_coexist() -> None:
    """Both built-ins are auto-loaded. Calling one does not affect the
    other; the capabilities_hash on both artifacts is the same."""
    email_result = paxman.canonicalize("user@example.com", paxman.Email())
    uuid_result = paxman.canonicalize("550e8400-e29b-41d4-a716-446655440000", paxman.UUID())
    assert email_result.status is paxman.Status.CANONICALIZED
    assert uuid_result.status is paxman.Status.CANONICALIZED
    assert (
        email_result.version_stamp.capabilities_hash == uuid_result.version_stamp.capabilities_hash
    )

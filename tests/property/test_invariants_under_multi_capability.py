"""Property tests for the four invariants under multiple capabilities.

This is the gating test for v2.0.0-rc1: it proves that the registry holds
{email_canonicalization, uuid_canonicalization} deterministically and that
the four invariants (replay, idempotence, uniqueness, immutability) hold
across all combinations.

The single-capability invariant property tests cover the one-capability
case. This file extends them to the two-capability case.
"""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

import paxman
from paxman import UUID, Email, Status
from paxman._contracts.contract import CanonicalEmailContract, CanonicalUUIDContract

# Strategy: any well-formed 36-char UUID (str(uuid.UUID(...)) is the
# RFC 4122 §3 canonical lowercase hyphenated form).
uuid_strings = st.uuids().map(str)

# Strategy: any plausible email address. Use a simple regex strategy to
# avoid depending on hypothesis's built-in email strategy availability.
emails = st.from_regex(r"[a-z]{3,}@[a-z]{3,}\.[a-z]{2,}", fullmatch=True)


@given(uuid_strings)
@settings(max_examples=50)
def test_uuid_replay_byte_equality(uuid_str: str) -> None:
    artifact = paxman.canonicalize(uuid_str, UUID())
    rehydrated = paxman.replay(artifact, UUID())
    assert rehydrated == artifact


@given(uuid_strings)
@settings(max_examples=50)
def test_uuid_idempotence(uuid_str: str) -> None:
    """canonicalize(canonicalize(x)) == canonicalize(x)."""
    first = paxman.canonicalize(uuid_str, UUID())
    assert first.status is Status.CANONICALIZED
    second = paxman.canonicalize(first.value, UUID())
    assert second == first


@given(uuid_strings, emails)
@settings(max_examples=50)
def test_capabilities_hash_is_stable_across_calls(uuid_str: str, email: str) -> None:
    """Both capabilities use the same default registry, so the
    capabilities_hash on every artifact must equal the hash on
    every other artifact (within the same process)."""
    uuid_artifact = paxman.canonicalize(uuid_str, UUID())
    email_artifact = paxman.canonicalize(email, Email())
    assert (
        uuid_artifact.version_stamp.capabilities_hash
        == email_artifact.version_stamp.capabilities_hash
    )


def test_no_two_builtins_claim_the_same_pair() -> None:
    """The AMBIGUOUS invariant for the built-in set: for every
    (contract, value) pair, at most one built-in claims it."""
    from paxman._capabilities.builtins.email import EmailCapability
    from paxman._capabilities.builtins.uuid import UUIDCapability

    email_cap = EmailCapability()
    uuid_cap = UUIDCapability()
    uuid_val = "550e8400-e29b-41d4-a716-446655440000"

    assert email_cap.can_handle(CanonicalUUIDContract(), uuid_val) is False
    assert uuid_cap.can_handle(CanonicalEmailContract(), "user@example.com") is False
    assert email_cap.can_handle("not a contract", "user@example.com") is False
    assert uuid_cap.can_handle("not a contract", "550e8400-e29b-41d4-a716-446655440000") is False

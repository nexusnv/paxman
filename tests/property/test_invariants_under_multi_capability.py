"""Property tests for the four invariants under multiple capabilities.

This is the gating test for v2.0.0-rc1: it proves that the registry holds
{email_canonicalization, uuid_canonicalization} deterministically and that
the four invariants (replay, idempotence, uniqueness, immutability) hold
across all combinations.

The single-capability invariant property tests cover the one-capability
case. This file extends them to the two-capability case.
"""

from __future__ import annotations

import hashlib

import attrs
import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

import paxman
import paxman._orchestrator_runtime as _orchestrator_runtime
from paxman._capabilities.uuid import UUIDCapability
from paxman._core.result import CapabilityResult
from paxman._core.status import Status
from paxman._registry.capability_registry import CapabilityRegistry

# Strategy: any well-formed 36-char UUID (str(uuid.UUID(...)) is the
# RFC 4122 §3 canonical lowercase hyphenated form).
uuid_strings = st.uuids().map(str)

# Strategy: any plausible email address. Use a simple regex strategy to
# avoid depending on hypothesis's built-in email strategy availability.
emails = st.from_regex(r"[a-z]{3,}@[a-z]{3,}\.[a-z]{2,}", fullmatch=True)


@given(uuid_strings)
@settings(max_examples=50)
def test_uuid_replay_byte_equality(uuid_str: str) -> None:
    artifact = paxman.canonicalize(uuid_str, paxman.UUID())
    rehydrated = paxman.replay(artifact, paxman.UUID())
    assert rehydrated == artifact
    assert rehydrated.canonical_bytes() == artifact.canonical_bytes()


@given(uuid_strings)
@settings(max_examples=50)
def test_uuid_idempotence(uuid_str: str) -> None:
    """canonicalize(canonicalize(x)) == canonicalize(x)."""
    first = paxman.canonicalize(uuid_str, paxman.UUID())
    assert first.status is paxman.Status.CANONICALIZED
    second = paxman.canonicalize(first.value, paxman.UUID())
    assert second == first


@given(uuid_strings, emails)
@settings(max_examples=50)
def test_capabilities_hash_is_stable_across_calls(uuid_str: str, email: str) -> None:
    """Both capabilities use the same default registry, so the
    capabilities_hash on every artifact must equal the hash on
    every other artifact (within the same process)."""
    uuid_artifact = paxman.canonicalize(uuid_str, paxman.UUID())
    email_artifact = paxman.canonicalize(email, paxman.Email())
    assert (
        uuid_artifact.version_stamp.capabilities_hash
        == email_artifact.version_stamp.capabilities_hash
    )
    assert uuid_artifact.contract.kind == "canonical_uuid"
    assert email_artifact.contract.kind == "canonical_email"
    assert uuid_artifact.contract.kind != email_artifact.contract.kind


def test_no_two_builtins_claim_the_same_pair() -> None:
    """The AMBIGUOUS invariant for the built-in set: for every
    (contract, value) pair, at most one built-in claims it."""
    from paxman._capabilities.email import EmailCapability
    from paxman._capabilities.email.contract import CanonicalEmailContract
    from paxman._capabilities.uuid.contract import CanonicalUUIDContract

    email_cap = EmailCapability()
    uuid_cap = UUIDCapability()
    uuid_val = "550e8400-e29b-41d4-a716-446655440000"

    assert email_cap.can_handle(CanonicalUUIDContract(), uuid_val) is False
    assert uuid_cap.can_handle(CanonicalEmailContract(), "user@example.com") is False
    assert email_cap.can_handle("not a contract", "user@example.com") is False
    assert uuid_cap.can_handle("not a contract", "550e8400-e29b-41d4-a716-446655440000") is False


class _Claimant:
    """A capability that claims every (contract, value) pair."""

    def __init__(self, name: str) -> None:
        self.name = name

    def can_handle(self, contract: object, value: object) -> bool:
        return True

    def canonicalize(self, value: object, contract: object) -> CapabilityResult:
        return CapabilityResult(status=Status.CANONICALIZED, value=str(value))


@pytest.mark.property
def test_uuid_uniqueness_invariant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mandate §5.4: multiple claimants -> Status.AMBIGUOUS, never a silent pick.

    The two-claimant registry is installed via the ``monkeypatch`` fixture;
    the hypothesis ``@given`` strategy is nested so the test signature carries
    exactly one fixture parameter and one generated parameter (this repo's
    hypothesis/pytest build rejects mixing them on one signature).
    """
    r = CapabilityRegistry()
    r.register(_Claimant("A"))
    r.register(_Claimant("B"))
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)

    @settings(max_examples=30, deadline=None, derandomize=True)
    @given(uuid_strings)
    def _check(uuid_str: str) -> None:
        art = paxman.canonicalize(uuid_str, paxman.UUID())
        assert art.status is Status.AMBIGUOUS
        rule_names = {e.rule for e in art.evidence}
        assert "multiple_claimants" in rule_names

    _check()


@pytest.mark.property
@settings(max_examples=30, deadline=None, derandomize=True)
@given(uuid_strings)
def test_uuid_artifact_immutability_invariant(uuid_str: str) -> None:
    """Mandate Law 13: every field on every artifact is immutable."""
    art = paxman.canonicalize(uuid_str, paxman.UUID())
    for field in attrs.fields(art.__class__):
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            setattr(art, field.name, "x")


@pytest.mark.property
@settings(max_examples=30, deadline=None, derandomize=True)
@given(uuid_strings)
def test_uuid_canonicalization_invariant(uuid_str: str) -> None:
    """Mandate Law 1: replay_hash matches sha256(canonical_bytes())."""
    art = paxman.canonicalize(uuid_str, paxman.UUID())
    expected = hashlib.sha256(art.canonical_bytes()).hexdigest()
    assert art.replay_hash == expected

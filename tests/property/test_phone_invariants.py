"""Property tests for phone canonicalization invariants.

Proves Mandate Law 12 (Replayability — replay(artifact, contract) == artifact
byte-for-byte), idempotence, and that no two built-in capabilities silently
claim the same (contract, value) pair.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import paxman
from paxman import Phone
from paxman._core.status import Status

# Strategy: valid E.164 bodies — cc 1-3 digits (first 1-9), national 4-12 digits.
# Capped so cc_len + national_len <= 15 (max E.164 length), keeping every
# generated string canonicalizable rather than rejected as INVALID.
_cc = st.integers(min_value=1, max_value=999).map(str)
_national = st.integers(min_value=1000, max_value=10**11 - 1).map(str)


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(cc=_cc, national=_national)
def test_replay_byte_equal(cc: str, national: str) -> None:
    s = f"+{cc}{national}"
    art = paxman.canonicalize(s, Phone(country="US"))
    assert art.status is Status.CANONICALIZED
    rehydrated = paxman.replay(art, Phone(country="US"))
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(cc=_cc, national=_national)
def test_idempotence(cc: str, national: str) -> None:
    s = f"+{cc}{national}"
    first = paxman.canonicalize(s, Phone(country="US"))
    assert first.status is Status.CANONICALIZED
    second = paxman.canonicalize(first.value, Phone(country="US"))
    assert second == first


# Separated national form (resolver prepends the declared country code).
# 7-15 digits so the body clears the grammar's minimum-length floor and the
# E.164 validator (<=15 digits). Exercises the non-e164 branch of
# generate_interpretations under replay.
_sep = st.sampled_from([" ", "-", ".", "(", ")", "(", "-", " ", "."])
_national_sep = st.integers(min_value=10**6, max_value=10**14 - 1).map(str)


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(national=_national_sep, sep1=_sep, sep2=_sep)
def test_replay_separated_national(national: str, sep1: str, sep2: str) -> None:
    s = f"{national[:3]}{sep1}{national[3:6]}{sep2}{national[6:]}"
    art = paxman.canonicalize(s, Phone(country="US"))
    assert art.status is Status.CANONICALIZED
    rehydrated = paxman.replay(art, Phone(country="US"))
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(value=st.text(min_size=1, max_size=40))
def test_no_silent_ambiguity_among_builtins(value: str) -> None:
    # A phone string must not be claimed by more than one built-in at once.
    from paxman._capabilities.discovery import builtin_capabilities

    claimants = [c for c in builtin_capabilities() if c.can_handle(Phone(country="US"), value)]
    # PhoneCapability claims only Phone contracts; other built-ins use their
    # own contract classes, so at most one built-in can claim this pair.
    assert len(claimants) <= 1

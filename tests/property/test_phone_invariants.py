"""Property tests for phone canonicalization invariants.

Proves Mandate Law 2 (replay byte-equal), idempotence, and that no two
built-in capabilities silently claim the same (contract, value) pair.
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
_cc = st.integers(min_value=1, max_value=999).map(lambda n: str(n))
_national = st.integers(min_value=1000, max_value=10**11 - 1).map(lambda n: str(n))


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(cc=_cc, national=_national)
def test_replay_byte_equal(cc: str, national: str) -> None:
    s = f"+{cc}{national}"
    art = paxman.canonicalize(s, Phone(country="US"))
    assert art.status is Status.CANONICALIZED
    rehydrated = paxman.replay(art, Phone(country="US"))
    assert rehydrated == art


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(cc=_cc, national=_national)
def test_idempotence(cc: str, national: str) -> None:
    s = f"+{cc}{national}"
    first = paxman.canonicalize(s, Phone(country="US"))
    assert first.status is Status.CANONICALIZED
    second = paxman.canonicalize(first.value, Phone(country="US"))
    assert second == first


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

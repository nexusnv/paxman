"""Boolean-specific invariant property tests (mandate Laws 2, 12).

Complements the generic engine property tests: every supported boolean
input canonicalizes idempotently and replays byte-equal. Derandomized per
AGENTS.md (mandate Law 1 — no randomness).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import Boolean, canonicalize, replay
from paxman._core.status import Status

_TOKENS = [
    "true",
    "True",
    "TRUE",
    "false",
    "False",
    "FALSE",
    "yes",
    "Y",
    "on",
    "enabled",
    "1",
    "0",
    "no",
    "N",
    "off",
    "disabled",
]


@pytest.mark.property
@settings(derandomize=True)
@given(st.sampled_from(_TOKENS), st.booleans(), st.booleans())
def test_idempotence(token: str, accept_numeric: bool, accept_words: bool) -> None:
    contract = Boolean(accept_numeric=accept_numeric, accept_words=accept_words)
    result = canonicalize(token, contract)
    if result.status is Status.CANONICALIZED:
        assert result.value in ("true", "false")
        again = canonicalize(result.value, contract)
        assert again.status is Status.CANONICALIZED
        assert again.value == result.value


@pytest.mark.property
@settings(derandomize=True)
@given(st.sampled_from(_TOKENS), st.booleans(), st.booleans())
def test_replay_byte_equal(token: str, accept_numeric: bool, accept_words: bool) -> None:
    contract = Boolean(accept_numeric=accept_numeric, accept_words=accept_words)
    result = canonicalize(token, contract)
    if result.status is Status.CANONICALIZED:
        rehydrated = replay(result, contract)
        assert rehydrated == result

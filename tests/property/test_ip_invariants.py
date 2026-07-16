"""IP-specific invariant property tests (mandate Laws 2, 12).

Complements the generic engine property tests: every supported IP input
canonicalizes idempotently and replays byte-equal. Derandomized per
AGENTS.md (mandate Law 1 — no randomness).
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import IP, canonicalize, replay
from paxman._core.status import Status

_VALID_IPV4 = [
    "192.168.1.1",
    "10.0.0.0",
    "172.16.254.1",
    "0.0.0.0",
    "255.255.255.255",
]
_VALID_IPV6 = [
    "2001:db8::1",
    "fe80::1",
    "::1",
    "::ffff:192.0.2.1",
    "2001:0db8:0000:0000:0000:0000:0000:0001",
]


@settings(derandomize=True)
@given(st.sampled_from(_VALID_IPV4 + _VALID_IPV6), st.booleans(), st.booleans(), st.booleans())
def test_idempotence(
    token: str, allow_ipv4: bool, allow_ipv6: bool, preserve_zone_id: bool
) -> None:
    contract = IP(allow_ipv4=allow_ipv4, allow_ipv6=allow_ipv6, preserve_zone_id=preserve_zone_id)
    result = canonicalize(token, contract)
    if result.status is Status.CANONICALIZED:
        again = canonicalize(result.value, contract)
        assert again.status is Status.CANONICALIZED
        assert again.value == result.value


@settings(derandomize=True)
@given(st.sampled_from(_VALID_IPV4 + _VALID_IPV6), st.booleans(), st.booleans(), st.booleans())
def test_replay_byte_equal(
    token: str, allow_ipv4: bool, allow_ipv6: bool, preserve_zone_id: bool
) -> None:
    contract = IP(allow_ipv4=allow_ipv4, allow_ipv6=allow_ipv6, preserve_zone_id=preserve_zone_id)
    result = canonicalize(token, contract)
    if result.status is Status.CANONICALIZED:
        rehydrated = replay(result, contract)
        assert rehydrated == result

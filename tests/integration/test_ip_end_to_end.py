"""End-to-end exercise of the IPCapability via the public API."""

from __future__ import annotations

import attrs

from paxman import IP, canonicalize, replay
from paxman._core.status import Status


def test_ipv4_strips_leading_zeros() -> None:
    r = canonicalize("192.168.001.001", IP())
    assert r.status is Status.CANONICALIZED
    assert r.value == "192.168.1.1"


def test_ipv6_rfc5952() -> None:
    r = canonicalize("2001:0DB8:0000:0000:0000:0000:0000:0001", IP())
    assert r.status is Status.CANONICALIZED
    assert r.value == "2001:db8::1"


def test_zone_preserved_and_lowercased() -> None:
    r = canonicalize("FE80::1%ETH0", IP())
    assert r.status is Status.CANONICALIZED
    assert r.value == "fe80::1%eth0"


def test_zone_stripped_when_policy_false() -> None:
    r = canonicalize("fe80::1%eth0", IP(preserve_zone_id=False))
    assert r.status is Status.CANONICALIZED
    assert r.value == "fe80::1"


def test_policy_disabled_ipv6_is_invalid() -> None:
    r = canonicalize("2001:db8::1", IP(allow_ipv6=False))
    assert r.status is Status.INVALID


def test_missing_for_empty() -> None:
    assert canonicalize("", IP()).status is Status.MISSING


def test_unknown_kind_is_unsupported() -> None:
    r = canonicalize("2001:db8::1", {"kind": "canonical_bogus"})
    assert r.status is Status.UNSUPPORTED


def test_replay_byte_equal() -> None:
    r = canonicalize("FE80::1%ETH0", IP())
    assert r.status is Status.CANONICALIZED
    rehydrated = replay(r, IP())
    assert rehydrated == r
    assert rehydrated.canonical_bytes() == r.canonical_bytes()


def test_artifact_is_immutable() -> None:
    r = canonicalize("192.168.1.1", IP())
    for field in attrs.fields(type(r)):
        try:
            setattr(r, field.name, "x")
            raise AssertionError(f"{field.name} was mutable")
        except attrs.exceptions.FrozenInstanceError:
            pass

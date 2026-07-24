"""Tests for the IP recognition (Layer 1) grammar."""

from __future__ import annotations

from paxman._capabilities.ip.contract import CanonicalIPContract
from paxman._capabilities.ip.grammar import GRAMMARS, recognize


def _contract(**kw: object) -> CanonicalIPContract:
    return CanonicalIPContract(**kw)


def test_recognize_ipv4_shape() -> None:
    reps = recognize("192.168.1.1", _contract())
    assert len(reps) == 1
    assert reps[0].shape == "ipv4"


def test_recognize_ipv6_shape() -> None:
    reps = recognize("2001:db8::1", _contract())
    assert len(reps) == 1
    assert reps[0].shape == "ipv6"


def test_recognize_ipv6_zone_shape() -> None:
    reps = recognize("fe80::1%eth0", _contract())
    assert len(reps) == 1
    assert reps[0].shape == "ipv6_zone"


def test_recognize_ipv4_mapped_zone_shape() -> None:
    reps = recognize("::ffff:192.0.2.1%eth0", _contract())
    assert len(reps) == 1
    assert reps[0].shape == "ipv6_zone"


def test_recognize_unknown_returns_empty() -> None:
    assert recognize("example.com", _contract()) == []


def test_recognize_rejects_non_ip_contract() -> None:
    assert recognize("192.168.1.1", object()) == []


def test_grammars_have_provenance() -> None:
    for g in GRAMMARS:
        assert g.provenance.name != ""

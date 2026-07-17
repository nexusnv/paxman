"""Tests for the IPCapability (four-stage canonicalization)."""

from __future__ import annotations

from typing import cast

from paxman._capabilities.ip import _RULE_PROVENANCE, IPCapability
from paxman._capabilities.ip.contract import CanonicalIPContract
from paxman._core.contracts import Contract
from paxman._core.status import Status


def _cap() -> IPCapability:
    return IPCapability()


def _contract(
    *,
    allow_ipv4: bool = True,
    allow_ipv6: bool = True,
    preserve_zone_id: bool = True,
) -> CanonicalIPContract:
    return CanonicalIPContract(
        allow_ipv4=allow_ipv4,
        allow_ipv6=allow_ipv6,
        preserve_zone_id=preserve_zone_id,
    )


class TestIPCapability:
    def test_capability_metadata(self) -> None:
        assert _cap().name == "ip_canonicalization"

    def test_can_handle_matches_ip_contract(self) -> None:
        assert _cap().can_handle(_contract(), "192.168.1.1") is True

    def test_can_handle_accepts_none_and_str(self) -> None:
        assert _cap().can_handle(_contract(), None) is True
        assert _cap().can_handle(_contract(), "192.168.1.1") is True

    def test_can_handle_rejects_non_str_non_none(self) -> None:
        assert _cap().can_handle(_contract(), 1) is False

    def test_can_handle_rejects_non_ip_contract(self) -> None:
        assert _cap().can_handle(cast(Contract, "nope"), "192.168.1.1") is False

    def test_ipv4_strips_leading_zeros(self) -> None:
        r = _cap().canonicalize("192.168.001.001", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "192.168.1.1"

    def test_ipv4_all_octets_zero_padded(self) -> None:
        r = _cap().canonicalize("001.002.003.004", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "1.2.3.4"

    def test_ipv4_leading_zeros_decimal_not_octal(self) -> None:
        r = _cap().canonicalize("192.168.08.001", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "192.168.8.1"
        r = _cap().canonicalize("010.000.000.001", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "10.0.0.1"

    def test_ipv4_zero_padded_edge_addresses(self) -> None:
        assert _cap().canonicalize("000.000.000.000", _contract()).value == "0.0.0.0"
        assert _cap().canonicalize("255.255.255.255", _contract()).value == "255.255.255.255"

    def test_ipv4_out_of_range_octet_stays_invalid(self) -> None:
        r = _cap().canonicalize("057.472.389.213", _contract())
        assert r.status is Status.INVALID

    def test_ipv6_rfc5952_compression(self) -> None:
        r = _cap().canonicalize("2001:0DB8:0000:0000:0000:0000:0000:0001", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "2001:db8::1"

    def test_ipv6_lowercase(self) -> None:
        assert _cap().canonicalize("FE80::1", _contract()).value == "fe80::1"

    def test_ipv4_mapped_preserved(self) -> None:
        r = _cap().canonicalize("::ffff:192.0.2.1", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "::ffff:192.0.2.1"

    def test_zone_preserved_and_lowercased(self) -> None:
        r = _cap().canonicalize("FE80::1%ETH0", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "fe80::1%eth0"

    def test_zone_stripped_when_policy_false(self) -> None:
        r = _cap().canonicalize("fe80::1%eth0", _contract(preserve_zone_id=False))
        assert r.status is Status.CANONICALIZED and r.value == "fe80::1"

    def test_allow_ipv6_false_rejects_ipv6(self) -> None:
        r = _cap().canonicalize("2001:db8::1", _contract(allow_ipv6=False))
        assert r.status is Status.INVALID
        assert "policy_disabled_family" in {e.rule for e in r.evidence}

    def test_allow_ipv4_false_rejects_ipv4(self) -> None:
        r = _cap().canonicalize("192.168.1.1", _contract(allow_ipv4=False))
        assert r.status is Status.INVALID

    def test_whitespace_is_trimmed(self) -> None:
        r = _cap().canonicalize("  192.168.1.1  ", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "192.168.1.1"
        assert "trimmed_whitespace" in {e.rule for e in r.evidence}

    def test_empty_string_is_missing(self) -> None:
        assert _cap().canonicalize("", _contract()).status is Status.MISSING

    def test_none_is_missing(self) -> None:
        assert _cap().canonicalize(None, _contract()).status is Status.MISSING

    def test_unparseable_is_invalid(self) -> None:
        r = _cap().canonicalize("example.com", _contract())
        assert r.status is Status.INVALID
        assert "unrecognized_format" in {e.rule for e in r.evidence}

    def test_invalid_ipv4_octet_is_invalid(self) -> None:
        r = _cap().canonicalize("999.1.1.1", _contract())
        assert r.status is Status.INVALID

    def test_idempotence(self) -> None:
        once = _cap().canonicalize("  2001:0DB8:0000:0000:0000:0000:0000:0001  ", _contract())
        assert once.status is Status.CANONICALIZED
        twice = _cap().canonicalize(once.value, _contract())
        assert twice.value == once.value


class TestLaw14ProvenanceManifest:
    _DISPATCH_INVARIANTS = frozenset({"not_a_ip_contract", "not_a_string_value"})

    def test_every_manifest_entry_beyond_dispatch_has_provenance(self) -> None:
        for rule, prov in _RULE_PROVENANCE.items():
            if rule in self._DISPATCH_INVARIANTS:
                continue
            assert prov != ""

    def test_dispatch_invariants_allow_listed(self) -> None:
        for inv in self._DISPATCH_INVARIANTS:
            assert inv in _RULE_PROVENANCE and _RULE_PROVENANCE[inv] == ""

    def test_manifest_keys_cover_every_fired_rule(self) -> None:
        c = _cap()
        contract = _contract()
        inputs = [
            ("192.168.001.001", contract),
            ("2001:0DB8:0000:0000:0000:0000:0000:0001", contract),
            ("FE80::1%ETH0", contract),
            ("fe80::1%eth0", _contract(preserve_zone_id=False)),
            ("999.1.1.1", contract),
            ("example.com", contract),
            ("", contract),
            (None, contract),
            ("2001:db8::1", _contract(allow_ipv6=False)),
            ("192.168.1.1", _contract(allow_ipv4=False)),
        ]
        fired: set[str] = set()
        for value, contract in inputs:
            r = c.canonicalize(value, contract)
            for ev in r.evidence:
                fired.add(ev.rule)
        not_contract = cast(Contract, "not_a_contract")
        r1 = c.canonicalize("2001:db8::1", not_contract)
        for ev in r1.evidence:
            fired.add(ev.rule)
        for rule in fired:
            assert rule in _RULE_PROVENANCE, f"fired rule {rule!r} missing from manifest"

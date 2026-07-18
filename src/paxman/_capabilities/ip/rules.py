# src/paxman/_capabilities/ip/rules.py
"""IP Law 14 rule→authority manifest + evidence helper.

Migrated from a free-form `_RULE_PROVENANCE` string map to a structured
`_RULE_AUTHORITIES` authority map (mandate Law 14 — issue #158).
"""

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence
from paxman._provenance import Authority
from paxman._provenance import _evidence as _provenance_evidence
from paxman._provenance import registries as R

# Law 14 rule→authority manifest. The two dispatch invariants
# (not_a_ip_contract, not_a_string_value) are allow-listed with ``None``
# authority (Law 14 §3.6): they describe a routing failure, not a
# canonical-form rule. Every canonical-form rule cites an authoritative RFC.
_RULE_AUTHORITIES: Mapping[str, Authority | None] = MappingProxyType(
    {
        # --- dispatch invariants (no authority — Law 14 §3.6 allow-list) ---
        "not_a_ip_contract": None,
        "not_a_string_value": None,
        # --- recognition / resolution (RFCs + declared Paxman policy) ---
        "trimmed_whitespace": R.PAXMAN_SPEC_IP.section("§3.2 (ASCII whitespace trim)"),
        "recognized_ipv4": R.RFC_4291.section("§2.2 (IPv4 address text representation)"),
        "recognized_ipv6": R.RFC_4291.section("§2.2 (IPv6 address text representation)"),
        "canonicalized_ipv4": R.RFC_4291.section("§2.2 (dotted-decimal, no leading zeros)"),
        "canonicalized_ipv6": R.RFC_5952.section(
            "§4 (IPv6 text representation, lowercase compressed)"
        ),
        "canonicalized_ipv6_zone": R.RFC_4007.section(
            "§11 + RFC 5952 §4.3 (zone id preserved, lowercased)"
        ),
        "policy_disabled_family": R.PAXMAN_SPEC_IP.section(
            "§3.3 (contract policy disables address family)"
        ),
        "missing_value": R.PAXMAN_SPEC_IP.section("§3.4 (Law 8 — required value absent)"),
        "unrecognized_format": R.RFC_4291.section("(input is not a valid IP address)"),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 authority from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return _provenance_evidence(rule, _RULE_AUTHORITIES, detail)

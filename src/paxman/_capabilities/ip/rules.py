# src/paxman/_capabilities/ip/rules.py
"""IP Law 14 rule→provenance manifest + evidence helper."""

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence

# Law 14 rule→provenance manifest. The two dispatch invariants
# (not_a_ip_contract, not_a_string_value) are allow-listed with empty
# provenance (Law 14 §3.6): they describe a routing failure, not a
# canonical-form rule. Every canonical-form rule cites an authoritative RFC.
_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 §3.6 allow-list) ---
        "not_a_ip_contract": "",
        "not_a_string_value": "",
        # --- recognition / resolution (RFCs + declared Paxman policy) ---
        "trimmed_whitespace": "paxman spec/ip §3.2 (ASCII whitespace trim)",
        "recognized_ipv4": "RFC 4291 §2.2 (IPv4 address text representation)",
        "recognized_ipv6": "RFC 4291 §2.2 (IPv6 address text representation)",
        "canonicalized_ipv4": "RFC 4291 §2.2 (dotted-decimal, no leading zeros)",
        "canonicalized_ipv6": "RFC 5952 (IPv6 text representation, lowercase compressed)",
        "canonicalized_ipv6_zone": ("RFC 4007 §11 + RFC 5952 §4.3 (zone id preserved, lowercased)"),
        "policy_disabled_family": ("paxman spec/ip §3.3 (contract policy disables address family)"),
        "missing_value": "paxman spec/ip §3.4 (Law 8 — required value absent)",
        "unrecognized_format": "RFC 4291 (input is not a valid IP address)",
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])

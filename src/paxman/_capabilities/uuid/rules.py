"""UUID capability rule provenance.

Verbatim move of `_RULE_PROVENANCE` and `_evidence` from
`paxman._capabilities.builtins.uuid`.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence

_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 allow-list) ---
        "not_a_uuid_contract": "",
        "not_a_string_value": "",
        # --- rejecting rules (authoritative spec) ---
        "unrecognized_format": (
            "RFC 4122 §3 (the canonical form is 36 chars; 8-4-4-4-12 grouping; lowercase hex)"
        ),
        "version_mismatch": "RFC 4122 §4.1.3 (version field encoding)",
        # --- transforming rule (success path) ---
        "no_transformation_needed": "RFC 4122 §3 (the canonical form is X; X was provided)",
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance citation from
    the `_RULE_PROVENANCE` manifest.

    A rule with no manifest entry raises `KeyError`, surfacing a
    missing citation at the exact site where the rule is emitted.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])

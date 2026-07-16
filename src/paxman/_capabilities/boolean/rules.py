"""Boolean Law 14 rule→provenance manifest + evidence helper."""

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence

# Law 14 rule→provenance manifest. The two dispatch invariants
# (not_a_boolean_contract, not_a_string_value) are allow-listed with empty
# provenance (Law 14 §3.6): they describe a routing failure, not a
# canonical-form rule.
_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 §3.6 allow-list) ---
        "not_a_boolean_contract": "",
        "not_a_string_value": "",
        # --- recognition / resolution (declared Paxman policy) ---
        "trimmed_whitespace": "paxman spec/boolean §3.2 (ASCII whitespace trim)",
        "matched_boolean_token": "paxman spec/boolean §3.2 (token -> canonical)",
        "missing_value": "paxman spec/boolean §3.3 (Law 8 — required value absent)",
        "policy_disabled_token": (
            "paxman spec/boolean §3.2 + §3.3 (contract policy disables token)"
        ),
        "unrecognized_token": "paxman spec/boolean §3.3 (input matched no boolean grammar)",
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])

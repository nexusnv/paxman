"""Boolean Law 14 rule→authority manifest + evidence helper.

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
# (not_a_boolean_contract, not_a_string_value) are allow-listed with
# ``None`` authority (Law 14 §3.6): they describe a routing failure, not a
# canonical-form rule.
_RULE_AUTHORITIES: Mapping[str, Authority | None] = MappingProxyType(
    {
        # --- dispatch invariants (no authority — Law 14 §3.6 allow-list) ---
        "not_a_boolean_contract": None,
        "not_a_string_value": None,
        # --- recognition / resolution (declared Paxman policy) ---
        "trimmed_whitespace": R.PAXMAN_SPEC_BOOLEAN.section("§3.2 (ASCII whitespace trim)"),
        "matched_boolean_token": R.PAXMAN_SPEC_BOOLEAN.section("§3.2 (token -> canonical)"),
        "missing_value": R.PAXMAN_SPEC_BOOLEAN.section("§3.3 (Law 8 — required value absent)"),
        "policy_disabled_token": R.PAXMAN_SPEC_BOOLEAN.section(
            "§3.2 + §3.3 (contract policy disables token)"
        ),
        "unrecognized_token": R.PAXMAN_SPEC_BOOLEAN.section(
            "§3.3 (input matched no boolean grammar)"
        ),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 authority from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return _provenance_evidence(rule, _RULE_AUTHORITIES, detail)

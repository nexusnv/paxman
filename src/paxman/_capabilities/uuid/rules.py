"""UUID capability rule authority manifest.

Migrated from a free-form `_RULE_PROVENANCE` string map to a structured
`_RULE_AUTHORITIES` authority map (mandate Law 14 — issue #158). Verbatim
move of the rule set from `paxman._capabilities.builtins.uuid`, then
re-pointed at the central authority registry.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence
from paxman._provenance import Authority
from paxman._provenance import _evidence as _provenance_evidence
from paxman._provenance import registries as R

_RULE_AUTHORITIES: Mapping[str, Authority | None] = MappingProxyType(
    {
        # --- dispatch invariants (no authority — Law 14 allow-list) ---
        "not_a_uuid_contract": None,
        "not_a_string_value": None,
        # --- rejecting rules (authoritative spec) ---
        "unrecognized_format": R.RFC_4122.section(
            "§3 (canonical form is 36 chars; 8-4-4-4-12 grouping; lowercase hex)"
        ),
        "grammar_rejected": R.RFC_4122.section(
            "§3 (fails canonical-form grammar: wrong length, non-hex, or misplaced hyphen)"
        ),
        "version_mismatch": R.RFC_4122.section("§4.1.3 (version field encoding)"),
        # --- ambiguity rule (recognition produced more than one survivor) ---
        "ambiguous_provider_equivalence": R.RFC_4122.section(
            "§3 (more than one canonical reading survived; Paxman surfaces ambiguity — Law 3)"
        ),
        # --- transforming rule (success path) ---
        "no_transformation_needed": R.RFC_4122.section("§3 (input already the canonical form)"),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 authority from the
    `_RULE_AUTHORITIES` manifest.

    A rule with no manifest entry raises `KeyError`, surfacing a
    missing citation at the exact site where the rule is emitted.
    """
    return _provenance_evidence(rule, _RULE_AUTHORITIES, detail)

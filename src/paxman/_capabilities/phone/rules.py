"""Phone capability rule authority manifest.

MANDATE Law 14: every Evidence rule carries an authority citation pointing
to the authoritative source (RFC 3966 §3 / ITU-T E.164). The two dispatch
invariants (`not_a_phone_contract`, `not_a_string_value`) are allow-listed
with ``None`` authority per Law 14 §3.
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
        "not_a_phone_contract": None,
        "not_a_string_value": None,
        # --- rejecting rules (authoritative spec) ---
        "unrecognized_format": R.RFC_3966.section("§3 (the global E.164 form: +<cc><national>)"),
        "grammar_rejected": R.RFC_3966.section(
            "§3 / ITU-T E.164 (max 15 digits; CC first digit 1-9; national non-empty)"
        ),
        # --- transforming rules (success path) ---
        "no_transformation_needed": R.RFC_3966.section("§3 (input already the global E.164 form)"),
        "cc_prepended": R.RFC_3966.section(
            "§3 / ITU-T E.164 (national/digits-only expanded to global +<cc><national>)"
        ),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 authority citation from
    the `_RULE_AUTHORITIES` manifest.

    A rule with no manifest entry raises `KeyError`, surfacing a missing
    citation at the exact site where the rule is emitted.
    """
    return _provenance_evidence(rule, _RULE_AUTHORITIES, detail)

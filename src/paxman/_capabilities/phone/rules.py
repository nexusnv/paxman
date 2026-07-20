"""Phone capability rule authority manifest.

MANDATE Law 14: every Evidence rule carries an authority citation pointing
to the authoritative source (RFC 3966 §3 / ITU-T E.164). The two dispatch
invariants (`not_a_phone_contract`, `not_a_string_value`) are allow-listed
with ``None`` authority per Law 14 §3.
"""

from __future__ import annotations

from collections.abc import Mapping

from paxman._capabilities._shared.evidence import rule_authorities
from paxman._provenance import Authority
from paxman._provenance import registries as R

_RULE_AUTHORITIES: Mapping[str, Authority | None] = {
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

_evidence = rule_authorities(_RULE_AUTHORITIES)

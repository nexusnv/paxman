"""Phone capability rule provenance.

MANDATE Law 14: every Evidence rule carries a provenance citation pointing
to the authoritative source (RFC 3966 §3 / ITU-T E.164). The two dispatch
invariants (`not_a_phone_contract`, `not_a_string_value`) are allow-listed
with empty provenance per Law 14 §3.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence

_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 allow-list) ---
        "not_a_phone_contract": "",
        "not_a_string_value": "",
        # --- rejecting rules (authoritative spec) ---
        "unrecognized_format": ("RFC 3966 §3 (the global E.164 form: +<cc><national>)"),
        "grammar_rejected": (
            "RFC 3966 §3 / ITU-T E.164 (max 15 digits; country code first "
            "digit 1-9; national part non-empty)"
        ),
        # --- transforming rule (success path) ---
        "no_transformation_needed": ("RFC 3966 §3 (the input is already the global E.164 form)"),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance citation from
    the `_RULE_PROVENANCE` manifest.

    A rule with no manifest entry raises `KeyError`, surfacing a missing
    citation at the exact site where the rule is emitted.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])

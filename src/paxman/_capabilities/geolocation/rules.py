# src/paxman/_capabilities/geolocation/rules.py
"""Geolocation Law 14 rule→authority manifest + evidence helper.

Migrated from a free-form `_RULE_PROVENANCE` string map to a structured
`_RULE_AUTHORITIES` authority map (mandate Law 14 — issue #158).
"""

from collections.abc import Mapping
from types import MappingProxyType

from paxman._capabilities._shared.evidence import make_evidence
from paxman._provenance import Authority
from paxman._provenance import registries as R

# Law 14 rule→authority manifest. The two dispatch invariants
# (not_a_geolocation_contract, not_a_string_value) are allow-listed with
# ``None`` authority (Law 14 §3.6): they describe a routing failure, not a
# canonical-form rule. Every canonical-form rule cites an authoritative
# source (ISO 6709 / WGS84 or the approved geolocation design spec).
_RULE_AUTHORITIES: Mapping[str, Authority | None] = MappingProxyType(
    {
        # --- dispatch invariants (no authority — Law 14 §3.6 allow-list) ---
        "not_a_geolocation_contract": None,
        "not_a_string_value": None,
        # --- recognition / resolution (design spec + ISO 6709 / WGS84) ---
        "trimmed_whitespace": R.PAXMAN_SPEC_GEOLOCATION.section("§3.1 (ASCII whitespace trim)"),
        "recognized_decimal_pair": R.PAXMAN_SPEC_GEOLOCATION.section("§3.1 (decimal-pair shape)"),
        "recognized_decimal_hemisphere": R.PAXMAN_SPEC_GEOLOCATION.section(
            "§3.1 (hemisphere-letter shape)"
        ),
        "recognized_dms": R.PAXMAN_SPEC_GEOLOCATION.section("§3.1 (DMS shape)"),
        "canonicalized_geolocation": Authority(
            "ISO 6709 + WGS84",
            "ISO 6709 (geographic point coord) + WGS84 datum",
            "specification",
        ),
        "axis_order_applied": R.PAXMAN_SPEC_GEOLOCATION.section("§4.1 (coordinate_order policy)"),
        "hemisphere_resolved": R.PAXMAN_SPEC_GEOLOCATION.section("§4.1 (N/S/E/W or sign)"),
        "hemisphere_defaulted": R.PAXMAN_SPEC_GEOLOCATION.section(
            "§4.1 (require_hemisphere=False, positive default)"
        ),
        "dms_to_decimal": Authority(
            "ISO 6709 + WGS84",
            "ISO 6709 + WGS84 (DMS→decimal exact conversion)",
            "specification",
        ),
        "precision_applied": R.PAXMAN_SPEC_GEOLOCATION.section(
            "§4.2 (literal decimal places preserved)"
        ),
        "out_of_range": R.PAXMAN_SPEC_GEOLOCATION.section("§5 (lat/long range violation)"),
        "ambiguous_hemisphere": R.PAXMAN_SPEC_GEOLOCATION.section(
            "§4.1 / Law 4 (unsigned axis, hemisphere required)"
        ),
        "missing_value": R.PAXMAN_SPEC_GEOLOCATION.section("§5 (Law 8 — required value absent)"),
        "unrecognized_format": R.PAXMAN_SPEC_GEOLOCATION.section(
            "§3.1 / §4 (input is not a valid coordinate)"
        ),
    }
)


_evidence = make_evidence(_RULE_AUTHORITIES)

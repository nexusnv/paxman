# src/paxman/_capabilities/geolocation/rules.py
"""Geolocation Law 14 rule→provenance manifest + evidence helper."""

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence

# Law 14 rule→provenance manifest. The two dispatch invariants
# (not_a_geolocation_contract, not_a_string_value) are allow-listed with empty
# provenance (Law 14 §3.6): they describe a routing failure, not a
# canonical-form rule. Every canonical-form rule cites an authoritative source
# (ISO 6709 / WGS84 or the approved geolocation design spec).
_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 §3.6 allow-list) ---
        "not_a_geolocation_contract": "",
        "not_a_string_value": "",
        # --- recognition / resolution (design spec + ISO 6709 / WGS84) ---
        "trimmed_whitespace": "paxman spec/geolocation §3.1 (ASCII whitespace trim)",
        "recognized_decimal_pair": "paxman spec/geolocation §3.1 (decimal-pair shape)",
        "recognized_decimal_hemisphere": ("paxman spec/geolocation §3.1 (hemisphere-letter shape)"),
        "recognized_dms": "paxman spec/geolocation §3.1 (DMS shape)",
        "canonicalized_geolocation": "ISO 6709 (geographic point coord) + WGS84 datum",
        "axis_order_applied": "paxman spec/geolocation §4.1 (coordinate_order policy)",
        "hemisphere_resolved": "paxman spec/geolocation §4.1 (N/S/E/W or sign)",
        "hemisphere_defaulted": (
            "paxman spec/geolocation §4.1 (require_hemisphere=False, positive default)"
        ),
        "dms_to_decimal": "ISO 6709 + WGS84 (DMS→decimal exact conversion)",
        "precision_applied": ("paxman spec/geolocation §4.2 (literal decimal places preserved)"),
        "out_of_range": "paxman spec/geolocation §5 (lat/long range violation)",
        "ambiguous_hemisphere": (
            "paxman spec/geolocation §4.1 / Law 4 (unsigned axis, hemisphere required)"
        ),
        "missing_value": "paxman spec/geolocation §5 (Law 8 — required value absent)",
        "unrecognized_format": (
            "paxman spec/geolocation §3.1 / §4 (input is not a valid coordinate)"
        ),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])

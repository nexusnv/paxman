# src/paxman/_capabilities/country/rules.py
"""Country Law 14 rule->provenance manifest + evidence helper."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._capabilities._iso3166 import COUNTRY_TABLE_VERSION
from paxman._capabilities.country.policy import (
    COUNTRY_POLICY_CONVENIENCE_ALIASES,
    COUNTRY_POLICY_EXTRA_SYNONYMS,
    COUNTRY_POLICY_HISTORICAL,
    COUNTRY_POLICY_KIND_GATING,
    COUNTRY_POLICY_LOCALIZED,
    COUNTRY_POLICY_MISSING_VALUE,
    COUNTRY_POLICY_NUMERIC,
    COUNTRY_POLICY_WHITESPACE_TRIM,
)
from paxman._core.provenance import Evidence

# Law 14 rule->provenance manifest.
#
# - Dispatch invariants cite their MANDATE SPI sections (§5.1): they are NOT
#   exempt from citation (Law 14 §838 — empty provenance is a violation).
# - Paxman-defined policy rules reference the recorded constants in policy.py
#   (Law 14 §826 bullet 3) so amendments are traceable to every citing rule.
# - External-spec rules cite the specification directly.
_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (cite MANDATE SPI, never empty) ---
        "not_a_country_contract": (
            "MANDATE.md §5.1 (capability handles only its own contract kind)"
        ),
        "not_a_string_value": (
            "MANDATE.md §5.1 (canonicalize(value, contract): value is None or str)"
        ),
        # --- recognition / canonicalization (ISO 3166-1 + recorded policy) ---
        "trimmed_whitespace": COUNTRY_POLICY_WHITESPACE_TRIM,
        "recognized_alpha2": f"ISO 3166-1:2020 (alpha-2 shape; {COUNTRY_TABLE_VERSION})",
        "recognized_alpha3": f"ISO 3166-1:2020 (alpha-3 shape; {COUNTRY_TABLE_VERSION})",
        "recognized_numeric": f"ISO 3166-1:2020 (numeric shape; {COUNTRY_TABLE_VERSION})",
        "recognized_name": f"ISO 3166-1:2020 (name shape; {COUNTRY_TABLE_VERSION})",
        "canonicalized_country": (
            f"ISO 3166-1:2020 (alpha-2 canonical form; {COUNTRY_TABLE_VERSION})"
        ),
        "numeric_resolved": COUNTRY_POLICY_NUMERIC,
        "localized_resolved": COUNTRY_POLICY_LOCALIZED,
        "historical_resolved": COUNTRY_POLICY_HISTORICAL,
        "alias_resolved": (
            f"paxman spec/country §3.3 (bundled alias table, {COUNTRY_TABLE_VERSION}); "
            "convenience aliases recorded per " + COUNTRY_POLICY_CONVENIENCE_ALIASES
        ),
        "extra_synonym_resolved": COUNTRY_POLICY_EXTRA_SYNONYMS,
        "policy_disabled_kind": COUNTRY_POLICY_KIND_GATING,
        "missing_value": COUNTRY_POLICY_MISSING_VALUE,
        "unrecognized_format": (
            f"ISO 3166-1:2020 (input is not a recognized country token; {COUNTRY_TABLE_VERSION})"
        ),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])

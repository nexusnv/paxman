# src/paxman/_capabilities/country/rules.py
"""Country Law 14 rule->authority manifest + evidence helper.

Migrated from a free-form `_RULE_PROVENANCE` string map to a structured
`_RULE_AUTHORITIES` authority map (mandate Law 14 — issue #158). The
bundled ISO 3166-1:2020 edition is declared once in the central registry
(`paxman._provenance.registries.ISO_3166`) and referenced here by import;
the `COUNTRY_TABLE_VERSION` string is no longer interpolated. Paxman
policy rules reference the recorded policy authorities so amendments are
traceable to every citing rule.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence
from paxman._provenance import Authority
from paxman._provenance import _evidence as _provenance_evidence
from paxman._provenance import registries as R

# Composite authorities used by single country rules.
_ALPHA2 = R.ISO_3166.section("alpha-2 shape")
_ALPHA3 = R.ISO_3166.section("alpha-3 shape")
_NUMERIC = R.ISO_3166.section("numeric shape")
_NAME = R.ISO_3166.section("name shape")
_CANONICAL = R.ISO_3166.section("alpha-2 canonical form")
_NUMERIC_RESOLVED = R.PAXMAN_SPEC_COUNTRY.section("numeric resolution policy")
_LOCALIZED = R.PAXMAN_SPEC_COUNTRY.section("localized name resolution policy")
_HISTORICAL = R.PAXMAN_SPEC_COUNTRY.section("historical name map")
_ALIAS = R.PAXMAN_SPEC_COUNTRY.section("bundled alias table")
_EXTRA_SYNONYM = R.PAXMAN_SPEC_COUNTRY.section("extra_synonyms policy")
_KIND_GATING = R.PAXMAN_SPEC_COUNTRY.section("kind-gating policy")
_MISSING = R.PAXMAN_SPEC_COUNTRY.section("missing value policy")

# Law 14 rule->authority manifest.
#
# - Dispatch invariants cite MANDATE SPI sections (§5.1): they are NOT
#   exempt from citation (Law 14 — empty authority is a violation).
# - Paxman-defined policy rules reference the recorded policy authorities
#   (Law 14) so amendments are traceable to every citing rule.
# - External-spec rules cite the specification directly.
_RULE_AUTHORITIES: Mapping[str, Authority | None] = MappingProxyType(
    {
        # --- dispatch invariants (cite MANDATE SPI, never None) ---
        "not_a_country_contract": R.MANDATE.section(
            "§5.1 (capability handles only its own contract kind)"
        ),
        "not_a_string_value": R.MANDATE.section(
            "§5.1 (canonicalize(value, contract): value is None or str)"
        ),
        # --- recognition / canonicalization (ISO 3166-1 + recorded policy) ---
        "trimmed_whitespace": R.PAXMAN_SPEC_COUNTRY.section("whitespace-trim policy"),
        "recognized_alpha2": _ALPHA2,
        "recognized_alpha3": _ALPHA3,
        "recognized_numeric": _NUMERIC,
        "recognized_name": _NAME,
        "canonicalized_country": _CANONICAL,
        "numeric_resolved": _NUMERIC_RESOLVED,
        "localized_resolved": _LOCALIZED,
        "historical_resolved": _HISTORICAL,
        "alias_resolved": _ALIAS,
        "extra_synonym_resolved": _EXTRA_SYNONYM,
        "policy_disabled_kind": _KIND_GATING,
        "missing_value": _MISSING,
        "unrecognized_format": R.ISO_3166.section("input is not a recognized country token"),
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 authority from the manifest.

    A rule with no manifest entry raises `KeyError` at the construction
    site, surfacing a missing citation immediately.
    """
    return _provenance_evidence(rule, _RULE_AUTHORITIES, detail)

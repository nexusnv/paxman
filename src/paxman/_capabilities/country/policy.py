# src/paxman/_capabilities/country/policy.py
"""Recorded Paxman-defined policies for the country capability (Law 14 §826).

Every provenance string that cites a Paxman-defined policy (rather than an
external specification) is declared HERE as a named constant. This keeps all
country-capability policy assertions in one auditable place and makes a policy
amendment traceable: edit the constant here and every rule that references it
via `_RULE_AUTHORITIES` is located by name. Each constant's docstring records the
MANDATE section or spec section that authorizes the policy (MANDATE §826 bullet
3 — "the policy is recorded in MANDATE, an ADR, or the capability's spec").
"""

from __future__ import annotations

from paxman._capabilities._iso3166 import COUNTRY_TABLE_VERSION

__all__ = [
    "COUNTRY_POLICY_CONVENIENCE_ALIASES",
    "COUNTRY_POLICY_EXTRA_SYNONYMS",
    "COUNTRY_POLICY_HISTORICAL",
    "COUNTRY_POLICY_KIND_GATING",
    "COUNTRY_POLICY_LOCALIZED",
    "COUNTRY_POLICY_MISSING_VALUE",
    "COUNTRY_POLICY_NUMERIC",
    "COUNTRY_POLICY_WHITESPACE_TRIM",
]

# Whitespace trim before recognition. MANDATE §5.1 (SPI: canonicalize(value,
# contract)); deterministic, idempotent, no guessing.
COUNTRY_POLICY_WHITESPACE_TRIM: str = (
    "paxman policy/country: ASCII whitespace is trimmed before recognition "
    "(MANDATE.md §5.1 — SPI canonicalize(value, contract))"
)

# Caller-supplied alias map. MANDATE §5.3 (users may teach Paxman new facts);
# Law 8a (bundled/versioned state); spec/country §1.2.
COUNTRY_POLICY_EXTRA_SYNONYMS: str = (
    "paxman policy/country: extra_synonyms let the caller extend the alias "
    "table (MANDATE.md §5.3; Law 8a; spec/country §1.2)"
)

# Representation-kind gating (allow_alpha3 / allow_name / allow_synonym /
# allow_numeric / localized_names / historical_names). MANDATE Law 5 (contract
# declares policy, not how); Law 7 (explicit over clever); spec/country §3.5.
COUNTRY_POLICY_KIND_GATING: str = (
    "paxman policy/country: contract flags gate representation kinds "
    "(MANDATE.md Law 5 + Law 7; spec/country §3.5)"
)

# ISO 3166-1 numeric (M49) recognition. MANDATE Law 5 (contract is truth) +
# Law 8a (versioned dataset); spec/country §3.1.
COUNTRY_POLICY_NUMERIC: str = (
    f"paxman policy/country: numeric (M49) codes are accepted when "
    f"allow_numeric is set (MANDATE.md Law 5; Law 8a; spec/country §3.1; "
    f"dataset {COUNTRY_TABLE_VERSION})"
)

# Unicode CLDR localized name recognition (opt-in). CLDR is a versioned
# authoritative specification (Law 14 source #1); opt-in per Law 7 (data
# footprint). The bundled _LOCALIZED_TO_ALPHA2 is a CURATED SAMPLE, not the
# full CLDR, and is therefore adopted under Law 15's "non-named-entity
# bulk-data scope boundary" exception: CLDR localized strings are bulk
# reference data, not a named-entity enumeration, and the subset is chosen
# for data-footprint reasons (Law 7 — explicit opt-in keeps the default
# surface small). The cited named-entity source (ISO 3166-1:2024) is adopted
# in full elsewhere (_NAME_TO_ALPHA2); this CLDR sample is a separate,
# explicitly-scoped bulk dataset.
COUNTRY_POLICY_LOCALIZED: str = (
    "paxman policy/country: localized (CLDR) names accepted when "
    "localized_names is set (Unicode CLDR; MANDATE.md Law 14 source #1; "
    "curated sample under Law 15 non-named-entity bulk-data scope boundary, "
    "data-footprint per Law 7)"
)

# Convenience aliases retained in _NAME_TO_ALPHA2 that are NOT official ISO
# 3166-1 short names (e.g. "UNITED STATES", "SOUTH KOREA", "RUSSIA"). These
# are recorded as a Law 15-permitted addition: the cited named-entity source
# (ISO 3166-1:2024) is adopted in FULL, and these extra entries are
# backward-compatible shortcuts outside that cited source. Their existence is
# recorded here so the exception justification is auditable provenance (Law 15
# + Law 14 source #3).
COUNTRY_POLICY_CONVENIENCE_ALIASES: str = (
    "paxman policy/country: short convenience aliases (e.g. UNITED STATES, "
    "SOUTH KOREA, RUSSIA) retained for backward compatibility; ISO 3166-1:2024 "
    "adopted in full, these are extra entries outside the cited source "
    "(Law 15 permitted addition; Law 14 source #3)"
)

# Historical / deprecated name recognition (opt-in). Recorded Paxman policy
# (Law 14 §826 bullet 3 — spec/country §3.4 historical map).
COUNTRY_POLICY_HISTORICAL: str = (
    "paxman policy/country: historical names accepted when historical_names "
    "is set (recorded Paxman policy; spec/country §3.4)"
)

# Empty / None input is MISSING. MANDATE Law 8 (fail informatively: the
# contract requires a field the input does not provide).
COUNTRY_POLICY_MISSING_VALUE: str = (
    "paxman policy/country: empty/None input is MISSING (MANDATE.md Law 8 — required value absent)"
)

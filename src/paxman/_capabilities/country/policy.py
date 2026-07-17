# src/paxman/_capabilities/country/policy.py
"""Recorded Paxman-defined policies for the country capability (Law 14 §826).

Every provenance string that cites a Paxman-defined policy (rather than an
external specification) is declared HERE as a named constant. This keeps all
country-capability policy assertions in one auditable place and makes a policy
amendment traceable: edit the constant here and every rule that references it
via `_RULE_PROVENANCE` is located by name. Each constant's docstring records the
MANDATE section or spec section that authorizes the policy (MANDATE §826 bullet
3 — "the policy is recorded in MANDATE, an ADR, or the capability's spec").
"""

from __future__ import annotations

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

# Representation-kind gating (allow_alpha3 / allow_name / allow_synonym).
# MANDATE Law 5 (contract declares policy, not how); Law 7 (explicit over
# clever); spec/country §3.5.
COUNTRY_POLICY_KIND_GATING: str = (
    "paxman policy/country: contract flags gate representation kinds "
    "(MANDATE.md Law 5 + Law 7; spec/country §3.5)"
)

# Empty / None input is MISSING. MANDATE Law 8 (fail informatively: the
# contract requires a field the input does not provide).
COUNTRY_POLICY_MISSING_VALUE: str = (
    "paxman policy/country: empty/None input is MISSING "
    "(MANDATE.md Law 8 — required value absent)"
)

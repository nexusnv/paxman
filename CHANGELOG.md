# Changelog

All notable changes to Paxman are documented here. This project adheres to
semantic versioning; entries are grouped by release.

## [Unreleased]

### Constitutional — Law 15 (cited named-entity sources adopted in full)

MANDATE Law 15 requires that any capability citing a named-entity enumeration
(countries, peoples, currencies, languages, scripts, jurisdictions) must embody
that source **in full** or not cite it. The following capabilities were brought
into full compliance:

- **phone** — The ISO 3166-1 alpha-2 → ITU-T E.164 country-code table
  (`_COUNTRY_TO_CC`) was back-filled from a ~18-code "common regions" subset to
  **all 249 officially assigned ISO 3166-1:2020 alpha-2 codes**, each mapped to
  its E.164 calling code. The table is now asserted complete against the shared
  `_ALPHA2_CODES` set at import time, so a partial adoption can never silently
  reappear. The provenance reference (`COUNTRY_TABLE_VERSION = "iso3166-1:2020"`)
  is imported from the single shared `_iso3166` module — it is no longer
  duplicated in the phone package.

- **money** — `_ISO4217_CODES` (the contract's accepted-currency gate) was
  back-filled to the **complete ISO 4217:2015 active code list** (177 codes;
  withdrawn BGN and HRK excluded per their 2026/2023 euro adoptions); no
  curated subset remains. `_SYMBOL_TO_CODE` and `_COMMA_DECIMAL_CURRENCIES`
  are intentionally scoped convention tables (recognition aids, not the
  named-entity enumeration): the symbol map is sourced from Unicode CLDR
  currency symbol data, and the comma-decimal set from CLDR currency number
  patterns. A new `MONEY_TABLE_VERSION` constant cites the frozen edition,
  and the currency/symbol/code rules in `_RULE_PROVENANCE` now cite their
  actual sources (ISO 4217 for code validation, CLDR for symbols and decimal
  conventions).

- **country** — the country capability's bundled ISO 3166-1:2020 dataset
  (alpha-2 codes, alpha-3→alpha-2, numeric→alpha-2, official names, synonyms)
  was extracted into the shared `_iso3166` module so the country and phone
  capabilities cite the single shared `COUNTRY_TABLE_VERSION` constant. All
  bundled lookup tables are now wrapped in `MappingProxyType` for runtime
  immutability (Law 1 + Law 2). The `extra_synonyms` contract field is frozen
  on construction via an attrs converter. Shared currency symbols (C$, kr, Bs)
  are now accepted for any of their permitted currencies, and ILS was moved
  off the comma-decimal convention (CLDR uses dot-decimal for ILS).

### Shared provenance module

- Added `src/paxman/_capabilities/_iso3166.py` — the single authoritative home
  for the ISO 3166-1:2020 dataset (`COUNTRY_TABLE_VERSION`, `_ALPHA2_CODES`,
  `_NAME_TO_ALPHA2`, `_SYNONYM_TO_ALPHA2`, `_NUMERIC_TO_ALPHA2`). Both the
  country and phone capabilities import from it, so the cited provenance string
  is defined in exactly one place (MANDATE Law 15 — no duplicated citation).

### date — supported-language subset (ongoing expansion)

- The date capability supports **three** languages for month/weekday-name
  recognition: `en`, `de`, `ms`. This is a **declared supported subset**, not an
  embodiment of the ISO 639 language-code standard — ISO 639 only encodes
  language *identities* (that `ms` denotes Malay), not the actual day/month
  *names* (which are declared Paxman policy). Each supported language's
  vocabulary is itself complete; the set grows by adding whole languages, never
  by partially covering one. More languages will be added over time, much like a
  translation matrix.

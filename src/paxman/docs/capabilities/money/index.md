# Money Capability — ISO 4217 Provenance

The money capability canonicalizes a money string into `<ISO4217>:<amount>`,
where the currency is taken from the contract (never guessed — MANDATE Law 3).

## Cited source (MANDATE Law 14 + Law 15)

- **ISO 4217:2015** (maintained by the SIX Group Maintenance Agency; amendments
  through #179, effective 2026-01-01). The frozen edition is recorded as
  `MONEY_TABLE_VERSION` and cited by the currency/symbol/code rules in
  `_RULE_PROVENANCE`.

ISO 4217 is a named-entity enumeration (currencies). Per Law 15 it is adopted
**in full**: `_ISO4217_CODES` contains the complete active code list (180 codes:
166 national/supranational + 14 X-codes). Withdrawn codes `BGN` (Bulgaria,
euro adoption 2026-01-01) and `HRK` (Croatia, euro adoption 2023-01-01) are
excluded, matching the cited edition's active set. There is no curated subset.

## Symbol and decimal-convention tables

- `_SYMBOL_TO_CODE` maps currency symbols (e.g. `$`, `€`, `RM`) to their ISO 4217
  code. Every target is a valid ISO 4217 code; the map is a recognition aid, not
  a separate named-entity source.
- `_COMMA_DECIMAL_CURRENCIES` lists the currencies that conventionally use a
  comma decimal separator / dot thousands separator (per CLDR currency patterns).
  Ambiguous cases (CHF currency uses a period) stay on the dot-decimal
  convention for determinism. This is a convention subset of the ISO 4217 set,
  not a partial adoption of a named-entity source.

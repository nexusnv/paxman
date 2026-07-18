# Phone Capability — ISO 3166-1 / E.164 Provenance

The phone capability expands a national number to global E.164 form
(`+<cc><national>`) using the calling code declared by the contract's `country`
field (an ISO 3166-1 alpha-2 code).

## Cited Source (MANDATE Law 14 + Law 15)

- **ISO 3166-1:2020** — the enumeration of countries the `country` field may
  name. Embodied in full (all 249 officially assigned alpha-2 codes).
- **ITU-T E.164** country calling-code list (Annex to ITU Operational Bulletin
  No. 1114, 15.XII.2016; complement to ITU-T Recommendation E.164 (11/2010)) —
  the calling-code assignment for each alpha-2 code.

Both are referenced through the single shared `COUNTRY_TABLE_VERSION` constant in
`src/paxman/_capabilities/_iso3166.py`. The phone package does **not** redefine
the citation string; it imports it, so the provenance reference exists in exactly
one place.

## Completeness Guarantee

`_COUNTRY_TO_CC` maps every code in `_ALPHA2_CODES` (the full ISO 3166-1:2020
set). `parser.py` raises an explicit `RuntimeError` at import time if the map
ever diverges from that set — this guard uses `raise` rather than `assert` so it
remains active under optimized Python execution (`python -O`, which strips
`assert` statements). A partial adoption (the Law 15 failure mode) cannot
reappear unnoticed.

Kosovo (`XK` -> 383) is intentionally excluded: `XK` is a user-assigned code, not
part of ISO 3166-1:2020, so adding it would place data outside the cited source.

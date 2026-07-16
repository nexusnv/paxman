# Phone Capability Changelog

## v1 (2026-07-16)

- Initial capability: recognition Layer 1 grammars (`e164`, `national`,
  `digits_only`), resolver (strip separators + prepend declared country
  code), validator (E.164 global shape), classifier.
- Contract: `Phone(country: str = "US")` (ISO 3166-1 alpha-2).
- No external dataset dependency; E.164 global-shape validation only.

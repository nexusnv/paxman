# Phone Capability (`phone_canonicalization`)

Canonicalizes telephone-number strings into the ITU-T E.164 global form
(`+<cc><national>`), rendered per RFC 3966 §3.

## Contract

```python
from paxman import Phone

Phone(country="US")   # ISO 3166-1 alpha-2; default "US"
```

The `country` field is the only policy lever: it supplies the country code
used to expand national-format numbers. There is no region inference.

## Rules (Law 14)

| Rule | Fires when | Citation |
|---|---|---|
| `not_a_phone_contract` | contract is not `CanonicalPhoneContract` | (allow-list) |
| `not_a_string_value` | value is not a `str` | (allow-list) |
| `unrecognized_format` | no grammar matches (no `+` global, national, or digits-only shape) | RFC 3966 §3 |
| `grammar_rejected` | candidate fails E.164 shape (1-15 digits; cc first digit 1-9) | RFC 3966 §3 / ITU-T E.164 |
| `no_transformation_needed` | input already E.164 global form | RFC 3966 §3 |

## Examples

| Input | Contract | Output |
|---|---|---|
| `+16502530000` | `Phone()` | `+16502530000` |
| `(650) 253-0000` | `Phone(country="US")` | `+16502530000` |
| `2079460000` | `Phone(country="GB")` | `+442079460000` |

## Limitations (drift excluded by mandate)

- No region guessing / fuzzy matching (Law 3).
- No carrier / line-type / geo interpretation (Law 4, Law 8a).
- No per-country numbering-plan validation beyond the E.164 global shape in v1.
- `00`-prefixed international strings are not rewritten (only `+` global form is recognized).

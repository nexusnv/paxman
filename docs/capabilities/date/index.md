# Date Capability

The date capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings into date representations. It is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `date_canonicalization`

**Contract kind:** `canonical_date`

**Contract factory:** `Date()`

## What It Does

The date capability rewrites a string into a single canonical form. The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Date(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Evidence Rules

| Rule | Citation |
|---|---|
| `not_a_date_contract` | (dispatch invariant) |\n| `not_a_string_value` | (dispatch invariant) |\n| `empty_value` | (dispatch invariant) |\n| `unrecognized_format` | (dispatch invariant) |\n| `numeric_format_requires_us_or_eu_locale` | paxman spec/date (ISO locale rejects slash forms; Law 7) |\n| `invalid_iso_format` | ISO 8601:2004 §5.2.1 |\n| `invalid_calendar_date` | ISO 8601:2004 (Gregorian calendar validity) |\n| `ambiguous_two_digit_year` | paxman spec/date (2-digit year with no `two_digit_year` century policy; Don't Guess -> AMBIGUOUS) |\n| `ambiguous_naive_datetime` | RFC 3339 §5.6 (unknown local offset convention) |\n| `invalid_epoch_value` | POSIX/IEEE 1003.1 (epoch seconds out of representable range) |\n| `parsed_iso_date` | ISO 8601:2004 §5.2.1 |\n| `parsed_iso_datetime` | RFC 3339 |\n| `parsed_us_numeric` | paxman spec/date (US MM/DD/YYYY reading) |\n| `parsed_eu_numeric` | paxman spec/date (EU DD/MM/YYYY reading) |\n| `parsed_rfc2822` | RFC 2822 §3.3 |\n| `parsed_unix_timestamp` | POSIX/IEEE 1003.1 (epoch seconds) + RFC 3339 |\n| `normalized_to_utc` | RFC 3339 §4.1 (instant equivalence) + §4.2 (Z designator) |\n| `no_transformation_needed` | ISO 8601:2004 §5.2.1 / RFC 3339 (input already canonical) |\n| `parsed_text_month_date` | paxman spec/date (full/abbrev month name in declared language; Law 14 declared Paxman policy — no single RFC governs multilingual month names) |\n| `parsed_numeric_date` | paxman spec/date (numeric slash form enumerated per locale ordering; architectural discussion §2) |\n| `parsed_numeric_ymd_date` | paxman spec/date (year-first numeric slash, ISO 8601 slash ordering; fixed Y/M/D reading — no locale ordering enumeration) |\n| `ambiguous_ordering` | paxman spec/date (MM/DD and DD/MM both survive under locale=ISO; Don't Guess -> AMBIGUOUS) |\n| `rejected_two_digit_year` | paxman spec/date (`two_digit_year='reject'` policy) |\n| `weekday_contradicts_date` | paxman spec/date (semantic validation: weekday must match calendar; architectural discussion §3 Stage 4) |

## Recognition Layer 1

Before any rewriting, the capability runs `grammar.recognize` over the input. Recognition assigns **no meaning** — it returns only raw captures. The resolver then assigns meaning to the captures and maps the survivors to a `Status`.

## Status Outcomes

- **CANONICALIZED:** The input was successfully matched and canonicalized.
- **INVALID:** The input was rejected due to an unrecognized format or policy restriction.
- **MISSING:** The input was empty or purely whitespace.
- **AMBIGUOUS:** (where applicable) The input could not be definitively resolved.
- **UNSUPPORTED:** (where applicable) The input format is known but explicitly not supported.

## Quickstart

```python
import paxman
from paxman import Date, Status

result = paxman.canonicalize("example_input", Date())
```

## References

- **Source Module:** [`src/paxman/_capabilities/date`](../../../src/paxman/_capabilities/date)
- **Contracts Reference:** [Contracts](../../reference/contracts.md)

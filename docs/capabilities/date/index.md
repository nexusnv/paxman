# Date Capability

The date capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings that represent calendar dates and datetimes into a single ISO 8601 / RFC 3339 form. It supports multilingual text-month dates, numeric slash forms, compact forms, RFC 2822 forms, and Unix epoch timestamps. The capability is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `date_canonicalization`

**Contract kind:** `canonical_date`

**Contract factory:** `Date()`

## What It Does

The date capability rewrites a string into a single canonical date or datetime form. It does not guess: when the input admits more than one reading (ambiguity from MM/DD vs DD/MM ordering, or a two-digit year without a century policy), the capability reports `Status.AMBIGUOUS` and lists every surviving candidate rather than picking one.

The canonical form is `YYYY-MM-DD` for dates and `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` for datetimes (RFC 3339, normalized to UTC). When `output_format="compact"`, the canonical form is `YYYYMMDD` or `YYYYMMDDTHHMMSSZ`.

The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Date(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Contract Fields

Every field is a policy declaration. There is no auto-detection; the contract declares what canonical means, and the capability applies it.

| Field | Type | Default | What it does |
|---|---|---|---|
| `locale` | `"ISO"`, `"US"`, or `"EU"` | `"ISO"` | Declares the numeric slash ordering policy. `"US"` reads MM/DD/YYYY, `"EU"` reads DD/MM/YYYY, `"ISO"` enumerates both orderings (reporting `AMBIGUOUS` when ambiguous). |
| `language` | `str` | `"en"` | Selects the month/weekday name table. Supported: `"en"`, `"de"`, `"ms"`. |
| `two_digit_year` | `None`, `"reject"`, `"require_four_digit_year"`, or `"pivot:YYYY"` | `None` | The century expansion policy for two-digit years. `None` expands across 1900/2000/2100 (reporting `AMBIGUOUS`). `"reject"` rejects two-digit years. `"pivot:YYYY"` resolves a single century from the pivot year. |
| `output_format` | `"iso"` or `"compact"` | `"iso"` | The canonical output form. `"iso"` produces `YYYY-MM-DD`, `"compact"` produces `YYYYMMDD`. |

The `kind` and `version_field` fields are fixed (`"canonical_date"` and `1` respectively). They are not part of the `Date()` factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Transforming Rules (Fire on Success)

These rules rewrite the input into the canonical form. They are recorded on the artifact in execution order.

| Rule | When it fires | Citation |
|---|---|---|
| `parsed_iso_date` | The input matched `YYYY-MM-DD`. | ISO 8601 section 5.2.1 |
| `parsed_iso_datetime` | The input matched `YYYY-MM-DDTHH:MM:SS[.fff](Z\|+HH:MM)` and was normalized to UTC. | RFC 3339 |
| `parsed_us_numeric` | The input matched `MM/DD/YYYY` under `locale="US"`. | Paxman spec/date (US MM/DD/YYYY reading) |
| `parsed_eu_numeric` | The input matched `DD/MM/YYYY` under `locale="EU"`. | Paxman spec/date (EU DD/MM/YYYY reading) |
| `parsed_rfc2822` | The input matched an RFC 2822 form (`1 Jan 2025`, `Tue, 01 Jan 2025 12:00:00 +0000`). | RFC 2822 section 3.3 |
| `parsed_unix_timestamp` | The input was a Unix epoch timestamp (integer or float seconds). | POSIX/IEEE 1003.1 + RFC 3339 |
| `normalized_to_utc` | A datetime input with a timezone offset was converted to UTC (`Z` designator). | RFC 3339 section 4.1 + section 4.2 |
| `parsed_compact_date` | The input matched `YYYYMMDD` (compact date). | ISO 8601 (compact YYYYMMDD re-parsable form) |
| `parsed_compact_datetime` | The input matched `YYYYMMDDTHHMMSSZ` (compact datetime). | RFC 3339 (compact re-parsable form) |
| `parsed_text_month_date` | The input matched a text-month form (`16 July 2026`, `July 16, 2026`, `the 3rd of July, 2026`). | Paxman spec/date (full/abbrev month name in declared language) |
| `parsed_numeric_date` | The input matched a numeric slash form (`MM/DD/YYYY` or `DD/MM/YYYY`) under the locale ordering. | Paxman spec/date (numeric slash form enumerated per locale ordering) |
| `parsed_numeric_ymd_date` | The input matched `YYYY/MM/DD` (year-first, fixed Y/M/D reading under every locale). | Paxman spec/date (year-first numeric slash, ISO 8601 slash ordering) |
| `no_transformation_needed` | The input was already in canonical form. | ISO 8601 section 5.2.1 / RFC 3339 (input already canonical) |
| `output_format_compact` | The output format is `"compact"` and the canonical value was converted. | Paxman spec/date (output_format compact rendering) |

### Rejecting Rules (Fire on Rejection)

These rules cause the capability to return `Status.INVALID` (or `Status.AMBIGUOUS`) with evidence entries. The string is *not* canonicalized; the artifact holds no `value`.

| Rule | When it fires | Citation |
|---|---|---|
| `not_a_date_contract` | The contract is not a `CanonicalDateContract`. (Defensive; the orchestrator normally routes date contracts to this capability.) | (dispatch invariant) |
| `not_a_string_value` | The value is not a `str`. | (dispatch invariant) |
| `empty_value` | The value is empty or whitespace-only. | (dispatch invariant) |
| `unrecognized_format` | The input did not match any date grammar. | (dispatch invariant) |
| `invalid_calendar_date` | The parsed month/day/year does not name a valid calendar date (e.g. February 30). | ISO 8601 (Gregorian calendar validity) |
| `invalid_iso_format` | The input matched an ISO datetime shape but contained an invalid field. | ISO 8601 section 5.2.1 |
| `ambiguous_two_digit_year` | A two-digit year with no `two_digit_year` century policy produces multiple century-expanded readings. Result is `Status.AMBIGUOUS`. | Paxman spec/date (2-digit year with no century policy; Don't Guess) |
| `ambiguous_naive_datetime` | A datetime without a timezone offset (e.g. `2025-01-01T12:00:00`) is ambiguous per RFC 3339. Result is `Status.AMBIGUOUS`. | RFC 3339 section 5.6 (unknown local offset convention) |
| `rejected_two_digit_year` | `two_digit_year="reject"` or `"require_four_digit_year"` and the input has a two-digit year. | Paxman spec/date (`two_digit_year='reject'` policy) |
| `weekday_contradicts_date` | The input includes a weekday name that does not match the calendar date (e.g. `Tuesday, 01 Jan 2025` when 1 Jan 2025 is a Wednesday). | Paxman spec/date (weekday must match calendar) |
| `numeric_format_requires_us_or_eu_locale` | A numeric slash form was found but `locale="ISO"` does not unambiguously resolve it. Result is `Status.AMBIGUOUS`. | Paxman spec/date (ISO locale rejects slash forms; Law 7) |
| `invalid_epoch_value` | A Unix epoch timestamp fell outside the representable datetime range. | POSIX/IEEE 1003.1 (epoch seconds out of representable range) |

## Worked Examples

### Example 1: A US-Format Date

```python
import paxman
from paxman import Date, Status

result = paxman.canonicalize("03/04/2025", Date(locale="US"))
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"2025-03-04"`
- `result.evidence` includes `Evidence(rule="parsed_us_numeric", ...)`

### Example 2: An ISO Datetime with Timezone

```python
result = paxman.canonicalize("2025-01-01T07:00:00-05:00", Date())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"2025-01-01T12:00:00Z"`
- `result.evidence` includes `Evidence(rule="parsed_iso_datetime", ...)` and `Evidence(rule="normalized_to_utc", ...)`

### Example 3: Ambiguous Slash Form Under ISO

```python
result = paxman.canonicalize("07/04/2025", Date(locale="ISO"))
```

- `result.status` is `Status.AMBIGUOUS`
- `result.value` is `None`
- `result.candidates` is `("2025-04-07", "2025-07-04")` (both MM/DD and DD/MM survive)
- `result.evidence` includes `Evidence(rule="ambiguous_ordering", ...)`

## Limitations of v2.0.0

The v2.0.0 date capability is intentionally narrow. It does not accept:

- Relative date expressions (`yesterday`, `next Tuesday`, `3 days ago`).
- Date ranges or partial dates (`2025-03`, `March 2025` without a day).
- Julian day numbers or Modified Julian Dates.
- Non-Gregorian calendars (Julian, Islamic, Hebrew, etc.).
- Dates before year 1 or after year 9999.
- Timezone names (only numeric offsets and `Z` are recognized).

Future v2.x versions may extend the grammar or add timezone-name support. The contract `version` is part of the artifact's `VersionStamp`; upgrading the grammar is a contract-version bump that will be visible on every new artifact.

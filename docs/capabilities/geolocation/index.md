# Geolocation Capability

The geolocation capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings into geolocation representations. It is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `geolocation_canonicalization`

**Contract kind:** `canonical_geolocation`

**Contract factory:** `Geolocation()`

## What It Does

The geolocation capability rewrites a string into a single canonical form. The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Geolocation(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Evidence Rules

| Rule | Citation |
|---|---|
| `not_a_geolocation_contract` | (dispatch invariant) |\n| `not_a_string_value` | (dispatch invariant) |\n| `trimmed_whitespace` | paxman spec/geolocation §3.1 (ASCII whitespace trim) |\n| `recognized_decimal_pair` | paxman spec/geolocation §3.1 (decimal-pair shape) |\n| `recognized_decimal_hemisphere` | paxman spec/geolocation §3.1 (hemisphere-letter shape) |\n| `recognized_dms` | paxman spec/geolocation §3.1 (DMS shape) |\n| `canonicalized_geolocation` | ISO 6709 (geographic point coord) + WGS84 datum |\n| `axis_order_applied` | paxman spec/geolocation §4.1 (coordinate_order policy) |\n| `hemisphere_resolved` | paxman spec/geolocation §4.1 (N/S/E/W or sign) |\n| `hemisphere_defaulted` | paxman spec/geolocation §4.1 (require_hemisphere=False, positive default) |\n| `dms_to_decimal` | ISO 6709 + WGS84 (DMS→decimal exact conversion) |\n| `precision_applied` | paxman spec/geolocation §4.2 (literal decimal places preserved) |\n| `out_of_range` | paxman spec/geolocation §5 (lat/long range violation) |\n| `ambiguous_hemisphere` | paxman spec/geolocation §4.1 / Law 4 (unsigned axis, hemisphere required) |\n| `missing_value` | paxman spec/geolocation §5 (Law 8 — required value absent) |\n| `unrecognized_format` | paxman spec/geolocation §3.1 / §4 (input is not a valid coordinate) |

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
from paxman import Geolocation, Status

result = paxman.canonicalize("example_input", Geolocation())
```

## References

- **Source Module:** [`src/paxman/_capabilities/geolocation`](../../../src/paxman/_capabilities/geolocation)
- **Contracts Reference:** [Contracts](../../reference/contracts.md)

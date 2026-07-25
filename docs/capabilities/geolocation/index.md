# Geolocation Capability

The geolocation capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings that represent geographic coordinates into a single decimal-degrees form (`"latitude,longitude"`) on the WGS84 datum. It accepts signed decimal pairs, hemisphere-letter forms (`N`/`S`/`E`/`W`), and degree-minute-second (DMS) notation. The capability is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `geolocation_canonicalization`

**Contract kind:** `canonical_geolocation`

**Contract factory:** `Geolocation()`

## What It Does

The geolocation capability rewrites a coordinate string into a single canonical form: `"<latitude>,<longitude>"` in decimal degrees, quantized to the contract's declared precision. The canonical output always uses latitude-first ordering regardless of the input's axis order. DMS notation is converted to decimal degrees using exact arithmetic (`Decimal`, not `float`). Hemisphere is resolved from explicit signs or N/S/E/W letters; unsigned axes under a hemisphere-requiring contract report `Status.AMBIGUOUS` with competing positive/negative readings rather than guessing.

The capability does not interpret place names, addresses, or reverse-geocode. It canonicalizes numeric coordinate representations only.

The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Geolocation(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

### Recognized Input Shapes

| Shape | Example | Description |
|---|---|---|
| `geo_decimal_pair` | `33.4484, -112.0740` | Two signed decimal numbers separated by a comma. Parenthesized form `(33.4484, -112.0740)` is also accepted. |
| `geo_decimal_hemi` | `33.4484N 112.0740W` | Decimal numbers with N/S/E/W hemisphere letters. |
| `geo_dms` | `33°26'54.2"N 112°4'26.4"W` | Degree-minute-second notation with degree/minute/second symbols and hemisphere letters. |
| `geo_dms_signed` | `33 26 54.2, -112 4 26.4` | Space-separated DMS components with signed degrees, comma-separated axes. |

## The Contract Fields

Every field is a policy declaration. There is no auto-detection; the contract declares what canonical means, and the capability applies it.

| Field | Type | Default | What it does |
|---|---|---|---|
| `datum` | `str` | `"WGS84"` | The geodetic datum. Only `"WGS84"` is supported in v2.0.0. |
| `coordinate_order` | `"lat_lon"` or `"lon_lat"` | `"lat_lon"` | The order of latitude/longitude in the INPUT. The canonical output is always `"latitude,longitude"` regardless of this setting. |
| `require_hemisphere` | `bool` | `True` | Require an explicit hemisphere signal (sign or N/S/E/W letter) on each axis. When `True`, an unsigned axis without a hemisphere letter produces `Status.AMBIGUOUS` (two competing readings) or `Status.INVALID` (out of range). When `False`, unsigned axes default to positive. |
| `output_format` | `"decimal"` | `"decimal"` | The canonical output form. Only `"decimal"` (decimal degrees) is supported in v2.0.0. |
| `precision` | `int` (0..12) | `6` | Number of decimal places in the canonical output. Must be an integer between 0 and 12 inclusive. |

The `kind`, `version`, and `version_field` fields are fixed (`"canonical_geolocation"`, `1`, and `1` respectively). They are not part of the `Geolocation()` factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Transforming Rules (Fire on Success)

These rules rewrite the input into the canonical form. They are recorded on the artifact in execution order.

| Rule | When it fires | Citation |
|---|---|---|
| `trimmed_whitespace` | Leading or trailing ASCII whitespace was removed from the input. | Paxman spec/geolocation section 3.1 (ASCII whitespace trim) |
| `recognized_decimal_pair` | The input matched the decimal-pair shape. | Paxman spec/geolocation section 3.1 (decimal-pair shape) |
| `recognized_decimal_hemisphere` | The input matched the hemisphere-letter shape. | Paxman spec/geolocation section 3.1 (hemisphere-letter shape) |
| `recognized_dms` | The input matched a DMS shape (with symbols or signed degrees). | Paxman spec/geolocation section 3.1 (DMS shape) |
| `axis_order_applied` | The contract's `coordinate_order` policy was applied to assign axes to latitude/longitude. | Paxman spec/geolocation section 4.1 (coordinate_order policy) |
| `hemisphere_resolved` | A hemisphere signal (letter or sign) resolved the sign of an axis. | Paxman spec/geolocation section 4.1 (N/S/E/W or sign) |
| `hemisphere_defaulted` | `require_hemisphere=False` and no hemisphere signal was present; axes defaulted to positive. | Paxman spec/geolocation section 4.1 (require_hemisphere=False, positive default) |
| `dms_to_decimal` | A DMS input was converted to decimal degrees. | ISO 6709 + WGS84 (DMS to decimal exact conversion) |
| `precision_applied` | The canonical value was quantized to the contract's declared precision. | Paxman spec/geolocation section 4.2 (literal decimal places preserved) |
| `canonicalized_geolocation` | The final canonical form was produced. | ISO 6709 (geographic point coord) + WGS84 datum |

### Rejecting Rules (Fire on Rejection)

These rules cause the capability to return `Status.INVALID` (or `Status.AMBIGUOUS`) with evidence entries. The string is *not* canonicalized; the artifact holds no `value`.

| Rule | When it fires | Citation |
|---|---|---|
| `not_a_geolocation_contract` | The contract is not a `CanonicalGeolocationContract`. (Defensive; the orchestrator normally routes geolocation contracts to this capability.) | (dispatch invariant) |
| `not_a_string_value` | The value is not a `str`. | (dispatch invariant) |
| `missing_value` | The value is `None` or whitespace-only. | Paxman spec/geolocation section 5 (Law 8: required value absent) |
| `unrecognized_format` | The input did not match any geolocation grammar. | Paxman spec/geolocation section 3.1 / section 4 (input is not a valid coordinate) |
| `out_of_range` | The resolved latitude is outside [-90, 90] or longitude is outside [-180, 180]. | Paxman spec/geolocation section 5 (lat/long range violation) |
| `ambiguous_hemisphere` | The input is a decimal pair with no hemisphere signal and `require_hemisphere=True`, so the sign of one or both axes is undetermined. Result is `Status.AMBIGUOUS` with competing readings. | Paxman spec/geolocation section 4.1 / Law 4 (unsigned axis, hemisphere required) |

## Worked Examples

### Example 1: A Normal Decimal Coordinate

```python
import paxman
from paxman import Geolocation, Status

result = paxman.canonicalize("33.4484, -112.0740", Geolocation())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"33.448400,-112.074000"`
- `result.evidence` includes `Evidence(rule="recognized_decimal_pair", ...)`, `Evidence(rule="axis_order_applied", ...)`, and `Evidence(rule="canonicalized_geolocation", ...)`

### Example 2: DMS to Decimal

```python
result = paxman.canonicalize(
    '33°26\'54.2"N 112°4\'26.4"W',
    Geolocation(),
)
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"33.448389,-112.074000"`
- `result.evidence` includes `Evidence(rule="recognized_dms", ...)` and `Evidence(rule="dms_to_decimal", ...)`

### Example 3: Ambiguous Hemisphere

```python
result = paxman.canonicalize("33.4484, 112.0740", Geolocation())
```

- `result.status` is `Status.AMBIGUOUS`
- `result.value` is `None`
- `result.candidates` is `("33.448400,112.074000", "33.448400,-112.074000", "-33.448400,112.074000", "-33.448400,-112.074000")`
- `result.evidence` includes `Evidence(rule="ambiguous_hemisphere", ...)`

## Limitations of v2.0.0

The v2.0.0 geolocation capability is intentionally narrow. It does not accept:

- Place names or addresses (`"Times Square"`, `"1600 Pennsylvania Ave"`).
- Altitude or elevation data (2D coordinates only).
- Coordinate systems other than WGS84 (NAD27, GRS80, etc.).
- DMS output format (only decimal degrees are supported).
- MGRS, UTM, or other projected coordinate systems.
- 3D coordinates with height/depth.

Future v2.x versions may add DMS/DMM output formats or altitude support. The contract `version` is part of the artifact's `VersionStamp`; extending the coordinate model is a contract-version bump.

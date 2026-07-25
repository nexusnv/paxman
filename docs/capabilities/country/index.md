# Country Capability

The country capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings that represent countries into ISO 3166-1 codes. It accepts alpha-2 codes, alpha-3 codes, numeric codes, canonical country names, bundled aliases, localized CLDR names, historical names, and caller-supplied extra synonyms. The capability uses a bundled ISO 3166-1:2024 dataset for all table lookups. It is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `country_canonicalization`

**Contract kind:** `canonical_country`

**Contract factory:** `Country()`

## What It Does

The country capability rewrites a string into a single canonical country code. The default canonical form is ISO 3166-1 alpha-2 (e.g. `"US"`, `"MY"`). The contract can request alpha-3 or numeric output instead. The capability does not guess: when a token matches multiple representation paths that resolve to different countries, or when no table match exists, the input is rejected rather than silently interpreted.

The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Country(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Contract Fields

Every field is a policy declaration. There is no auto-detection; the contract declares what the capability accepts, and the capability applies it.

| Field | Type | Default | What it does |
|---|---|---|---|
| `allow_alpha3` | `bool` | `True` | Accept ISO 3166-1 alpha-3 codes (e.g. `"USA"`, `"MYS"`). When `False`, alpha-3 inputs are rejected with `policy_disabled_kind`. |
| `allow_name` | `bool` | `True` | Accept canonical country names (e.g. `"United States"`, `"Malaysia"`). When `False`, name inputs are rejected with `policy_disabled_kind`. |
| `allow_synonym` | `bool` | `True` | Accept bundled aliases (e.g. `"UK"`, `"U.S.A."`). When `False`, synonym inputs are rejected with `policy_disabled_kind`. |
| `allow_numeric` | `bool` | `True` | Accept ISO 3166-1 numeric (M49) codes (e.g. `"840"`, `"458"`). When `False`, numeric inputs are rejected with `policy_disabled_kind`. |
| `localized_names` | `bool` | `False` | Accept Unicode CLDR localized names (multilingual). Default `False` to keep the default data footprint small. |
| `historical_names` | `bool` | `False` | Accept deprecated/historical names (e.g. `"Burma"` resolves to `"MM"`). Default `False` to keep the default surface stable. |
| `extra_synonyms` | `Mapping[str, str]` | `{}` | A caller-supplied `{alias: alpha2}` mapping. Each target must be a valid ISO 3166-1 alpha-2 code. The mapping is frozen at construction (replayable, Law 8a). |
| `output_format` | `"alpha2"`, `"alpha3"`, or `"numeric"` | `"alpha2"` | The canonical output form. When `"alpha3"`, the canonical alpha-2 code is converted to alpha-3. When `"numeric"`, it is converted to the 3-digit M49 code. |

The `kind`, `version`, and `version_field` fields are fixed (`"canonical_country"`, `1`, and `1` respectively). They are not part of the `Country()` factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Transforming Rules (Fire on Success)

These rules rewrite the input into the canonical form. They are recorded on the artifact in execution order.

| Rule | When it fires | Citation |
|---|---|---|
| `trimmed_whitespace` | Leading or trailing ASCII whitespace was removed from the input. | Paxman spec/country (whitespace-trim policy) |
| `canonicalized_country` | The input was a valid alpha-2 code, a resolved alpha-3 code, a canonical country name, or a resolved synonym. The canonical form is the alpha-2 code. | ISO 3166-1 (alpha-2 canonical form) |
| `numeric_resolved` | The input was a numeric (M49) code resolved to an alpha-2 code. | Paxman spec/country (numeric resolution policy) |
| `alias_resolved` | The input was a bundled alias (e.g. `"UK"`) resolved to an alpha-2 code. | Paxman spec/country (bundled alias table) |
| `localized_resolved` | The input was a CLDR localized name resolved to an alpha-2 code (requires `localized_names=True`). | Paxman spec/country (localized name resolution policy) |
| `historical_resolved` | The input was a historical/deprecated name resolved to an alpha-2 code (requires `historical_names=True`). | Paxman spec/country (historical name map) |
| `extra_synonym_resolved` | The input was a caller-supplied `extra_synonyms` alias resolved to an alpha-2 code. | Paxman spec/country (extra_synonyms policy) |
| `output_format_alpha3` | The output format is `"alpha3"` and the alpha-2 code was converted to alpha-3. | ISO 3166-1 (alpha-3 output format conversion) |
| `output_format_numeric` | The output format is `"numeric"` and the alpha-2 code was converted to a 3-digit M49 code. | ISO 3166-1 (numeric output format conversion) |

### Rejecting Rules (Fire on Rejection)

These rules cause the capability to return `Status.INVALID` with a single evidence entry. The string is *not* canonicalized; the artifact holds no `value`.

| Rule | When it fires | Citation |
|---|---|---|
| `not_a_country_contract` | The contract is not a `CanonicalCountryContract`. (Defensive; the orchestrator normally routes country contracts to this capability.) | MANDATE section 5.1 (capability handles only its own contract kind) |
| `not_a_string_value` | The value is not a `str`. | MANDATE section 5.1 (canonicalize(value, contract): value is None or str) |
| `missing_value` | The value is `None` or whitespace-only. | Paxman spec/country (missing value policy) |
| `unrecognized_format` | The input did not match any country grammar, or matched a shape but was not found in the corresponding table. | ISO 3166-1 (input is not a recognized country token) |
| `policy_disabled_kind` | The input matched a representation kind that the contract disables (e.g. alpha-3 with `allow_alpha3=False`, or name with `allow_name=False`). | Paxman spec/country (kind-gating policy) |

## Worked Examples

### Example 1: A Normal Country Name

```python
import paxman
from paxman import Country, Status

result = paxman.canonicalize("Malaysia", Country())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"MY"`
- `result.evidence` includes `Evidence(rule="canonicalized_country", ...)`

### Example 2: Alpha-3 Code

```python
result = paxman.canonicalize("USA", Country())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"US"`
- `result.evidence` includes `Evidence(rule="canonicalized_country", ...)`

### Example 3: Alpha-3 Output Format

```python
result = paxman.canonicalize("Malaysia", Country(output_format="alpha3"))
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"MYS"`
- `result.evidence` includes `Evidence(rule="canonicalized_country", ...)` and `Evidence(rule="output_format_alpha3", ...)`

### Example 4: Policy Rejection

```python
result = paxman.canonicalize("USA", Country(allow_alpha3=False))
```

- `result.status` is `Status.INVALID`
- `result.value` is `None`
- `result.evidence` is `(Evidence(rule="policy_disabled_kind", ...),)`

## Limitations of v2.0.0

The v2.0.0 country capability is intentionally narrow. It does not accept:

- Sub-national regions (states, provinces, counties).
- Country calling codes (`+1`, `+60`) as country identifiers (those route to the phone capability).
- Fuzzy or partial matches (`"United"` should not resolve to `"United States"`).
- Emoji flags or ISO 3166-2 subdivision codes.
- UN/IOC/special codes beyond the ISO 3166-1 standard.

Future v2.x versions may extend the dataset or add subdivision support.

# Reference: Types

The types you read from and pass to Paxman's public functions. Most are frozen value objects; the one exception is the `CapabilityRegistry`, which is mutable until you call `freeze()` on it.

## Input Types

Types you pass **to** `paxman.canonicalize()`.

### The Contract

Paxman ships ten built-in contract types. Each is a frozen `@attrs.frozen` value object. You declare policy fields (which forms to accept, how to format the output); the capability applies them. Every contract shares three fixed fields (`kind`, `version`, `version_field`) plus a grammar-selector pair (`include_grammar`, `exclude_grammar`) and an `authority_override` escape hatch for testing.

The user-facing factory for each contract is a plain function (`Email()`, `Date()`, `UUID()`, etc.) that returns the corresponding `Canonical*Contract`. Use the factories; they validate inputs and match the documented defaults.

#### `CanonicalEmailContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `lowercase` | `bool` | `True` | Lowercase the local part and domain. |
| `strip_whitespace` | `bool` | `True` | Strip leading/trailing ASCII whitespace. |
| `provider_aliases` | `Literal["none", "gmail"]` | `"none"` | Apply a provider's alias rules. |
| `strict` | `bool` | `False` | Reject inputs with embedded whitespace or non-ASCII characters. |
| `output_format` | `Literal["email"]` | `"email"` | The canonical output form. |

Factory: `Email()`

#### `CanonicalUUIDContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `version` | `Literal["any", "1", "3", "4", "5", "7"]` | `"any"` | Restrict to specific UUID versions. `"any"` accepts all versions. |
| `output_format` | `Literal["hex"]` | `"hex"` | The canonical output form. |

Factory: `UUID()`

#### `CanonicalDateContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `locale` | `Literal["ISO", "US", "EU"]` | `"ISO"` | Slash-ordering policy for ambiguous date forms. `"ISO"` enumerates both `MM/DD` and `DD/MM` (reports `AMBIGUOUS`). |
| `language` | `str` | `"en"` | Month/weekday-name reading table. |
| `two_digit_year` | `Literal["reject", "require_four_digit_year"] \| str \| None` | `None` | Century policy for 2-digit years. `None` means enumerate plausible centuries (reports `AMBIGUOUS`). A `"pivot:YYYY"` string expands via a pivot year. |
| `output_format` | `Literal["iso", "compact"]` | `"iso"` | `"iso"` for `YYYY-MM-DD`, `"compact"` for `YYYYMMDD`. |

Factory: `Date()`

#### `CanonicalPhoneContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `country` | `str` | `"US"` | ISO 3166-1 alpha-2 country code used to expand national numbers into E.164. Declared policy; never inferred. |
| `output_format` | `Literal["e164"]` | `"e164"` | The canonical output form. |

Factory: `Phone()`

#### `CanonicalURLContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `scheme_allow` | `tuple[str, ...] \| None` | `None` | Restrict to these schemes. `None` accepts all schemes. |
| `strip_userinfo` | `bool` | `False` | Remove the `user:info@` portion from the authority. |
| `strip_fragment` | `bool` | `True` | Remove the `#fragment` portion. |
| `sort_query` | `bool` | `False` | Sort query parameters alphabetically. |
| `whatwg` | `bool` | `False` | Use WHATWG URL Standard rules. |
| `output_format` | `Literal["normalized"]` | `"normalized"` | The canonical output form. |

Factory: `URL()`

#### `CanonicalBooleanContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `accept_numeric` | `bool` | `True` | Accept `"1"` / `"0"` as true/false. |
| `accept_words` | `bool` | `True` | Accept yes/no, y/n, t/f, on/off, enabled/disabled. |
| `case_sensitive` | `bool` | `False` | Match tokens case-insensitively when `False`. |
| `output_format` | `Literal["truefalse"]` | `"truefalse"` | The canonical output form. |

Factory: `Boolean()`

#### `CanonicalIPContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `allow_ipv4` | `bool` | `True` | Accept IPv4 inputs. |
| `allow_ipv6` | `bool` | `True` | Accept IPv6 inputs. |
| `preserve_zone_id` | `bool` | `True` | Keep the `%zone` scope identifier on link-local addresses (RFC 4007), lowercased. |
| `output_format` | `Literal["normalized"]` | `"normalized"` | The canonical output form. |

Factory: `IP()`

#### `CanonicalMoneyContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `currency` | `str` | *(required)* | ISO 4217 alpha code. No default; the capability never guesses the currency. |
| `allow_symbol` | `bool` | `True` | Accept currency symbols (`$`/`EUR`/etc.) in input, validated against `currency`. |
| `allow_code` | `bool` | `True` | Accept ISO codes (`"MYR"`) in input, validated against `currency`. |
| `strip_spaces` | `bool` | `True` | Trim ASCII whitespace around the amount. |
| `output_format` | `Literal["iso4217"]` | `"iso4217"` | The canonical output form. |

Factory: `Money()`

#### `CanonicalGeolocationContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `datum` | `str` | `"WGS84"` | Geodetic datum of the coordinates. Only `"WGS84"` is supported in v1. |
| `coordinate_order` | `str` | `"lat_lon"` | Order of latitude/longitude in the input. One of `"lat_lon"` or `"lon_lat"`. The canonical output is always `"latitude,longitude"`. |
| `require_hemisphere` | `bool` | `True` | Require an explicit hemisphere sign (or N/S/E/W) on each coordinate. |
| `output_format` | `Literal["decimal"]` | `"decimal"` | Decimal degrees output. Only `"decimal"` is supported in v1. |
| `precision` | `int` | `6` | Number of decimal places in the canonical output. Must be an int in 0..12. |

Factory: `Geolocation()`

#### `CanonicalCountryContract`

| Field | Type | Default | Description |
|---|---|---|---|
| `allow_alpha3` | `bool` | `True` | Accept ISO 3166-1 alpha-3 codes. |
| `allow_name` | `bool` | `True` | Accept canonical country names. |
| `allow_synonym` | `bool` | `True` | Accept bundled aliases (USA, UK, etc.). |
| `allow_numeric` | `bool` | `True` | Accept ISO 3166-1 numeric (M49) codes. |
| `localized_names` | `bool` | `False` | Accept Unicode CLDR localized names (multilingual). Opt-in; default off to keep data footprint small. |
| `historical_names` | `bool` | `False` | Accept deprecated/historical names (e.g. Burma -> Myanmar). Default off. |
| `extra_synonyms` | `Mapping[str, str]` | `{}` | Caller-supplied `{alias: alpha2}` map. Frozen after construction. |
| `output_format` | `Literal["alpha2", "alpha3", "numeric"]` | `"alpha2"` | The canonical output form. |

Factory: `Country()`

### The `Contract` Union

```python
Contract = (CanonicalEmailContract | CanonicalUUIDContract | CanonicalDateContract |
            CanonicalPhoneContract | CanonicalURLContract | CanonicalBooleanContract |
            CanonicalIPContract | CanonicalMoneyContract | CanonicalGeolocationContract |
            CanonicalCountryContract)
```

This is the type alias you pass to `paxman.canonicalize()`. The DSL parser (`parse_contract`) returns one of these concrete types.

### The Input Value

The first argument to `paxman.canonicalize()`. For built-in capabilities, this is a `str`. Custom capabilities may accept other types.

## Output Types

Types you read **from** `paxman.canonicalize()` and `paxman.replay()`.

### `ExecutionArtifact`

The immutable result. Eight fields plus one method.

| Field | Type | Description |
|---|---|---|
| `status` | `Status` | One of the five outcomes. |
| `value` | `str \| None` | The canonical form, or `None` for non-success statuses. |
| `evidence` | `tuple[Evidence, ...]` | Ordered list of rules that fired, with citations. |
| `contract` | (contract-like) | The contract the artifact was produced with. |
| `version_stamp` | `VersionStamp` | The four-component version stamp. |
| `authorities` | `tuple[Authority, ...]` | The concrete authority editions that produced this artifact. Sorted by name. |
| `candidates` | `tuple[str, ...] \| None` | When status is `AMBIGUOUS`, the sorted tuple of surviving canonical forms. `None` for non-`AMBIGUOUS` outcomes. |
| `replay_hash` | `str` | SHA-256 of `canonical_bytes()`, computed automatically. |

| Method | Signature | Description |
|---|---|---|
| `canonical_bytes` | `() -> bytes` | Deterministic byte serialization. JSON, sort_keys=True, no insignificant whitespace, ensure_ascii=False. Used to compute the `replay_hash`. |

The artifact is `@attrs.frozen`; no field may be reassigned after construction. The only way to "modify" an artifact is to produce a new one via a new `canonicalize()` call.

### `Status`

The five outcomes:

| Value | When |
|---|---|
| `CANONICALIZED` | The capability produced a canonical form. `value` is set. |
| `INVALID` | The input cannot satisfy the contract. `value` is `None`. |
| `MISSING` | The contract requires information the input does not provide. `value` is `None`. |
| `AMBIGUOUS` | More than one capability claimed the pair. `value` is `None`. |
| `UNSUPPORTED` | No capability claimed the pair, or the contract kind is not recognized. `value` is `None`. |

These are outcomes, not exceptions. Every `paxman.canonicalize()` call returns an artifact; the artifact's `status` says what happened. See [Status and evidence](../concepts/status-and-evidence.md) for the conceptual background.

### `Evidence`

One entry on the artifact's evidence list. Every rule that contributes to a canonical form or a rejection decision must carry a non-empty `authority` citation (MANDATE Law 14). The only entries allowed to have `authority=None` are the named dispatch invariants (`not_an_email_contract`, `not_a_string_value`, etc.), which describe a routing failure rather than a canonical-form rule.

```python
@attrs.frozen
class Evidence:
    rule: str
    detail: str = ""
    authority: Authority | None = None
```

| Field | Type | Description |
|---|---|---|
| `rule` | `str` | Machine-readable rule name (e.g. `stripped_whitespace`, `lowercased_domain`, `grammar_rejected`). |
| `detail` | `str` | Human-readable detail. May be empty. |
| `authority` | `Authority \| None` | Structured citation to an authoritative spec, bundled data-set, documented platform behavior, or Paxman policy. `None` only for the allow-listed dispatch invariants. |

The `provenance` string field was deprecated and replaced by the structured `authority` field (mandate Law 14). Accessing `evidence.provenance` raises `AttributeError` with guidance.

### `VersionStamp`

The four-component version recorded on every artifact. Replay verifies all four.

| Field | Type | Description |
|---|---|---|
| `paxman_version` | `str` | The Paxman version (e.g. `"0.0.0.dev0"`). |
| `contract_version` | `int` | The contract schema version. |
| `capabilities_hash` | `str` | SHA-256 of the sorted registered capability names. |
| `configuration_version` | `str` | Currently `"0"`. Reserved for future configuration. |

## Extension Types

Types you use when writing a custom capability.

### `Capability` (Protocol)

The structural protocol a custom capability must satisfy.

| Member | Type | Description |
|---|---|---|
| `name` | `str` | Unique identifier. Appears in the artifact's `VersionStamp` and in evidence. |
| `can_handle` | `(contract, value) -> bool` | Deterministic predicate: "Can I canonicalize this pair?" |
| `supported_output_formats` | `frozenset[str]` | The output formats this capability can produce. |
| `canonicalize` | `(value, contract, engine) -> CapabilityResult` | Pure transformation. Returns the canonical value and evidence. |

`@runtime_checkable` allows the registry to validate duck-typing at register time.

### `CapabilityResult`

The return value of a capability's `canonicalize()` method.

| Field | Type | Description |
|---|---|---|
| `status` | `Status` | The outcome. |
| `value` | `str \| None` | The canonical value. Required when `status is Status.CANONICALIZED`; otherwise `None`. |
| `evidence` | `tuple[Evidence, ...]` | Ordered list of rules that fired. Every entry's `authority` is non-`None` except the named dispatch invariants. |
| `candidates` | `tuple[str, ...] \| None` | When status is `AMBIGUOUS`, the sorted tuple of surviving canonical forms. `None` for non-`AMBIGUOUS` outcomes. |

### `CapabilityRegistry`

The default registry used by `paxman.canonicalize()`. You can also instantiate it directly for custom workflows. **The registry is mutable until you call `freeze()` on it.** `register()` and `load_builtins()` raise `FrozenRegistryError` after the freeze.

| Method | Signature | Description |
|---|---|---|
| `register` | `(capability: Capability) -> None` | Add a capability. Raises on duplicate name or non-Capability object. |
| `freeze` | `() -> None` | Make the registry immutable. Idempotent. |
| `load_builtins` | `(builtins: list[Capability]) -> None` | Register built-ins whose names are not already present. |
| `resolve_all` | `(contract, value) -> list[Capability]` | Return the set of capabilities that claim the pair, sorted by name. |
| `capabilities_hash` | `() -> str` | SHA-256 of the sorted registered capability names. |
| `is_frozen` | `bool` (property) | Whether the registry is frozen. |

`load_builtins` skips capabilities whose names are already registered (your registration wins; the built-in is skipped).

## Where to Go Next

- [API reference](api.md) -- the public functions and full error hierarchy.
- [Contracts reference](contracts.md) -- the contract vocabulary in detail.
- [Capability protocol reference](capability-protocol.md) -- the SPI for custom capabilities.

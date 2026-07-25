# API Reference

This section is the API reference. It documents every public symbol in `paxman`, with signatures, parameters, return types, and the exceptions that may be raised.

## Top-Level Functions

The four public verbs you call directly. All are imported from `paxman`.

### `canonicalize`

```python
def canonicalize(input_data: object, contract: object) -> ExecutionArtifact
```

Canonicalize `input_data` against `contract`. Returns an `ExecutionArtifact`. Never raises for an outcome representable as a `Status` value.

| Parameter | Type | Description |
|---|---|---|
| `input_data` | `object` | The value to canonicalize. For the email capability, this is a `str`. |
| `contract` | `object` | The contract that declares the canonical form. Usually an `Email(...)` value object. |

**Returns:** `ExecutionArtifact` — the immutable result. The artifact's `status` is one of the five `Status` values. If `status is Status.CANONICALIZED`, the artifact's `value` holds the canonical form.

**Raises:** Nothing for normal use. The function never raises `ContractError`, `VersionMismatchError`, etc. — those are raised by `parse_contract()` (for malformed contracts) or `replay()` (for version mismatch), not by `canonicalize()`.

**Example:**

```python
import paxman
from paxman import Email, Status

result = paxman.canonicalize("User@Example.com", Email())
assert result.status is Status.CANONICALIZED
assert result.value == "user@example.com"
```

See [How-to: Canonicalize a value](../how-to/canonicalize-a-value.md).

### `canonicalize_with`

```python
def canonicalize_with(input_data: object, contract: object, engine: Engine) -> ExecutionArtifact
```

Same as `canonicalize` but binds an explicit `Engine` for authority-edition control. For replay-deterministic testing or audit trails. The zero-config `canonicalize()` uses `Engine.default()` internally.

| Parameter | Type | Description |
|---|---|---|
| `input_data` | `object` | The value to canonicalize. |
| `contract` | `object` | The contract that declares the canonical form. |
| `engine` | `Engine` | The engine binding specific authority editions. |

**Returns:** `ExecutionArtifact` — same shape as `canonicalize()`.

**Raises:** Nothing for normal use. Same semantics as `canonicalize()`.

**Example:**

```python
import paxman
from paxman import Country, Edition, Engine, canonicalize_with

eng = Engine.with_authorities({"ISO 3166-1": Edition("2024")})
result = canonicalize_with("malaysia", Country(allow_name=True), eng)
assert result.status.value == "canonicalized"
```

### `replay`

```python
def replay(artifact: ExecutionArtifact, contract: object) -> ExecutionArtifact
```

Rehydrate an artifact from its stored form. Verifies the artifact's `VersionStamp` matches the current environment and that the `replay_hash` matches the artifact's content. Does not re-execute the capability.

| Parameter | Type | Description |
|---|---|---|
| `artifact` | `ExecutionArtifact` | The artifact to rehydrate. |
| `contract` | `object` | The contract the artifact was produced with. Must match the artifact's stored contract for replay to succeed. |

**Returns:** `ExecutionArtifact` — the same frozen artifact instance, byte-equal to the input.

**Raises:**

- `VersionMismatchError` — one of the `VersionStamp` fields does not match the current environment.
- `CanonicalizationError` — the `replay_hash` does not match the artifact's content (tampering detected).

**Example:**

```python
import paxman
from paxman import Email

result = paxman.canonicalize("User@Example.com", Email())
rehydrated = paxman.replay(result, Email())
assert rehydrated == result
```

See [How-to: Replay for verification](../how-to/replay-for-verification.md).

### `register_capability`

```python
def register_capability(capability: Capability) -> None
```

Register a capability with the default registry. Must be called **before** the first `paxman.canonicalize()` call. After the first call, the registry is frozen and further calls raise `FrozenRegistryError`.

| Parameter | Type | Description |
|---|---|---|
| `capability` | `Capability` | An object that implements the `Capability` protocol: a `name` attribute, a `can_handle(contract, value) -> bool` method, and a `canonicalize(value, contract) -> CapabilityResult` method. |

**Returns:** `None`.

**Raises:**

- `FrozenRegistryError` — the registry is already frozen (a `canonicalize()` call has happened).
- `ConfigurationError` — the capability is structurally invalid (missing `name`, missing methods, or a duplicate name registration).

**Example:**

```python
import paxman
from paxman import register_capability

register_capability(YourCapability())
```

See [How-to: Write a compliant capability](../how-to/write-a-compliant-capability.md).

## The Dict DSL Helper

`parse_contract()` is a *contract helper*, not one of the four public verbs (`canonicalize`, `canonicalize_with`, `replay`, `register_capability`). It is a convenience for turning the Dict DSL into a contract value object. It is re-exported from `paxman` and is used by callers that store contracts as JSON and reconstruct them at load time.

### `parse_contract`

```python
def parse_contract(spec: Any) -> Contract
```

Parse a Dict DSL contract into a `Contract` value object. Also accepts an already-parsed contract value object and returns it unchanged.

| Parameter | Type | Description |
|---|---|---|
| `spec` | `Any` | A dict with a `kind` discriminator, or an already-parsed contract. |

**Returns:** `Contract` (the union `CanonicalEmailContract | CanonicalUUIDContract | CanonicalDateContract | CanonicalPhoneContract | CanonicalURLContract | CanonicalBooleanContract | CanonicalIPContract | CanonicalMoneyContract | CanonicalGeolocationContract | CanonicalCountryContract`).

**Raises:** `ContractError` if the spec is malformed (unknown `kind`, missing `kind`, wrong-type field, a `provider_aliases` value outside the closed set, or an invalid uuid version value for a `canonical_uuid` contract).

**Example:**

```python
import paxman

contract = paxman.parse_contract({
    "kind": "canonical_email",
    "lowercase": True,
    "strict": False,
})
```

## Core Types

The types the public surface uses for inputs, outputs, and configuration.

### `Email`

```python
def Email(
    *,
    strict: bool = False,
    provider_aliases: Literal["none", "gmail"] = "none",
    lowercase: bool = True,
    strip_whitespace: bool = True,
    output_format: Literal["email"] = "email",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalEmailContract
```

Domain-type sugar for declaring an email contract. Returns a `CanonicalEmailContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `strict` | `bool` | `False` | Reject inputs with embedded whitespace or non-ASCII characters. |
| `provider_aliases` | `"none"` or `"gmail"` | `"none"` | Apply a provider's documented alias rules. Only `"gmail"` is supported in v2.0.0. |
| `lowercase` | `bool` | `True` | Lowercase the local part and domain. |
| `strip_whitespace` | `bool` | `True` | Strip leading/trailing ASCII whitespace. |
| `output_format` | `"email"` | `"email"` | The canonical output form. Only `"email"` is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalEmailContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [Email capability spec](../capabilities/email/index.md).

### `UUID`

```python
def UUID(
    *,
    version: Literal["any", "1", "3", "4", "5", "7"] = "any",
    output_format: Literal["hex"] = "hex",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalUUIDContract
```

Domain-type sugar for declaring a UUID contract. Returns a `CanonicalUUIDContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `version` | `"any"`, `"1"`, `"3"`, `"4"`, `"5"`, `"7"` | `"any"` | Which UUID version to accept. Under `version="any"` the capability validates only RFC 4122 §3 form. A specific value (e.g. `"4"`) adds an RFC 4122 §4.1.3 check. |
| `output_format` | `"hex"` | `"hex"` | The canonical output form. Only `"hex"` is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalUUIDContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [UUID capability spec](../capabilities/uuid/index.md).

### `Phone`

```python
def Phone(
    *,
    country: str = "US",
    output_format: Literal["e164"] = "e164",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalPhoneContract
```

Domain-type sugar for declaring a phone contract. Returns a `CanonicalPhoneContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `country` | `str` | `"US"` | ISO 3166-1 alpha-2 country code used to expand national-format numbers. |
| `output_format` | `"e164"` | `"e164"` | The canonical output form. Only `"e164"` is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalPhoneContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [Phone capability spec](../capabilities/phone/index.md).

### `URL`

```python
def URL(
    *,
    scheme_allow: tuple[str, ...] | None = None,
    strip_userinfo: bool = False,
    strip_fragment: bool = True,
    sort_query: bool = False,
    whatwg: bool = False,
    output_format: Literal["normalized"] = "normalized",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalURLContract
```

Domain-type sugar for declaring a URL contract. Returns a `CanonicalURLContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `scheme_allow` | `tuple[str, ...] \| None` | `None` | Tuple of allowed schemes. `None` means accept any scheme. |
| `strip_userinfo` | `bool` | `False` | Strip `user:info@` from the authority. |
| `strip_fragment` | `bool` | `True` | Strip the `#fragment` component. |
| `sort_query` | `bool` | `False` | Sort query parameters lexicographically. |
| `whatwg` | `bool` | `False` | Use WHATWG URL parsing rules instead of RFC 3986. |
| `output_format` | `"normalized"` | `"normalized"` | The canonical output form. Only `"normalized"` is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalURLContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [URL capability spec](../capabilities/url/index.md).

### `Date`

```python
def Date(
    *,
    locale: Literal["ISO", "US", "EU"] = "ISO",
    language: str = "en",
    two_digit_year: Literal["reject", "require_four_digit_year"] | str | None = None,
    output_format: Literal["iso", "compact"] = "iso",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalDateContract
```

Domain-type sugar for declaring a date contract. Returns a `CanonicalDateContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `locale` | `"ISO"`, `"US"`, `"EU"` | `"ISO"` | Numeric slash ordering policy. `"ISO"` enumerates both MM/DD and DD/MM (ambiguous forms report `AMBIGUOUS`). |
| `language` | `str` | `"en"` | Month/weekday-name reading table. |
| `two_digit_year` | `str \| None` | `None` | Century policy. `None` means Don't Guess -> AMBIGUOUS for 2-digit years. `"reject"` rejects them. A `"pivot:YYYY"` string expands YY via a pivot year. |
| `output_format` | `"iso"` or `"compact"` | `"iso"` | The canonical output form. `"iso"` for `YYYY-MM-DD`, `"compact"` for `YYYYMMDD`. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalDateContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [Date capability spec](../capabilities/date/index.md).

### `Boolean`

```python
def Boolean(
    *,
    accept_numeric: bool = True,
    accept_words: bool = True,
    case_sensitive: bool = False,
    output_format: Literal["truefalse"] = "truefalse",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalBooleanContract
```

Domain-type sugar for declaring a boolean contract. Returns a `CanonicalBooleanContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `accept_numeric` | `bool` | `True` | Enable `"1"` -> `true`, `"0"` -> `false`. |
| `accept_words` | `bool` | `True` | Enable yes/no, y/n, t/f, on/off, enabled/disabled. |
| `case_sensitive` | `bool` | `False` | Match tokens case-insensitively when `False`. |
| `output_format` | `"truefalse"` | `"truefalse"` | The canonical output form. Only `"truefalse"` is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalBooleanContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [Boolean capability spec](../capabilities/boolean/index.md).

### `IP`

```python
def IP(
    *,
    allow_ipv4: bool = True,
    allow_ipv6: bool = True,
    preserve_zone_id: bool = True,
    output_format: Literal["normalized"] = "normalized",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalIPContract
```

Domain-type sugar for declaring an IP contract. Returns a `CanonicalIPContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allow_ipv4` | `bool` | `True` | Accept IPv4 inputs. |
| `allow_ipv6` | `bool` | `True` | Accept IPv6 inputs. |
| `preserve_zone_id` | `bool` | `True` | Keep the `%zone` scope identifier on link-local addresses (RFC 4007), lowercased. |
| `output_format` | `"normalized"` | `"normalized"` | The canonical output form. Only `"normalized"` is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalIPContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [IP capability spec](../capabilities/ip/index.md).

### `Money`

```python
def Money(
    *,
    currency: str,
    allow_symbol: bool = True,
    allow_code: bool = True,
    strip_spaces: bool = True,
    output_format: Literal["iso4217"] = "iso4217",
    authority_override: Any | None = None,
) -> CanonicalMoneyContract
```

Domain-type sugar for declaring a money contract. Returns a `CanonicalMoneyContract` value object. Keyword-only arguments. `currency` is required with no default.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `currency` | `str` | *(required)* | ISO 4217 alpha code. No default: Paxman never guesses the currency. |
| `allow_symbol` | `bool` | `True` | Accept currency symbols in input, validating them against `currency`. |
| `allow_code` | `bool` | `True` | Accept ISO codes (e.g. `"MYR"`) in input, validating against `currency`. |
| `strip_spaces` | `bool` | `True` | Trim ASCII whitespace around the amount. |
| `output_format` | `"iso4217"` | `"iso4217"` | The canonical output form. Only `"iso4217"` is supported. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalMoneyContract` — a frozen value object with the same fields.

**Raises:** `ContractError` if `currency` is missing, not a 3-letter string, or not a recognized ISO 4217 code.

See [Concepts: Contracts](../concepts/contracts.md) and the [Money capability spec](../capabilities/money/index.md).

### `Geolocation`

```python
def Geolocation(
    *,
    datum: str = "WGS84",
    coordinate_order: str = "lat_lon",
    require_hemisphere: bool = True,
    output_format: Literal["decimal"] = "decimal",
    precision: int = 6,
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalGeolocationContract
```

Domain-type sugar for declaring a geolocation contract. Returns a `CanonicalGeolocationContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `datum` | `str` | `"WGS84"` | Geodetic datum of the coordinates. Only `"WGS84"` is supported in v1. |
| `coordinate_order` | `str` | `"lat_lon"` | Order of latitude/longitude in the INPUT. One of `"lat_lon"` or `"lon_lat"`. The canonical output is always `"latitude,longitude"`. |
| `require_hemisphere` | `bool` | `True` | Require an explicit hemisphere sign (or N/S/E/W) on each coordinate so the canonical form is unambiguous. |
| `output_format` | `"decimal"` | `"decimal"` | Canonical output format. Only `"decimal"` (decimal degrees) is supported in v1. |
| `precision` | `int` | `6` | Number of decimal places in the canonical output. Must be an int in 0..12. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalGeolocationContract` — a frozen value object with the same fields.

**Raises:** `ContractError` if `datum`, `coordinate_order`, or `output_format` is not a recognized value, or if `precision` is not an int in 0..12, or if a flag argument is not a bool.

See [Concepts: Contracts](../concepts/contracts.md) and the [Geolocation capability spec](../capabilities/geolocation/index.md).

### `Country`

```python
def Country(
    *,
    allow_alpha3: bool = True,
    allow_name: bool = True,
    allow_synonym: bool = True,
    allow_numeric: bool = True,
    localized_names: bool = False,
    historical_names: bool = False,
    extra_synonyms: Mapping[str, str] | None = None,
    output_format: Literal["alpha2", "alpha3", "numeric"] = "alpha2",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalCountryContract
```

Domain-type sugar for declaring a country contract. Returns a `CanonicalCountryContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allow_alpha3` | `bool` | `True` | Accept ISO 3166-1 alpha-3 codes. |
| `allow_name` | `bool` | `True` | Accept canonical country names. |
| `allow_synonym` | `bool` | `True` | Accept bundled aliases (USA, UK, ...). |
| `allow_numeric` | `bool` | `True` | Accept ISO 3166-1 numeric (M49) codes. |
| `localized_names` | `bool` | `False` | Accept Unicode CLDR localized names (multilingual). Default False (data footprint; opt-in). |
| `historical_names` | `bool` | `False` | Accept deprecated/historical names (Burma->Myanmar). Default False (keeps default surface stable). |
| `extra_synonyms` | `Mapping[str, str] \| None` | `None` | Caller-supplied `{alias: alpha2}` map (replayable). Default None (empty). |
| `output_format` | `"alpha2"`, `"alpha3"`, `"numeric"` | `"alpha2"` | The canonical output form. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to include for recognition. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar selectors to exclude from recognition. |
| `authority_override` | `Any \| None` | `None` | Pin one authority edition for this call (testing escape hatch). |

**Returns:** `CanonicalCountryContract` — a frozen value object with the same fields.

**Raises:** `ContractError` if a flag argument is not a bool, if an `extra_synonyms` target is not a valid alpha-2 code, or if `output_format` is not one of the supported formats.

See [Concepts: Contracts](../concepts/contracts.md) and the [Country capability spec](../capabilities/country/index.md).

### `CanonicalEmailContract`

```python
@attrs.frozen
class CanonicalEmailContract:
    lowercase: bool = True
    strip_whitespace: bool = True
    provider_aliases: Literal["none", "gmail"] = "none"
    strict: bool = False
    output_format: Literal["email"] = "email"
    kind: str = "canonical_email"
    version: int = 1
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing an email canonicalization policy. Has a method `as_dict() -> dict` that round-trips through `parse_contract()`.

### `CanonicalUUIDContract`

```python
@attrs.frozen
class CanonicalUUIDContract:
    version: Literal["any", "1", "3", "4", "5", "7"] = "any"
    output_format: Literal["hex"] = "hex"
    kind: str = "canonical_uuid"
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing a UUID canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalPhoneContract`

```python
@attrs.frozen
class CanonicalPhoneContract:
    country: str = "US"
    kind: str = "canonical_phone"
    version: int = 1
    version_field: int = 1
    output_format: Literal["e164"] = "e164"
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing a phone canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalURLContract`

```python
@attrs.frozen
class CanonicalURLContract:
    scheme_allow: tuple[str, ...] | None = None
    strip_userinfo: bool = False
    strip_fragment: bool = True
    sort_query: bool = False
    whatwg: bool = False
    kind: str = "canonical_url"
    version: int = 1
    version_field: int = 1
    output_format: Literal["normalized"] = "normalized"
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing a URL canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalDateContract`

```python
@attrs.frozen
class CanonicalDateContract:
    locale: Literal["ISO", "US", "EU"] = "ISO"
    language: str = "en"
    two_digit_year: Literal["reject", "require_four_digit_year"] | str | None = None
    output_format: Literal["iso", "compact"] = "iso"
    kind: str = "canonical_date"
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing a date canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalBooleanContract`

```python
@attrs.frozen
class CanonicalBooleanContract:
    accept_numeric: bool = True
    accept_words: bool = True
    case_sensitive: bool = False
    output_format: Literal["truefalse"] = "truefalse"
    kind: str = "canonical_boolean"
    version: int = 1
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing a boolean canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalIPContract`

```python
@attrs.frozen
class CanonicalIPContract:
    allow_ipv4: bool = True
    allow_ipv6: bool = True
    preserve_zone_id: bool = True
    output_format: Literal["normalized"] = "normalized"
    kind: str = "canonical_ip"
    version: int = 1
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing an IP canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalMoneyContract`

```python
@attrs.frozen
class CanonicalMoneyContract:
    currency: str  # required, no default
    allow_symbol: bool = True
    allow_code: bool = True
    strip_spaces: bool = True
    output_format: Literal["iso4217"] = "iso4217"
    kind: str = "canonical_money"
    version: int = 1
    version_field: int = 1
    authority_override: Any = None
```

The frozen value object representing a money canonicalization policy. `currency` is required (no default). Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalGeolocationContract`

```python
@attrs.frozen
class CanonicalGeolocationContract:
    datum: str = "WGS84"
    coordinate_order: str = "lat_lon"
    require_hemisphere: bool = True
    output_format: Literal["decimal"] = "decimal"
    precision: int = 6
    kind: str = "canonical_geolocation"
    version: int = 1
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing a geolocation canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `CanonicalCountryContract`

```python
@attrs.frozen
class CanonicalCountryContract:
    allow_alpha3: bool = True
    allow_name: bool = True
    allow_synonym: bool = True
    allow_numeric: bool = True
    localized_names: bool = False
    historical_names: bool = False
    extra_synonyms: Mapping[str, str] = {}
    output_format: Literal["alpha2", "alpha3", "numeric"] = "alpha2"
    kind: str = "canonical_country"
    version: int = 1
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

The frozen value object representing a country canonicalization policy. `extra_synonyms` is stored as a `MappingProxyType` (immutable). Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `Contract`

```python
Contract = (CanonicalEmailContract | CanonicalUUIDContract | CanonicalDateContract |
            CanonicalPhoneContract | CanonicalURLContract | CanonicalBooleanContract |
            CanonicalIPContract | CanonicalMoneyContract | CanonicalGeolocationContract |
            CanonicalCountryContract)
```

The union of the frozen contract types, covering all ten built-in canonical kinds. `parse_contract()` returns one of these types.

### `Capability`

```python
@runtime_checkable
class Capability(Protocol):
    name: str
    def can_handle(self, contract: Contract, value: Any) -> bool: ...
    def canonicalize(self, value: Any, contract: Contract) -> CapabilityResult: ...
```

The structural protocol a custom capability must satisfy. `@runtime_checkable` allows duck-typing validation at register time.

### `CapabilityRegistry`

```python
class CapabilityRegistry:
    def __init__(self) -> None: ...
    def register(self, capability: Capability) -> None: ...
    def freeze(self) -> None: ...
    def load_builtins(self, builtins: list[Capability]) -> None: ...
    def resolve_all(self, contract: Contract, value: object) -> list[Capability]: ...
    def capabilities_hash(self) -> str: ...
    @property
    def is_frozen(self) -> bool: ...
```

The resolver / dispatcher. Holds registered capabilities and answers `resolve_all(contract, value)` with the set of capabilities that explicitly declare they canonicalize the pair.

The default, module-level registry used by `paxman.canonicalize()` is the singleton at `paxman._orchestrator_runtime.default_registry`. You usually do not interact with it directly; `register_capability()` does it for you.

### `CapabilityResult`

```python
@attrs.frozen
class CapabilityResult:
    status: Status
    value: str | None = None
    evidence: tuple[Evidence, ...] = ()
    candidates: tuple[str, ...] | None = None
```

The return value of a capability's `canonicalize()` method. `value` is required only when `status` is `CANONICALIZED`. When `status` is `AMBIGUOUS`, `candidates` may hold the sorted tuple of every surviving canonical form, exposing the ambiguity instead of guessing.

### `ExecutionArtifact`

```python
@attrs.frozen
class ExecutionArtifact:
    status: Status
    value: str | None
    evidence: tuple[Evidence, ...]
    contract: _ContractLike
    version_stamp: VersionStamp
    authorities: tuple[Authority, ...] = ()
    candidates: tuple[str, ...] | None = None
    replay_hash: str  # computed in __attrs_post_init__

    def canonical_bytes(self) -> bytes: ...
```

The immutable result of `paxman.canonicalize()`. All fields are set at construction. The `replay_hash` is computed from `canonical_bytes()` automatically.

| Field | Type | Description |
|---|---|---|
| `status` | `Status` | One of the five outcomes. |
| `value` | `str \| None` | The canonical form. `None` unless `status is Status.CANONICALIZED`. |
| `evidence` | `tuple[Evidence, ...]` | Ordered list of every rule that fired, with detail and authority citation. |
| `contract` | (contract-like) | The contract the artifact was produced with. |
| `version_stamp` | `VersionStamp` | The four-component version that makes replay deterministic. |
| `authorities` | `tuple[Authority, ...]` | The concrete authority editions that produced this artifact, sorted by name. |
| `candidates` | `tuple[str, ...] \| None` | When `AMBIGUOUS`, the surviving canonical forms. `None` otherwise. |
| `replay_hash` | `str` | SHA-256 of `canonical_bytes()`, computed automatically. |

| Method | Signature | Description |
|---|---|---|
| `canonical_bytes` | `() -> bytes` | Deterministic byte serialization. `sort_keys=True`, no insignificant whitespace, `ensure_ascii=False`. Used for the `replay_hash`. |

### `Status`

```python
class Status(enum.Enum):
    CANONICALIZED = "canonicalized"
    INVALID = "invalid"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
```

The five mutually-exclusive outcomes of a canonicalize call. See [Status and evidence](../concepts/status-and-evidence.md) for what each value means.

### `Evidence`

```python
@attrs.frozen
class Evidence:
    rule: str
    detail: str = ""
    authority: Authority | None = None
```

One entry on an artifact's evidence list. The `authority` field carries a structured `Authority` citation naming the source, edition, and kind of the rule that fired. A small set of routing/dispatch failures are allow-listed with `authority=None` because they describe a routing failure, not a canonical-form rule.

Note: the old `provenance` string property is deprecated. Accessing it raises `AttributeError` with guidance to use `authority` instead.

### `VersionStamp`

```python
@attrs.frozen
class VersionStamp:
    paxman_version: str
    contract_version: int
    capabilities_hash: str
    configuration_version: str
```

The four-component version stamp recorded on every artifact. Replay verifies all four components.

| Field | Type | Description |
|---|---|---|
| `paxman_version` | `str` | The Paxman version string (e.g. `"0.0.0.dev0"`). |
| `contract_version` | `int` | The contract schema version. |
| `capabilities_hash` | `str` | SHA-256 of the sorted registered capability names. |
| `configuration_version` | `str` | Currently `"0"`. Reserved for future configuration. |

### `ValidationResult`

```python
@attrs.frozen
class ValidationResult:
    is_valid: bool
```

The verdict of the post-capability validation step. Most users do not interact with this directly.

### `Engine`

```python
class Engine:
    @classmethod
    def default(cls) -> Engine: ...
    @classmethod
    def with_authorities(cls, bindings: dict[str, Selector]) -> Engine: ...
    @classmethod
    def from_artifact(cls, authorities: tuple[Authority, ...]) -> Engine: ...
    def authority(self, name: str) -> Authority: ...
    def override(self, name: str, selector: Selector) -> Engine: ...
    def authorities(self) -> tuple[Authority, ...]: ...
```

The immutable name-to-Authority binding that controls which concrete editions are used during canonicalization. `Engine.default()` uses active (latest) editions for every known authority. `Engine.with_authorities()` pins specific editions. `Engine.from_artifact()` reconstructs the exact editions recorded on an artifact for replay-deterministic behavior.

| Method | Description |
|---|---|
| `default()` | Class method. Binds every known authority to its active (latest) edition. |
| `with_authorities(bindings)` | Class method. Starts from `default` and applies each binding. |
| `from_artifact(authorities)` | Class method. Rebuilds from the editions recorded on an artifact. |
| `authority(name)` | Returns the concrete `Authority` bound for `name`. |
| `override(name, selector)` | Returns a new Engine with `name` re-bound to `selector`. |
| `authorities()` | Returns the bound authorities, sorted by name. |

### `Edition`

```python
@attrs.frozen
class Edition:
    edition_id: str
```

A selector that pins a concrete edition id of an authority (e.g. `"2024"` for ISO 3166-1). Used with `Engine.with_authorities()` or a contract's `authority_override` to lock a specific edition for replay-deterministic canonicalization.

### `Latest`

```python
@attrs.frozen
class Latest: ...
```

A selector that requests the active (latest) edition of an authority. This is a resolution strategy, not an edition. It is resolved once to a concrete `Authority` and never stored; the artifact records the resolved concrete edition so replay is deterministic regardless of whether a newer edition has since been published.

## Errors

The exception hierarchy. See [Errors](errors.md) for the full reference.

- `PaxmanError` — base class for all paxman exceptions.
- `CanonicalizationError(PaxmanError)` — base for runtime errors during canonicalization.
  - `AmbiguousInputError` — defensive; normally surfaced as `Status.AMBIGUOUS`, not raised.
  - `UnsupportedContractError` — defensive; orchestrator catches and maps to `Status.UNSUPPORTED`.
  - `VersionMismatchError` — raised by `paxman.replay()` on version stamp mismatch.
  - `FrozenRegistryError` — raised by `paxman.register_capability()` after the first canonicalize.
  - `ConfigurationError` — raised at register time on a structurally invalid capability.
  - `UnknownAuthorityEdition` — raised by `Engine` when an authority edition is requested that this build does not ship.
- `ContractError(PaxmanError)` — raised by `parse_contract()` on a malformed contract.

## Version

### `__version__`

```python
__version__ = "0.0.0.dev0"
```

The Paxman version string. Reported by `paxman.__version__` and recorded on every artifact's `VersionStamp.paxman_version`.

## Where to Go Next

- [Contracts reference](contracts.md) — the full contract vocabulary.
- [Capability protocol reference](capability-protocol.md) — the SPI for custom capabilities.
- [Errors reference](errors.md) — the full exception hierarchy and decision tree.

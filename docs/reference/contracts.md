# Reference: Contracts

A contract declares *what* the canonical form is. It is the source of truth in Paxman.

## The Contract Types in v2.0.0

v2.0.0 ships ten contract kinds: `canonical_email`, `canonical_uuid`, `canonical_date`, `canonical_phone`, `canonical_url`, `canonical_boolean`, `canonical_ip`, `canonical_money`, `canonical_geolocation`, and `canonical_country`. The `Contract` type alias is the union of the frozen contract types: `CanonicalEmailContract | CanonicalUUIDContract | CanonicalDateContract | CanonicalPhoneContract | CanonicalURLContract | CanonicalBooleanContract | CanonicalIPContract | CanonicalMoneyContract | CanonicalGeolocationContract | CanonicalCountryContract`.

## `CanonicalEmailContract`

The frozen value object representing an email canonicalization policy.

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

| Field | Type | Default | Description |
|---|---|---|---|
| `lowercase` | `bool` | `True` | Lowercase the local part and domain. |
| `strip_whitespace` | `bool` | `True` | Strip leading and trailing ASCII whitespace. |
| `provider_aliases` | `"none"` or `"gmail"` | `"none"` | Apply a provider's documented alias rules. Only `"gmail"` is supported in v2.0.0. |
| `strict` | `bool` | `False` | Reject inputs with embedded whitespace or non-ASCII characters. |
| `output_format` | `Literal["email"]` | `"email"` | Canonical output form. Only `"email"` is supported. |
| `kind` | `str` | `"canonical_email"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

The `kind`, `version`, and `version_field` fields are fixed. They are not part of the `Email()` factory signature.

## `CanonicalUUIDContract`

The frozen value object representing a UUID canonicalization policy.

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

| Field | Type | Default | Description |
|---|---|---|---|
| `version` | `"any"`, `"1"`, `"3"`, `"4"`, `"5"`, `"7"` | `"any"` | Which UUID version(s) to accept. Under `"any"` only RFC 4122 §3 form is validated, so any version/variant nibble in canonical form is accepted. A specific value adds an RFC 4122 §4.1.3 check that rejects other versions. |
| `output_format` | `Literal["hex"]` | `"hex"` | Canonical output form. Only `"hex"` (32 lowercase hex in 8-4-4-4-12 grouping) is supported. |
| `kind` | `str` | `"canonical_uuid"` | The contract kind discriminator. Fixed. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

## `CanonicalDateContract`

The frozen value object representing a date canonicalization policy. There is no auto-detection: the caller declares the locale, language, century policy, and output format; the capability applies them (Law 7).

```python
@attrs.frozen
class CanonicalDateContract:
    locale: Literal["ISO", "US", "EU"] = "ISO"
    language: str = "en"
    two_digit_year: TwoDigitYearPolicy | None = None
    output_format: Literal["iso", "compact"] = "iso"
    kind: str = "canonical_date"
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

| Field | Type | Default | Description |
|---|---|---|---|
| `locale` | `"ISO"`, `"US"`, `"EU"` | `"ISO"` | Numeric slash ordering policy. `"ISO"` enumerates both `MM/DD` and `DD/MM` orderings (ambiguous forms report `AMBIGUOUS`). |
| `language` | `str` | `"en"` | Month/weekday name reading language. Selects the month name table. |
| `two_digit_year` | `TwoDigitYearPolicy \| None` | `None` | Century policy for 2-digit years. `None` means enumerate all plausible centuries (Don't Guess -> AMBIGUOUS). `"reject"`, `"require_four_digit_year"`, or `"pivot:YYYY"` are the other options. |
| `output_format` | `Literal["iso", "compact"]` | `"iso"` | Canonical output format. `"iso"` produces `YYYY-MM-DD`; `"compact"` produces `YYYYMMDD`. |
| `kind` | `str` | `"canonical_date"` | The contract kind discriminator. Fixed. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

The `TwoDigitYearPolicy` type is `Literal["reject", "require_four_digit_year"] | str`. The string form accepts `"pivot:YYYY"` where `YYYY` is a 4-digit pivot year.

## `CanonicalPhoneContract`

The frozen value object representing a phone canonicalization policy.

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

| Field | Type | Default | Description |
|---|---|---|---|
| `country` | `str` | `"US"` | ISO 3166-1 alpha-2 country code used to expand national-format numbers. |
| `kind` | `str` | `"canonical_phone"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `output_format` | `Literal["e164"]` | `"e164"` | Canonical output form. Only `"e164"` (ITU-T E.164) is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

## `CanonicalURLContract`

The frozen value object representing a URL canonicalization policy.

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

| Field | Type | Default | Description |
|---|---|---|---|
| `scheme_allow` | `tuple[str, ...] \| None` | `None` | Allow-list of schemes. `None` means accept any scheme; a non-empty tuple rejects other schemes with `Status.UNSUPPORTED`. |
| `strip_userinfo` | `bool` | `False` | Elide `userinfo@` from the authority. |
| `strip_fragment` | `bool` | `True` | Drop the `#fragment` (default on). |
| `sort_query` | `bool` | `False` | Sort query parameters by key. |
| `whatwg` | `bool` | `False` | Opt into WHATWG URL Standard authority normalization (e.g. trailing-dot equivalence). |
| `kind` | `str` | `"canonical_url"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `output_format` | `Literal["normalized"]` | `"normalized"` | Canonical output form. Only `"normalized"` is supported. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

## `CanonicalBooleanContract`

The frozen value object representing a boolean canonicalization policy.

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

| Field | Type | Default | Description |
|---|---|---|---|
| `accept_numeric` | `bool` | `True` | Accept `"1"` as true and `"0"` as false. |
| `accept_words` | `bool` | `True` | Accept word forms: yes/no, y/n, t/f, on/off, enabled/disabled. |
| `case_sensitive` | `bool` | `False` | When `False`, tokens are matched case-insensitively. |
| `output_format` | `Literal["truefalse"]` | `"truefalse"` | Canonical output form. Only `"truefalse"` is supported. |
| `kind` | `str` | `"canonical_boolean"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

## `CanonicalIPContract`

The frozen value object representing an IP canonicalization policy.

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

| Field | Type | Default | Description |
|---|---|---|---|
| `allow_ipv4` | `bool` | `True` | Accept IPv4 inputs. When `False`, IPv4 inputs fall through to the grammar gate and are rejected. |
| `allow_ipv6` | `bool` | `True` | Accept IPv6 inputs. When `False`, IPv6 inputs are rejected. |
| `preserve_zone_id` | `bool` | `True` | Preserve and lowercase the RFC 4007 zone identifier (e.g. `fe80::1%eth0`). When `False`, the zone is stripped. |
| `output_format` | `Literal["normalized"]` | `"normalized"` | Canonical output form. Only `"normalized"` is supported. |
| `kind` | `str` | `"canonical_ip"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

The capability recognizes IPv4, IPv6, and IPv6-with-zone forms and delegates parse + canonical form to the standard library `ipaddress` module (RFC 4291 / RFC 5952 / RFC 4007). IPv4 leading-zero octets are normalized (e.g. `192.168.001.001` → `192.168.1.1`); the resolver reads `08`/`09` as decimal, not octal. A non-`1` `version` or `version_field` in a `parse_contract` dict raises `ContractError`.

## `CanonicalMoneyContract`

The frozen value object representing a money canonicalization policy. The `currency` field is REQUIRED with no default: Paxman never guesses the currency (mandate Law 3 — Never Guess; Law 7 — Explicit Over Clever).

```python
@attrs.frozen
class CanonicalMoneyContract:
    currency: str
    allow_symbol: bool = True
    allow_code: bool = True
    strip_spaces: bool = True
    output_format: Literal["iso4217"] = "iso4217"
    kind: str = "canonical_money"
    version: int = 1
    version_field: int = 1
    authority_override: Any = None
```

| Field | Type | Default | Description |
|---|---|---|---|
| `currency` | `str` | **(required)** | ISO 4217 alpha code (e.g. `"MYR"`, `"USD"`). No default — Paxman must never guess the currency (Law 3). Must be a recognized 3-letter code or `Money()` raises `ContractError`. |
| `allow_symbol` | `bool` | `True` | Accept currency symbols (`$`/`€`/`£`/`¥`/`RM`) in the input, validating them against `currency`. When `False`, a symbol in the input is rejected. |
| `allow_code` | `bool` | `True` | Accept an ISO code (e.g. `"MYR"`) in the input, validating it against `currency`. When `False`, a code in the input is rejected. |
| `strip_spaces` | `bool` | `True` | Trim leading/trailing ASCII whitespace around the amount. When `False`, surrounding whitespace is rejected. |
| `output_format` | `Literal["iso4217"]` | `"iso4217"` | Canonical output form. Only `"iso4217"` is supported. |
| `kind` | `str` | `"canonical_money"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

The canonical form is the single string `"<ISO4217>:<amount>"`, where `amount` is an exact `Decimal` string: literal decimal places are preserved (no rounding or quantization), thousands separators are stripped, and the decimal separator follows the currency-keyed convention (comma-decimal for EUR/DKK/NOK/SEK/CHF/BRL/RUB/TRY/PLN/HUF/CZK/RON/ILS/ISK, dot-decimal otherwise). Negatives are preserved (leading `-` or parenthesized `(...)`); scientific notation is normalized to plain decimal. Any symbol or code present in the input must match the contract `currency`, otherwise the input is rejected (Law 3 — Never Guess). The Law 14 rule manifest lives in `paxman._capabilities.money.rules`.

Note: `CanonicalMoneyContract` does not have `include_grammar` or `exclude_grammar` fields. Grammar selection is not applicable to money because the money capability uses a single, fixed grammar.

## `CanonicalGeolocationContract`

The frozen value object representing a geolocation canonicalization policy. There is no auto-detection: the caller declares the datum, coordinate order, hemisphere requirement, output format, and precision; the capability applies them (Law 7 — Explicit Over Clever).

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

| Field | Type | Default | Description |
|---|---|---|---|
| `datum` | `str` | `"WGS84"` | Geodetic datum of the coordinates. Only `"WGS84"` is supported in v2.0.0. |
| `coordinate_order` | `"lat_lon"` or `"lon_lat"` | `"lat_lon"` | Order of latitude/longitude in input and output. |
| `require_hemisphere` | `bool` | `True` | Require an explicit hemisphere sign (or N/S/E/W) on each coordinate so the canonical form is unambiguous. |
| `output_format` | `Literal["decimal"]` | `"decimal"` | Canonical output format. Only `"decimal"` (decimal degrees) is supported in v2.0.0. |
| `precision` | `int` | `6` | Number of decimal places in the canonical output. Must be an int in 0..12. |
| `kind` | `str` | `"canonical_geolocation"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

The canonical form is the single string `"<lat>,<lon>"` in decimal degrees on the WGS84 datum, quantized to `precision` decimal places (trailing zeros kept). The resolver applies `coordinate_order`, resolves hemisphere signals (letter or sign), converts DMS to decimal, validates ranges (latitude in [-90, 90], longitude in [-180, 180]), and quantizes. An unsigned axis under `require_hemisphere=True` is surfaced as `Status.AMBIGUOUS` (Law 4), never guessed. The Law 14 rule manifest lives in `paxman._capabilities.geolocation.rules`.

## `CanonicalCountryContract`

The frozen value object representing a country canonicalization policy.

```python
@attrs.frozen
class CanonicalCountryContract:
    allow_alpha3: bool = True
    allow_name: bool = True
    allow_synonym: bool = True
    allow_numeric: bool = True
    localized_names: bool = False
    historical_names: bool = False
    extra_synonyms: Mapping[str, str] = {}  # factory=dict, frozen to MappingProxyType
    output_format: Literal["alpha2", "alpha3", "numeric"] = "alpha2"
    kind: str = "canonical_country"
    version: int = 1
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()
    authority_override: Any = None
```

| Field | Type | Default | Description |
|---|---|---|---|
| `allow_alpha3` | `bool` | `True` | Accept ISO 3166-1 alpha-3 codes. |
| `allow_name` | `bool` | `True` | Accept canonical country names. |
| `allow_synonym` | `bool` | `True` | Accept bundled aliases (USA, UK, etc.). |
| `allow_numeric` | `bool` | `True` | Accept ISO 3166-1 numeric (M49) codes. |
| `localized_names` | `bool` | `False` | Accept Unicode CLDR localized names (multilingual). Default off to keep the default data footprint small. |
| `historical_names` | `bool` | `False` | Accept deprecated/historical names (e.g. Burma -> Myanmar). Default off to keep the default surface stable. |
| `extra_synonyms` | `Mapping[str, str]` | `{}` | Caller-supplied `{alias: alpha2}` map (replayable, Law 8a). Frozen to `MappingProxyType` on construction so the caller cannot mutate it post-construction. |
| `output_format` | `Literal["alpha2", "alpha3", "numeric"]` | `"alpha2"` | The canonical output form. |
| `kind` | `str` | `"canonical_country"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. Only `1` is accepted. |
| `include_grammar` | `tuple[str, ...]` | `()` | Grammar names to include. Empty means all grammars are active. |
| `exclude_grammar` | `tuple[str, ...]` | `()` | Grammar names to exclude. Empty means none are excluded. |
| `authority_override` | `Any` | `None` | Authority edition override. Excluded from `repr`, `eq`, and `hash`. |

## `Email()` — The Factory

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

Domain-type sugar for declaring an email contract. Returns a `CanonicalEmailContract`. All arguments are keyword-only.

**Example:**

```python
from paxman import Email

contract = Email(provider_aliases="gmail", strict=True)
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `UUID()` — The Factory

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

Domain-type sugar for declaring a UUID contract. Returns a `CanonicalUUIDContract`. All arguments are keyword-only.

## `Date()` — The Factory

```python
def Date(
    *,
    locale: Literal["ISO", "US", "EU"] = "ISO",
    language: str = "en",
    two_digit_year: TwoDigitYearPolicy | None = None,
    output_format: Literal["iso", "compact"] = "iso",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalDateContract
```

Domain-type sugar for declaring a date contract. Returns a `CanonicalDateContract`. All arguments are keyword-only.

The `TwoDigitYearPolicy` type is `Literal["reject", "require_four_digit_year"] | str`. The string form accepts `"pivot:YYYY"` where `YYYY` is a 4-digit pivot year. `None` (the default) means no century policy, so 2-digit years enumerate every plausible century (Don't Guess -> AMBIGUOUS).

## `Phone()` — The Factory

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

Domain-type sugar for declaring a phone contract. Returns a `CanonicalPhoneContract`. All arguments are keyword-only.

**Example:**

```python
from paxman import Phone

contract = Phone(country="GB")
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `URL()` — The Factory

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

Domain-type sugar for declaring a URL contract. Returns a `CanonicalURLContract`. All arguments are keyword-only.

**Example:**

```python
from paxman import URL

contract = URL(scheme_allow=("http", "https"), strip_fragment=False)
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `Boolean()` — The Factory

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

Domain-type sugar for declaring a boolean contract. Returns a `CanonicalBooleanContract`. All arguments are keyword-only.

## `IP()` — The Factory

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

Domain-type sugar for declaring an IP contract. Returns a `CanonicalIPContract`. All arguments are keyword-only.

**Example:**

```python
from paxman import IP

contract = IP(allow_ipv6=False)  # IPv4 only
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `Money()` — The Factory

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

Domain-type sugar for declaring a money contract. Returns a `CanonicalMoneyContract`. All arguments are keyword-only. `currency` is REQUIRED (no default) — Paxman never guesses the currency (Law 3).

Note: The `Money()` factory does not accept `include_grammar` or `exclude_grammar` arguments. The money capability uses a single, fixed grammar.

**Example:**

```python
from paxman import Money

contract = Money(currency="MYR")  # currency is mandatory
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `Geolocation()` — The Factory

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

Domain-type sugar for declaring a geolocation contract. Returns a `CanonicalGeolocationContract`. All arguments are keyword-only.

**Example:**

```python
from paxman import Geolocation

contract = Geolocation(coordinate_order="lon_lat", precision=4)
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `Country()` — The Factory

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

Domain-type sugar for declaring a country contract. Returns a `CanonicalCountryContract`. All arguments are keyword-only.

The `extra_synonyms` factory parameter accepts `None` (the default, treated as empty) or a `{alias: alpha2}` mapping. On construction, the mapping is frozen to a `MappingProxyType` so the caller cannot mutate it post-construction.

## `parse_contract()` — The Dict DSL Parser

```python
def parse_contract(spec: Any) -> Contract
```

Parse a Dict DSL contract into a `Contract` value object. Accepts either a dict, a string-form DSL expression, or an already-parsed contract value object (`CanonicalEmailContract`, `CanonicalUUIDContract`, `CanonicalDateContract`, `CanonicalPhoneContract`, `CanonicalURLContract`, `CanonicalBooleanContract`, `CanonicalIPContract`, `CanonicalMoneyContract`, `CanonicalGeolocationContract`, or `CanonicalCountryContract`).

**Example (Dict form):**

```python
import paxman

contract = paxman.parse_contract({
    "kind": "canonical_email",
    "provider_aliases": "gmail",
    "lowercase": True,
    "strip_whitespace": True,
    "strict": False,
})
```

**Example (String form):**

```python
import paxman

contract = paxman.parse_contract('Date(locale="US", output_format="compact")')
```

**Raises:** `ContractError` if the spec is malformed. `parse_contract()` runs at the call site, *before* capability dispatch, so a bad contract is a programming error caught at the call site, not a `Status` outcome on the artifact.

`parse_contract` is a no-op for an already-parsed contract value object — `CanonicalEmailContract`, `CanonicalUUIDContract`, `CanonicalDateContract`, `CanonicalPhoneContract`, `CanonicalURLContract`, `CanonicalBooleanContract`, `CanonicalIPContract`, `CanonicalMoneyContract`, `CanonicalGeolocationContract`, or `CanonicalCountryContract` (the contract is the truth; an instance is its own best representation).

## The Dict DSL

The Dict DSL is the wire form of a contract. It is a dict with a `kind` discriminator and the contract's fields.

```python
{
    "kind": "canonical_email",
    "lowercase": True,
    "strip_whitespace": True,
    "provider_aliases": "none",
    "strict": False,
    "version": 1,
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `kind` | `str` | Yes | — | Must be a supported `kind`: `canonical_email`, `canonical_uuid`, `canonical_date`, `canonical_phone`, `canonical_url`, `canonical_boolean`, `canonical_ip`, `canonical_money`, `canonical_geolocation`, or `canonical_country` in v2.0.0. Unknown kinds raise `ContractError`. |
| `lowercase` | `bool` | No | `True` | Same as `CanonicalEmailContract.lowercase`. |
| `strip_whitespace` | `bool` | No | `True` | Same as `CanonicalEmailContract.strip_whitespace`. |
| `provider_aliases` | `"none"` or `"gmail"` | No | `"none"` | Same as `CanonicalEmailContract.provider_aliases`. |
| `strict` | `bool` | No | `False` | Same as `CanonicalEmailContract.strict`. |
| `include_grammar` | `tuple[str, ...]` | No | `()` | Grammar names to include. Applicable to all contract kinds except `canonical_money`. |
| `exclude_grammar` | `tuple[str, ...]` | No | `()` | Grammar names to exclude. Applicable to all contract kinds except `canonical_money`. |
| `version` | `int` | No | `1` | Contract schema version. Only `1` is supported. |

Unknown `kind` values, missing `kind`, non-bool values for bool fields, and unknown `provider_aliases` values all raise `ContractError` at parse time.

The Dict DSL is round-trip-safe: `parse_contract(contract.as_dict()) == contract` for any valid contract value object.

### Canonical Phone

```json
{"kind": "canonical_phone", "country": "US"}
```

### Canonical Date

```json
{"kind": "canonical_date", "locale": "US", "language": "en"}
```

### Canonical Country

```json
{"kind": "canonical_country", "output_format": "alpha2", "allow_name": true}
```

## What a Contract Is Not

A contract is **not**:

- A configuration file. Contracts are values, not files. Build them in code, pass them to `canonicalize()`.
- A pipeline. A contract declares a target form, not a sequence of operations. The library's pipeline is fixed.
- A plugin configuration. A contract does not say which capability to invoke. The resolver (the registry) decides based on what capabilities declare.
- A regex. A contract is a typed value object. The input is the string; the contract is the policy.

## Field Semantics in Detail

### `lowercase`

When `True`, the capability lowercases the local part and the domain. When `False`, the input case is preserved.

- Lowercasing the **domain** is mandated by RFC 5321 §2.4 (domain is case-insensitive). This is non-controversial.
- Lowercasing the **local part** is a Paxman policy that diverges from RFC 5321 §2.4 (the local part is technically case-sensitive). The capability cites the Paxman spec/email §1.3 for this rule. A user who needs RFC-strict behavior can build a different capability with `lowercase=False` or with a different `lowercased_local_part` rule.

### `strip_whitespace`

When `True`, the capability strips **leading and trailing ASCII whitespace only**. When `False`, the input is canonicalized as-is.

The whitespace stripped is the ASCII set (` `, `\t`, `\n`, `\r`, `\f`, `\v`). Unicode whitespace (e.g. U+00A0 NO-BREAK SPACE) is *not* stripped, even when this field is `True`. Inputs that contain only Unicode whitespace fall through to the grammar gate and are rejected (or, with `strict=True`, are rejected by the strict-mode check first).

The contract does not strip embedded whitespace anywhere in the input. `strict=True` is the only way to reject an input with embedded whitespace; the default `strip_whitespace=True` leaves interior whitespace untouched.

### `provider_aliases`

Closed enum, two values:

- `"none"` — preserve the input domain. Do not apply any provider-specific alias rules.
- `"gmail"` — apply Gmail's documented alias rules:
  - The domain `googlemail.com` is normalized to `gmail.com`.
  - Dots in the local part are removed.
  - A `+tag` suffix in the local part is stripped (e.g. `john+work@gmail.com` becomes `john@gmail.com`).

The `"gmail"` value is based on Google's published help articles. The citations appear on the relevant evidence rules. See the [Email capability spec](../capabilities/email/index.md#the-rules) for the full rule table.

### `strict`

When `True`, the capability rejects inputs with:

- Embedded whitespace (space, tab, newline) anywhere in the input.
- Non-ASCII characters anywhere in the input.

The check happens *before* any rewriting. A non-strict input that would canonicalize successfully is rejected under `strict=True` because the input itself is non-conforming.

When `False` (the default), the capability accepts the input and applies the contract's rewriting rules. An input with embedded whitespace will be canonicalized (the whitespace is stripped); an input with non-ASCII characters will be canonicalized (the characters are preserved, then the grammar gate runs on the result).

### `include_grammar` and `exclude_grammar`

These fields control which grammar recognition layers are active during canonicalization. Both are `tuple[str, ...]` values listing grammar names.

- `include_grammar` is a whitelist. When non-empty, only the named grammars are active. When empty (the default), all registered grammars for the capability are active.
- `exclude_grammar` is a blacklist. Named grammars are removed from the active set. When empty (the default), no grammars are excluded.

Both fields accept a `converter` that normalizes lists and sets to tuples, so callers can pass `[...]` or `{...}` in addition to `(...)`.

These fields are not available on `CanonicalMoneyContract`, which uses a single fixed grammar.

## Where to Go Next

- [Concepts: Contracts](../concepts/contracts.md) — the conceptual background.
- [Capability protocol reference](capability-protocol.md) — the SPI for custom capabilities.
- [Email capability spec](../capabilities/email/index.md) — the full rule table for the shipped capability.

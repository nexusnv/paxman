# Reference: Contracts

A contract declares *what* the canonical form is. It is the source of truth in Paxman.

## The Contract Types in v2.0.0

v2.0.0 ships five contract kinds: `canonical_email`, `canonical_uuid`, `canonical_date`, `canonical_phone`, and `canonical_url`. Future versions may add new kinds (Money, etc.). The `Contract` type alias is the union of the frozen contract types: `CanonicalEmailContract | CanonicalUUIDContract | CanonicalDateContract | CanonicalPhoneContract | CanonicalURLContract`.

## `CanonicalEmailContract`

The frozen value object representing an email canonicalization policy.

```python
@attrs.frozen
class CanonicalEmailContract:
    lowercase: bool = True
    strip_whitespace: bool = True
    provider_aliases: Literal["none", "gmail"] = "none"
    strict: bool = False
    kind: str = "canonical_email"
    version: int = 1
```

| Field | Type | Default | Description |
|---|---|---|---|
| `lowercase` | `bool` | `True` | Lowercase the local part and domain. |
| `strip_whitespace` | `bool` | `True` | Strip leading and trailing ASCII whitespace. |
| `provider_aliases` | `"none"` or `"gmail"` | `"none"` | Apply a provider's documented alias rules. Only `"gmail"` is supported in v2.0.0. |
| `strict` | `bool` | `False` | Reject inputs with embedded whitespace or non-ASCII characters. |
| `kind` | `str` | `"canonical_email"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |

The `kind` and `version` fields are fixed. They are not part of the `Email()` factory signature.

## `Canonical UUID Contract`

The frozen value object representing a UUID canonicalization policy.

```python
@attrs.frozen
class CanonicalUUIDContract:
    version: Literal["any", "1", "3", "4", "5", "7"] = "any"
    kind: str = "canonical_uuid"
    version_field: int = 1
```

| Field | Type | Default | Description |
|---|---|---|---|
| `version` | `"any"`, `"1"`, `"3"`, `"4"`, `"5"`, `"7"` | `"any"` | Which UUID version(s) to accept. Under `"any"` only RFC 4122 §3 form is validated, so any version/variant nibble in canonical form is accepted. A specific value adds an RFC 4122 §4.1.3 check that rejects other versions. |
| `kind` | `str` | `"canonical_uuid"` | The contract kind discriminator. Fixed. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |

## `Canonical Phone Contract`

The frozen value object representing a phone canonicalization policy.

```python
@attrs.frozen
class CanonicalPhoneContract:
    country: str = "US"
    kind: str = "canonical_phone"
    version: int = 1
    version_field: int = 1
```

| Field | Type | Default | Description |
|---|---|---|---|
| `country` | `str` | `"US"` | ISO 3166-1 alpha-2 country code used to expand national-format numbers. |
| `kind` | `str` | `"canonical_phone"` | The contract kind discriminator. Fixed. |
| `version` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |
| `version_field` | `int` | `1` | The contract schema version. Recorded on the artifact's `VersionStamp.contract_version`. |

## `Canonical URL Contract`

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

## `UUID()` — The Factory

```python
def UUID(
    *,
    version: Literal["any", "1", "3", "4", "5", "7"] = "any",
) -> CanonicalUUIDContract
```

Domain-type sugar for declaring a UUID contract. Returns a `CanonicalUUIDContract`. All arguments are keyword-only.

## `Email()` — The Factory

```python
def Email(
    *,
    strict: bool = False,
    provider_aliases: Literal["none", "gmail"] = "none",
    lowercase: bool = True,
    strip_whitespace: bool = True,
) -> CanonicalEmailContract
```

Domain-type sugar for declaring an email contract. Returns a `CanonicalEmailContract`. All arguments are keyword-only.

**Example:**

```python
from paxman import Email

contract = Email(provider_aliases="gmail", strict=True)
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `Phone()` — The Factory

```python
def Phone(*, country: str = "US") -> CanonicalPhoneContract
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
    scheme_allow: tuple[str, ...] = (),
    strip_userinfo: bool = False,
    strip_fragment: bool = True,
    sort_query: bool = False,
    whatwg: bool = False,
) -> CanonicalURLContract
```

Domain-type sugar for declaring a URL contract. Returns a `CanonicalURLContract`. All arguments are keyword-only.

**Example:**

```python
from paxman import URL

contract = URL(scheme_allow=("http", "https"), strip_fragment=False)
```

The factory and the value object have the same field defaults. The factory does not introduce a new abstraction; it just provides a domain vocabulary.

## `parse_contract()` — The Dict DSL Parser

```python
def parse_contract(spec: Any) -> Contract
```

Parse a Dict DSL contract into a `Contract` value object. Accepts either a dict or an already-parsed contract value object (`CanonicalEmailContract`, `CanonicalUUIDContract`, `CanonicalDateContract`, `CanonicalPhoneContract`, or `CanonicalURLContract`).

**Example:**

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

**Raises:** `ContractError` if the spec is malformed. `parse_contract()` runs at the call site, *before* capability dispatch, so a bad contract is a programming error caught at the call site, not a `Status` outcome on the artifact.

`parse_contract` is a no-op for an already-parsed contract value object — `CanonicalEmailContract`, `CanonicalUUIDContract`, `CanonicalDateContract`, `CanonicalPhoneContract`, and `CanonicalURLContract` (the contract is the truth; an instance is its own best representation).

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
| `kind` | `str` | Yes | — | Must be a supported `kind`: `canonical_email`, `canonical_uuid`, `canonical_date`, `canonical_phone`, or `canonical_url` in v2.0.0. Unknown kinds raise `ContractError`. |
| `lowercase` | `bool` | No | `True` | Same as `CanonicalEmailContract.lowercase`. |
| `strip_whitespace` | `bool` | No | `True` | Same as `CanonicalEmailContract.strip_whitespace`. |
| `provider_aliases` | `"none"` or `"gmail"` | No | `"none"` | Same as `CanonicalEmailContract.provider_aliases`. |
| `strict` | `bool` | No | `False` | Same as `CanonicalEmailContract.strict`. |
| `version` | `int` | No | `1` | Same as `CanonicalEmailContract.version`. |

Unknown `kind` values, missing `kind`, non-bool values for bool fields, and unknown `provider_aliases` values all raise `ContractError` at parse time.

The Dict DSL is round-trip-safe: `parse_contract(contract.as_dict()) == contract` for any valid `CanonicalEmailContract`.

### Canonical Phone

```json
{"kind": "canonical_phone", "country": "US"}
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

## Where to Go Next

- [Concepts: Contracts](../concepts/contracts.md) — the conceptual background.
- [Capability protocol reference](capability-protocol.md) — the SPI for custom capabilities.
- [Email capability spec](../capabilities/email/index.md) — the full rule table for the shipped capability.

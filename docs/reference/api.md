# API Reference

This section is the API reference. It documents every public symbol in `paxman`, with signatures, parameters, return types, and the exceptions that may be raised.

## Top-Level Functions

The three public verbs you call directly. All are imported from `paxman`.

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

`parse_contract()` is a *contract helper*, not one of the three public verbs (`canonicalize`, `replay`, `register_capability`). It is a convenience for turning the Dict DSL into a `CanonicalEmailContract` value object. It is re-exported from `paxman` and is used by callers that store contracts as JSON and reconstruct them at load time.

### `parse_contract`

```python
def parse_contract(spec: Any) -> Contract
```

Parse a Dict DSL contract into a `Contract` value object. Also accepts an already-parsed `CanonicalEmailContract` and returns it unchanged.

| Parameter | Type | Description |
|---|---|---|
| `spec` | `Any` | A dict with a `kind` discriminator, or an already-parsed contract. |

**Returns:** `Contract` (currently bound to `CanonicalEmailContract`).

**Raises:** `ContractError` if the spec is malformed (unknown `kind`, missing `kind`, wrong-type field, or a `provider_aliases` value outside the closed set).

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
) -> CanonicalEmailContract
```

Domain-type sugar for declaring an email contract. Returns a `CanonicalEmailContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `strict` | `bool` | `False` | Reject inputs with embedded whitespace or non-ASCII characters. |
| `provider_aliases` | `"none"` or `"gmail"` | `"none"` | Apply a provider's documented alias rules. Only `"gmail"` is supported in v2.0.0. |
| `lowercase` | `bool` | `True` | Lowercase the local part and domain. |
| `strip_whitespace` | `bool` | `True` | Strip leading/trailing ASCII whitespace. |

**Returns:** `CanonicalEmailContract` — a frozen value object with the same fields.

See [Concepts: Contracts](../concepts/contracts.md) and the [Email capability spec](../capabilities/email/index.md).

### `UUID`

```python
def UUID(
    *,
    version: Literal["any", "1", "3", "4", "5", "7"] = "any",
) -> CanonicalUUIDContract
```

Domain-type sugar for declaring a UUID contract. Returns a `CanonicalUUIDContract` value object. Keyword-only arguments.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `version` | `"any"`, `"1"`, `"3"`, `"4"`, `"5"`, `"7"` | `"any"` | Which UUID version to accept. `"any"` accepts all five. A specific value rejects other versions with `Status.INVALID`. |

**Returns:** `CanonicalUUIDContract` — a frozen value object with the same field.

See [Concepts: Contracts](../concepts/contracts.md) and the [UUID capability spec](../capabilities/uuid/index.md).

### `CanonicalEmailContract`

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

The frozen value object representing an email canonicalization policy. Has a method `as_dict() -> dict` that round-trips through `parse_contract()`.

### `CanonicalUUIDContract`

```python
@attrs.frozen
class CanonicalUUIDContract:
    version: Literal["any", "1", "3", "4", "5", "7"] = "any"
    kind: str = "canonical_uuid"
    version_field: int = 1
```

The frozen value object representing a UUID canonicalization policy. Has an `as_dict()` method; `parse_contract` produces it from a dict, and the orchestrator uses `as_dict()` via the structural Protocol.

### `Contract`

```python
Contract = CanonicalEmailContract
```

Type alias. Currently bound to `CanonicalEmailContract`. Future versions may add new contract kinds.

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
```

The return value of a capability's `canonicalize()` method. `value` is required only when `status` is `CANONICALIZED`.

### `ExecutionArtifact`

```python
@attrs.frozen
class ExecutionArtifact:
    status: Status
    value: str | None
    evidence: tuple[Evidence, ...]
    contract: _ContractLike
    version_stamp: VersionStamp
    replay_hash: str  # computed in __attrs_post_init__
```

    def canonical_bytes(self) -> bytes: ...
```

The immutable result of `paxman.canonicalize()`. All fields are set at construction. The `replay_hash` is computed from `canonical_bytes()` automatically.

| Field | Type | Description |
|---|---|---|
| `status` | `Status` | One of the five outcomes. |
| `value` | `str \| None` | The canonical form. `None` unless `status is Status.CANONICALIZED`. |
| `evidence` | `tuple[Evidence, ...]` | Ordered list of every rule that fired, with detail and provenance citation. |
| `contract` | (contract-like) | The contract the artifact was produced with. |
| `version_stamp` | `VersionStamp` | The four-component version that makes replay deterministic. |
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
    provenance: str = ""
```

One entry on an artifact's evidence list. The `provenance` field cites the source of the rule. See [Why rules cite sources](../concepts/why-rules-cite-sources.md).

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

## Errors

The exception hierarchy. See [Errors](errors.md) for the full reference.

- `PaxmanError` — base class for all paxman exceptions.
- `CanonicalizationError(PaxmanError)` — base for runtime errors during canonicalization.
  - `AmbiguousInputError` — defensive; normally surfaced as `Status.AMBIGUOUS`, not raised.
  - `UnsupportedContractError` — defensive; orchestrator catches and maps to `Status.UNSUPPORTED`.
  - `VersionMismatchError` — raised by `paxman.replay()` on version stamp mismatch.
  - `FrozenRegistryError` — raised by `paxman.register_capability()` after the first canonicalize.
  - `ConfigurationError` — raised at register time on a structurally invalid capability.
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

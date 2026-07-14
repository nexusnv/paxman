# Reference: Types

The types you read from and pass to Paxman's public functions. Most are frozen value objects; the one exception is the `CapabilityRegistry`, which is mutable until you call `freeze()` on it.

## Input Types

Types you pass **to** `paxman.canonicalize()`.

### The Contract

`CanonicalEmailContract` is the only contract type in v2.0.0. You usually build one with the `Email()` factory.

| Attribute | Type | Default | Description |
|---|---|---|---|
| `lowercase` | `bool` | `True` | Lowercase the local part and domain. |
| `strip_whitespace` | `bool` | `True` | Strip leading/trailing ASCII whitespace. |
| `provider_aliases` | `Literal["none", "gmail"]` | `"none"` | Apply a provider's alias rules. |
| `strict` | `bool` | `False` | Reject inputs with embedded whitespace or non-ASCII characters. |
| `kind` | `str` | `"canonical_email"` | The contract kind. Fixed. |
| `version` | `int` | `1` | The contract schema version. |

Methods:

| Method | Signature | Description |
|---|---|---|
| `as_dict` | `() -> dict` | Return the Dict DSL form. Round-trips through `parse_contract()`. |

`Contract = CanonicalEmailContract` is a type alias. Future versions may add new contract kinds under this name.

### The Input Value

The first argument to `paxman.canonicalize()`. For the email capability, this is a `str`. Custom capabilities may accept other types.

## Output Types

Types you read **from** `paxman.canonicalize()` and `paxman.replay()`.

### `ExecutionArtifact`

The immutable result. Six fields plus one method.

| Field | Type | Description |
|---|---|---|
| `status` | `Status` | One of the five outcomes. |
| `value` | `str \| None` | The canonical form, or `None` for non-success statuses. |
| `evidence` | `tuple[Evidence, ...]` | Ordered list of rules that fired, with citations. |
| `contract` | (contract-like) | The contract the artifact was produced with. |
| `version_stamp` | `VersionStamp` | The four-component version stamp. |
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

One entry on the artifact's evidence list. **Every rule that contributes to a canonical form or a rejection decision must carry a non-empty `provenance` citation** (MANDATE Law 14). The only entries allowed to have an empty `provenance` are the two named dispatch invariants (`not_an_email_contract`, `not_a_string_value`), which describe a routing failure rather than a canonical-form rule.

| Field | Type | Description |
|---|---|---|
| `rule` | `str` | Machine-readable rule name (e.g. `stripped_whitespace`, `lowercased_domain`, `grammar_rejected`). |
| `detail` | `str` | Human-readable detail. May be empty. |
| `provenance` | `str` | Citation: RFC, documented platform behavior, or Paxman policy. Non-empty for every rule except the two named dispatch invariants. |

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
| `canonicalize` | `(value, contract) -> CapabilityResult` | Pure transformation. Returns the canonical value and evidence. |

`@runtime_checkable` allows the registry to validate duck-typing at register time.

### `CapabilityResult`

The return value of a capability's `canonicalize()` method.

| Field | Type | Description |
|---|---|---|
| `status` | `Status` | The outcome. |
| `value` | `str \| None` | The canonical value. Required when `status is Status.CANONICALIZED`; otherwise `None`. |
| `evidence` | `tuple[Evidence, ...]` | Ordered list of rules that fired. Every entry's `provenance` is non-empty except the two named dispatch invariants. |

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

- [API reference](api.md) — the public functions and full error hierarchy.
- [Contracts reference](contracts.md) — the contract vocabulary in detail.
- [Capability protocol reference](capability-protocol.md) — the SPI for custom capabilities.

# Reference: Capability Protocol

The `Capability` protocol is the only extension point of Paxman. This page documents it in detail.

## The Protocol

```python
@runtime_checkable
class Capability(Protocol):
    name: str

    def can_handle(self, contract: Contract, value: Any) -> bool: ...

    def canonicalize(self, value: Any, contract: Contract) -> CapabilityResult: ...
```

A capability is a class that satisfies this protocol. It can use inheritance (`class MyCapability(Capability): ...`) or duck-typing (just defining the three members). The `@runtime_checkable` decorator means the registry checks at register time whether the object looks like a `Capability`.

## The Three Members

### `name`

A `str` attribute. Must be unique within the registry.

- Used as the registry key.
- Appears in the artifact's evidence when a rule fires under this capability.
- Contributes to the `capabilities_hash` component of the `VersionStamp` (the hash is over the sorted list of names).

Names should be stable across capability versions. Changing a capability's name is a breaking change for any artifact produced under the old name.

### `can_handle(contract, value) -> bool`

A deterministic predicate. Returns `True` if this capability declares it can canonicalize the `(contract, value)` pair, `False` otherwise.

| Parameter | Type | Description |
|---|---|---|
| `contract` | `Contract` | The contract the caller passed to `canonicalize()`. |
| `value` | `Any` | The input value. |

**Returns:** `bool`.

**Must be:**

- **Deterministic.** Same `(contract, value)` always returns the same answer.
- **Pure.** No side effects, no network, no filesystem, no time, no randomness.
- **Fast.** It is called for every `(contract, value)` pair the orchestrator considers.

A typical implementation:

```python
def can_handle(self, contract, value):
    return isinstance(contract, MyContract) and isinstance(value, str)
```

### `canonicalize(value, contract) -> CapabilityResult`

The transformation. Given the input value and the contract, produce a `CapabilityResult` with the canonical form and evidence.

| Parameter | Type | Description |
|---|---|---|
| `value` | `Any` | The input value. |
| `contract` | `Contract` | The contract the caller passed to `canonicalize()`. |

**Returns:** `CapabilityResult` with:

- `status`: the outcome. `CANONICALIZED` for success; `INVALID`, `MISSING`, `AMBIGUOUS`, or `UNSUPPORTED` for non-success.
- `value`: the canonical form. Required when `status is Status.CANONICALIZED`; otherwise `None`.
- `evidence`: an ordered tuple of `Evidence` entries, one per rule that fired. **Every entry's `provenance` field is a non-empty citation to one of the three Law 14 sources** (authoritative spec, documented platform behavior, or declared Paxman policy). The only entries allowed to have an empty `provenance` are the two named dispatch invariants (`not_an_email_contract`, `not_a_string_value`), which describe a routing failure rather than a canonical-form rule. A rule that contributes evidence without a citation violates MANDATE Law 14 and is grounds for rejecting the capability.

**Must be:**

- **Deterministic.** Same `(value, contract)` always returns the same `CapabilityResult`.
- **Pure.** No network, no filesystem, no time, no randomness, no global mutable state.
- **Comprehensive.** Every transformation or rejection rule it applies must be reflected in the evidence list. A rule with no evidence entry is invisible to the audit trail.

**Must not:**

- Throw exceptions for outcomes representable as `Status` values. Use `Status.INVALID`, `Status.MISSING`, etc.
- Branch on "looks like X" guesses. "If the input looks like X, try Y first" is a guess; express it as a deterministic matching rule.
- Define a pipeline. A capability is one transformation. The library owns the pipeline.

A typical implementation:

```python
def canonicalize(self, value, contract):
    if not isinstance(value, str):
        return CapabilityResult(
            status=Status.INVALID,
            evidence=(Evidence(
                rule="not_a_string_value",
                provenance="",  # dispatch invariant
            ),),
        )

    canonical = transform(value, contract)
    evidence = (
        Evidence(
            rule="my_rule",
            detail="...",
            provenance="RFC 1234 §1 (some citation)",  # Law 14: never empty
        ),
    )

    return CapabilityResult(
        status=Status.CANONICALIZED,
        value=canonical,
        evidence=evidence,
    )
```

## The `CapabilityResult` Return Value

| Field | Type | Description |
|---|---|---|
| `status` | `Status` | The outcome. |
| `value` | `str \| None` | The canonical form. Required when `status is Status.CANONICALIZED`; otherwise `None`. |
| `evidence` | `tuple[Evidence, ...]` | Ordered list of rules that fired. May be empty only when the capability is the dispatch target and there are no rules to record. |

## The `Evidence` Tuple

Each `Evidence` entry has three fields. The `provenance` field is **non-empty for every rule that contributes to a canonical form or to a rejection decision** (MANDATE Law 14). The only entries allowed to have an empty `provenance` are the two named dispatch invariants (`not_an_email_contract` and `not_a_string_value`), which describe a routing failure rather than a canonical-form rule.

| Field | Type | Description |
|---|---|---|
| `rule` | `str` | Machine-readable rule name. |
| `detail` | `str` | Human-readable detail. May be empty. |
| `provenance` | `str` | Citation: an RFC section, a documented platform behavior, or a Paxman policy declaration. Required (non-empty) for every rule except the two named dispatch invariants. |

See [Why rules cite sources](../concepts/why-rules-cite-sources.md) for the full citation policy.

## The SPI Litmus Test

Before registering, ask: *can two independent implementations of this capability produce different outputs for the same `(value, contract)` pair while both correctly implementing the SPI?*

- If **yes** — the capability's dispatch is underdetermined. Do not register it.
- If **no** — the capability is a deterministic transformation. Register it.

The litmus test is necessary, not sufficient. A capability that passes the test may still be undesirable (e.g. a capability that canonicalizes `"John"` and `"JOHN"` to the same form is non-deterministic only in the trivial sense; in practice, conflating them is a real problem). The litmus test catches the structural defects; the rest is judgment.

## The Rule-to-Citation Manifest

In production code, maintain a rule-to-citation manifest the way the email capability does. **Every rule name that appears in a `rule="..."` literal must have a key in the manifest, and every key must carry a non-empty citation** (the two named dispatch invariants are the only exception; their key exists with an empty string and a comment explaining the exemption):

```python
_RULE_PROVENANCE = {
    # Dispatch invariants (the only entries with empty provenance, per MANDATE Law 14 §3.6).
    "not_a_string_value": "",
    "not_an_email_contract": "",
    # Transforming and rejecting rules — every one of these must cite a source.
    "my_rule": "RFC 1234 §1 (some citation)",
    "another_rule": "Google Help: some article (retrieved 2026-07-14)",
    "yet_another": "Paxman spec/my-capability §2.1 (declared policy)",
}

def _evidence(rule, detail=""):
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])
```

A rule with no manifest entry raises `KeyError` at the exact site where the rule is emitted. A rule with a manifest entry whose value is empty (and which is not a named dispatch invariant) is a Law 14 violation. This makes "I forgot to cite a rule" and "I cited a rule with an empty string" build-time errors, not documentation oversights.

## The CapabilityRegistry

`register_capability()` uses the default module-level registry. You can also instantiate a registry directly:

```python
from paxman import CapabilityRegistry

registry = CapabilityRegistry()
registry.register(YourCapability())
registry.freeze()
```

The default `paxman.canonicalize()` does not currently accept a custom registry as a parameter. To use a custom registry, call its methods directly (this is a v2.x future enhancement).

### Registry Methods

| Method | Signature | Description |
|---|---|---|
| `register` | `(capability: Capability) -> None` | Add a capability. Raises `FrozenRegistryError` if frozen, `ConfigurationError` if not a `Capability` or if the name is already registered. |
| `freeze` | `() -> None` | Make the registry immutable. Idempotent. |
| `load_builtins` | `(builtins: list[Capability]) -> None` | Register built-ins whose names are not already present. Skips (does not error) on duplicates. |
| `resolve_all` | `(contract, value) -> list[Capability]` | Return every capability that claims the pair, sorted by name. Empty list means `UNSUPPORTED`. List of length > 1 means `AMBIGUOUS`. |
| `capabilities_hash` | `() -> str` | SHA-256 of the sorted registered capability names. |
| `is_frozen` | `bool` (property) | Whether the registry is frozen. |

## The Registry Freeze

After the first `paxman.canonicalize()` call, the default registry is frozen. `register_capability()` calls after that raise `FrozenRegistryError`.

The freeze is what makes the capability set part of the determinism invariant. If you could keep registering capabilities mid-run, two runs of the same call could produce different artifacts because the registered set differed.

For tests and one-off scripts, instantiate a `CapabilityRegistry` directly and freeze it manually. The default registry's freeze is implicit and irreversible.

## Where to Go Next

- [Concepts: Capabilities and the SPI](../concepts/capabilities-and-spi.md) — the conceptual background.
- [How-to: Write a compliant capability](../how-to/write-a-compliant-capability.md) — a worked example.
- [Email capability spec](../capabilities/email/index.md) — the reference implementation.

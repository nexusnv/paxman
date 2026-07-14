# Stability

Paxman is small and slow to change. This page documents the stability guarantees: what is stable, what is not, and what happens to stored artifacts when the library evolves.

## Versioning

Paxman uses semantic versioning: `MAJOR.MINOR.PATCH`. The current version is `0.0.0.dev0` (a pre-release under active development).

| Version component | Meaning |
|---|---|
| `MAJOR` | Breaking changes to the public API, the artifact schema, or the contract schema. |
| `MINOR` | New capabilities, new contract kinds, new public symbols. Backwards-compatible with the previous major. |
| `PATCH` | Bug fixes that do not change the canonical form of any input. |

Pre-`1.0.0` versions may break compatibility on every release. After `1.0.0`, the rules above apply.

## The Public API

The public API is whatever is exported from `paxman.__all__`. Twenty-three symbols as of v2.0.0:

- The three user-facing verbs: `canonicalize`, `replay`, `register_capability`.
- The contract types: `Email`, `CanonicalEmailContract`, `Contract`, `parse_contract`.
- The capability types: `Capability`, `CapabilityRegistry`, `CapabilityResult`.
- The output types: `ExecutionArtifact`, `Status`, `Evidence`, `VersionStamp`, `ValidationResult`.
- The error types: `PaxmanError`, `CanonicalizationError`, `ContractError`, `UnsupportedContractError`, `VersionMismatchError`, `FrozenRegistryError`, `ConfigurationError`.
- The version: `__version__`.

These symbols are part of the public surface. Backwards-incompatible changes to their signatures, semantics, or value objects will trigger a major version bump.

Private modules (those starting with `_` — `_core`, `_capabilities`, `_contracts`, `_errors`, `_orchestrator_runtime`) are *not* public. Their contents may change in any release. Code that imports from a private module is unsupported and may break without notice.

## The Artifact Schema

An `ExecutionArtifact` has six fields: `status`, `value`, `evidence`, `contract`, `version_stamp`, `replay_hash`. The schema is stable within a major version.

If a future major version changes the schema (e.g. adds a field, removes one, changes the type of one), the change will be:

1. Documented in the release notes.
2. Reflected in a new `canonical_bytes()` format.
3. Caught by `replay()` (a v2.0.0 artifact replayed under a v3.0.0 library that has changed the schema will raise `VersionMismatchError`).

Stored artifacts from older versions remain valid for replay under the version that produced them. They are not silently reinterpreted under newer versions.

## The Contract Schema

A contract has a `kind` discriminator and a `version` field. The `version` is recorded on the artifact's `VersionStamp.contract_version`.

If a future version changes a contract's schema (e.g. adds a field, changes a default), the contract's `version` will be bumped, and the change will be visible on every new artifact. Stored artifacts from the old contract version remain valid for replay under the rules that produced them.

This is the principle: an artifact's evidence is bound to the contract version that produced it. Replay verifies the binding.

## The Capability Set

The set of registered capabilities is part of the artifact's identity, via the `capabilities_hash` component of the `VersionStamp`. Adding or removing a capability changes the hash; an artifact produced under one set cannot be replayed under a different set.

This is intentional. Two capabilities that produce the same canonical form for the same input may not produce the same evidence (different rules, different orderings, different citations). A capability-set change is a behavior change; the version stamp reflects that.

## The Paxman Version

The `paxman_version` component of the `VersionStamp` records the library version. An artifact produced under Paxman v2.0.0 cannot be replayed under a future version that has changed the canonical form of any input.

This is intentional. The library might fix a bug that changed the canonical form (e.g. a grammar gate that was too permissive in v2.0.0 and was tightened in v2.0.1). Such a fix is a behavior change and bumps the `paxman_version`. Old artifacts replayed under the new version will raise `VersionMismatchError`, and the right action is to re-canonicalize the original input.

## The Configuration Version

The `configuration_version` component of the `VersionStamp` is `"0"` in v2.0.0. Paxman has no user-visible configuration in v2.0.0; the field is reserved for future use. A future version that introduces configuration will bump this field.

## What Is Guaranteed

- **The five `Status` values are stable.** `CANONICALIZED`, `INVALID`, `MISSING`, `AMBIGUOUS`, `UNSUPPORTED` will not be added to or removed from within a major version.
- **The capability SPI is stable.** `Capability` has three members: `name`, `can_handle`, `canonicalize`. New members will only be added in a major version, with deprecation warnings before removal.
- **The exception hierarchy is stable.** New exceptions may be added (as subclasses of `PaxmanError`); existing exceptions will not be removed or have their semantics changed within a major version.
- **The artifact immutability is stable.** An `ExecutionArtifact` cannot be mutated; the `replay_hash` will always match the `canonical_bytes()` of the artifact's contents.

## What Is Not Guaranteed

- **Performance.** The library is not optimized for throughput. Future versions may be faster or slower; behavior is guaranteed, not speed.
- **Error message text.** The exact text of exception messages may change. The exception type and the field that caused the error are stable.
- **The order of capabilities in the registry's internal storage.** The registry sorts by name before returning; the internal storage order is not part of the public contract.
- **Private modules.** Code that imports from `paxman._core`, `paxman._capabilities`, or `paxman._contracts` is unsupported. Future versions may restructure these modules without notice.

## What to Do When an Artifact Cannot Be Replayed

A `VersionMismatchError` from `replay()` means one of the four version-stamp components does not match the current environment. The right action depends on which component mismatched:

- **`paxman_version` mismatch** — the library has been upgraded (or downgraded) since the artifact was produced. Re-canonicalize the original input under the new version. The new canonical form may differ from the old.
- **`contract_version` mismatch** — the contract schema has changed. Re-canonicalize the original input under the new contract.
- **`capabilities_hash` mismatch** — a capability was added or removed. Re-canonicalize the original input under the new capability set.
- **`configuration_version` mismatch** — Paxman has introduced user-visible configuration. Adjust the configuration and re-canonicalize.

In all cases, the old artifact is *not* silently reinterpreted. The library refuses to produce a result that might no longer reflect the canonical form that the old version produced.

## Where to Go Next

- [Philosophy](philosophy.md) — the design decisions behind these guarantees.
- [The three invariants](../concepts/the-three-invariants.md) — the formal determinism and replay statements.
- [How-to: Replay for verification](../how-to/replay-for-verification.md) — the practical replay workflow.

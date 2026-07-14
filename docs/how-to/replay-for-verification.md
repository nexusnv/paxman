# Replay for verification

`paxman.replay()` rehydrates an artifact from its stored form. It does not re-execute the underlying capability. Use it to verify that an artifact is intact, that the version stamp matches, and that the canonical form is the same as when the artifact was produced.

## The basic replay

```python
import paxman
from paxman import Email

original = paxman.canonicalize("User@Example.com", Email())
rehydrated = paxman.replay(original, Email())

assert rehydrated == original
```

`replay()` takes two arguments: the artifact and the contract. It returns the same artifact (a new object, byte-equal to the original) without invoking the capability. The assertion holds because `ExecutionArtifact` is a frozen value object with value equality.

## What replay verifies

Replay checks two things:

1. **The version stamp matches.** The artifact carries a `VersionStamp` with four fields: `paxman_version`, `contract_version`, `capabilities_hash`, and `configuration_version`. Replay reads the current environment's version and hash and compares. Any mismatch raises `VersionMismatchError`.
2. **The content is intact.** The artifact's `replay_hash` is a SHA-256 of its canonical byte serialization. Replay recomputes the hash from the artifact's content and compares. A mismatch raises `CanonicalizationError`.

If both checks pass, replay returns the same artifact. If either fails, replay raises.

## When replay raises

`VersionMismatchError` — one of the four `VersionStamp` fields does not match the current environment. The most common causes:

- The Paxman version changed between when the artifact was produced and now.
- The contract version changed (e.g. a new field was added to the contract schema).
- The set of registered capabilities changed (a new capability was added, or one was removed).
- The configuration version changed (no user-visible configuration in v2.0.0; this field is reserved for future use).

`CanonicalizationError` — the `replay_hash` does not match the content. This means the artifact was tampered with (a field was changed after construction, which should not be possible because the artifact is frozen, but storage corruption or an explicit attack could cause it).

In both cases, the artifact is unusable. Do not try to recover the data from a failed replay; the artifact is not trustworthy. Produce a new artifact from the original input.

## A worked verification example

```python
import attrs
import paxman
from paxman import Email, VersionMismatchError, CanonicalizationError

original = paxman.canonicalize("User@Example.com", Email())

# Replay succeeds.
rehydrated = paxman.replay(original, Email())
assert rehydrated == original
print("replay ok")

# Replace the artifact with one whose replay_hash has been zeroed.
# This simulates storage corruption.
tampered = attrs.evolve(original, replay_hash="0" * 64)
try:
    paxman.replay(tampered, Email())
except CanonicalizationError:
    print("tamper detected")
```

## Why replay is useful

Three reasons:

1. **Trust boundary.** If your system stores artifacts (in a database, on disk, in a queue), a replay check at read time catches tampering and version drift before the artifact's data propagates further.
2. **Idempotence guarantee.** Replay demonstrates the determinism invariant. If the artifact is byte-equal to its rehydrated form, the canonical form is fully determined by the recorded inputs.
3. **Audit trail.** The artifact carries the contract, the version stamp, the evidence, and the canonical value. Replay says: "this artifact, with this contract, under this environment, is intact."

## What replay is not

Replay is not a re-execution. It does not invoke the capability. It does not call out to the network, look up a database, or re-read a file. The canonical form is stored on the artifact; replay just verifies it matches the recorded hash.

This is what makes replay fast and offline. It is also what makes it trustable: there is no place for hidden state to leak in.

## Where to go next

- [Serialize an artifact](serialize-an-artifact.md) — store an artifact in JSON or a database.
- [Reference: `paxman.replay`](../reference/api.md#replay) — the full signature and exception list.
- [The three invariants](../concepts/the-three-invariants.md) — replay is one of the three pillars.

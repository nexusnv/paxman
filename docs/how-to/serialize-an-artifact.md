# Serialize an artifact

`ExecutionArtifact` is a frozen value object. You can serialize it for storage (database, disk, message queue) and reconstruct it later. This page shows the recommended pattern.

## The canonical byte form

The artifact has a `canonical_bytes()` method that returns a deterministic byte serialization:

```python
import paxman
from paxman import Email

result = paxman.canonicalize("User@Example.com", Email())
raw = result.canonical_bytes()
print(len(raw), "bytes")
```

The byte form is:

- **Deterministic.** Same artifact → same bytes. `sort_keys=True`, no insignificant whitespace, `ensure_ascii=False`.
- **Includes everything replay needs.** The contract, the version stamp, the evidence, the canonical value, and the status.
- **Hashed for `replay_hash`.** The `replay_hash` is the SHA-256 of `canonical_bytes()`. If you serialize the artifact, store the `replay_hash` separately so a future replay can compare it.

The byte form is JSON. You can decode it for inspection:

```python
import json

raw = result.canonical_bytes()
print(json.loads(raw.decode("utf-8")))
```

Output for a `CANONICALIZED` email artifact:

```json
{
  "status": "canonicalized",
  "value": "user@example.com",
  "evidence": [
    ["lowercased_local_part", "", "Paxman spec/email §1.3"],
    ["lowercased_domain", "", "RFC 5321 §2.4"]
  ],
  "contract": {
    "kind": "canonical_email",
    "lowercase": true,
    "strip_whitespace": true,
    "provider_aliases": "none",
    "strict": false,
    "version": 1
  },
  "version_stamp": {
    "paxman_version": "0.0.0.dev0",
    "contract_version": 1,
    "capabilities_hash": "...",
    "configuration_version": "0"
  }
}
```

The `replay_hash` is *not* in the byte form. It is the hash *of* the byte form.

## A full serialize / deserialize pattern

Paxman does not ship a `from_bytes()` constructor. Reconstructing an artifact from its bytes requires re-canonicalizing and verifying the hash. The intended use is: store the bytes (or just the value + version stamp + evidence), and on read, recompute the artifact and verify.

```python
import hashlib
import json
import paxman
from paxman import Email, ExecutionArtifact, VersionStamp, Status, Evidence, CanonicalEmailContract


def serialize_artifact(artifact: ExecutionArtifact) -> dict:
    """Convert an artifact to a JSON-safe dict for storage."""
    return {
        "status": artifact.status.value,
        "value": artifact.value,
        "evidence": [
            {"rule": e.rule, "detail": e.detail, "provenance": e.provenance}
            for e in artifact.evidence
        ],
        "contract": artifact.contract.as_dict(),
        "version_stamp": {
            "paxman_version": artifact.version_stamp.paxman_version,
            "contract_version": artifact.version_stamp.contract_version,
            "capabilities_hash": artifact.version_stamp.capabilities_hash,
            "configuration_version": artifact.version_stamp.configuration_version,
        },
        "replay_hash": artifact.replay_hash,
    }


def deserialize_artifact(stored: dict, contract) -> ExecutionArtifact:
    """Reconstruct an artifact from a stored dict, verifying the replay_hash.

    Raises VersionMismatchError or CanonicalizationError on tampering.
    """
    # Re-canonicalize the original input to reconstruct the artifact.
    # Note: this requires you to store the input alongside the artifact,
    # or to canonicalize from the stored value (idempotence).
    contract_obj = contract
    if isinstance(contract, dict):
        contract_obj = paxman.parse_contract(contract)

    # Replay the canonical value: idempotence says this gives back the
    # same artifact (or a byte-equal one).
    if stored["status"] != "canonicalized":
        raise ValueError(f"cannot reconstruct non-canonicalized artifact: {stored['status']}")

    artifact = paxman.canonicalize(stored["value"], contract_obj)
    if artifact.replay_hash != stored["replay_hash"]:
        raise paxman.CanonicalizationError("replay_hash mismatch — artifact was tampered with")
    return artifact
```

The pattern works because of [idempotence](../concepts/the-three-invariants.md): `canonicalize(canonical_value) == canonical_value`. If you have the canonical value, you can re-canonicalize it and get the same artifact back. If the stored `replay_hash` does not match, the artifact was tampered with.

## A simpler alternative: store only the canonical value

For many use cases, you do not need to store the entire artifact. The canonical value plus the contract plus the version stamp is enough to reconstruct and verify:

```python
import paxman
from paxman import Email, ExecutionArtifact

result = paxman.canonicalize("User@Example.com", Email())

# Store just what you need.
stored = {
    "value": result.value,
    "contract": result.contract.as_dict(),
    "replay_hash": result.replay_hash,
}

# Later: reconstruct and verify.
contract = paxman.parse_contract(stored["contract"])
rehydrated = paxman.canonicalize(stored["value"], contract)
assert rehydrated.replay_hash == stored["replay_hash"]
```

The evidence list is lost in this form. If you need the evidence for audit purposes, store it explicitly:

```python
stored = {
    "value": result.value,
    "contract": result.contract.as_dict(),
    "replay_hash": result.replay_hash,
    "evidence": [
        {"rule": e.rule, "detail": e.detail, "provenance": e.provenance}
        for e in result.evidence
    ],
}
```

## Using a database

The serialization pattern works with any key-value or document store. Store the dict as JSON, BSON, MessagePack, or whatever your stack uses. The `replay_hash` is a 64-character hex string; index on it if you need to look up artifacts by hash.

When reading back, deserialize the dict, re-canonicalize the value, and verify the hash. If verification fails, the record is corrupt — do not trust its data.

## What not to do

- **Do not pickle artifacts.** Pickling a frozen attrs dataclass works, but it bypasses the deterministic byte form. Replay verifies the hash of `canonical_bytes()`, not the pickle bytes. A pickled artifact that has been mutated after construction would not be caught by pickle's checks (pickle deserializes whatever bytes you give it).
- **Do not reconstruct the artifact by hand.** The `ExecutionArtifact` is `@attrs.frozen`; you can construct it with `attrs.evolve()` if you must, but always re-canonicalize and verify the hash. Hand-construction without verification loses the replay guarantee.
- **Do not store the artifact as Python object only.** Storing the artifact as a Python object without serializing means it never leaves memory, and a process restart loses it. Serialize for any storage that survives a process boundary.

## Where to go next

- [Replay for verification](replay-for-verification.md) — verify an artifact after reconstruction.
- [The three invariants](../concepts/the-three-invariants.md) — why idempotence makes this pattern work.
- [Reference: `ExecutionArtifact`](../reference/api.md#executionartifact) — the full schema.

# Serialize an Artifact

`ExecutionArtifact` is a frozen value object. You can serialize it for storage (database, disk, message queue) and reconstruct it later. This page shows the recommended pattern.

## The Canonical Byte Form

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

## A Full Serialize / Deserialize Pattern

Paxman does not ship a `from_bytes()` constructor. The canonical byte form (above) *is* the authoritative serialization: it contains the status, value, evidence, contract, and version stamp, and its SHA-256 equals the `replay_hash`. The recommended pattern stores those bytes plus the `replay_hash`, and verifies integrity by recomputing the hash.

```python
import json
import hashlib
import paxman
from paxman import Email, CanonicalizationError


def serialize_artifact(artifact) -> dict:
    """Store the canonical bytes plus the replay hash.

    canonical_bytes() is the authoritative serialization. Its SHA-256
    equals replay_hash, so storing both lets a reader verify the record
    was not tampered with without re-canonicalizing the input.
    """
    return {
        "canonical_bytes": artifact.canonical_bytes().decode("utf-8"),
        "replay_hash": artifact.replay_hash,
    }


def deserialize_artifact(stored: dict):
    """Verify the stored record and return a usable artifact object.

    Integrity is checked by recomputing SHA-256 of the stored canonical
    bytes and comparing to the stored replay_hash (MANDATE Law 12). This
    is a pure hash check — it does not re-canonicalize the input, so it
    detects tampering with the value, evidence, contract, or version
    stamp byte-for-byte.

    To get a usable ExecutionArtifact back, re-canonicalize the canonical
    value. The value, contract, and version stamp are deterministic and
    match the stored record exactly. The evidence list reflects
    canonicalizing the canonical value: transformation rules do not
    re-fire, so it is a subset of the original evidence. If you need the
    exact original evidence for audit, read it from the stored
    canonical_bytes() JSON directly — it is already in there.
    """
    raw = stored["canonical_bytes"].encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != stored["replay_hash"]:
        raise CanonicalizationError("artifact was tampered with")

    record = json.loads(raw)
    rehydrated = paxman.canonicalize(record["value"], paxman.parse_contract(record["contract"]))
    assert rehydrated.value == record["value"]
    assert rehydrated.contract.as_dict() == record["contract"]
    assert rehydrated.version_stamp == paxman.VersionStamp(**record["version_stamp"])
    return rehydrated
```

The pattern works because `replay_hash` is defined as `SHA-256(canonical_bytes())`. Storing both and re-checking the hash is the same check `replay()` performs (MANDATE Law 12), and it does not depend on re-canonicalizing the input — which matters because re-canonicalizing a *canonical* value does **not** reproduce the original transformation evidence, and therefore produces a different `replay_hash`.

## A Simpler Alternative: Store Only the Canonical Value

If you do not need the full record or the original evidence, store just the canonical value, the contract, and the version stamp:

```python
import paxman
from paxman import Email

result = paxman.canonicalize("User@Example.com", Email())

# Store what you need to reconstruct and verify the canonical value.
stored = {
    "value": result.value,
    "contract": result.contract.as_dict(),
    "version_stamp": {
        "paxman_version": result.version_stamp.paxman_version,
        "contract_version": result.version_stamp.contract_version,
        "capabilities_hash": result.version_stamp.capabilities_hash,
        "configuration_version": result.version_stamp.configuration_version,
    },
}

# Later: reconstruct and verify the canonical value.
contract = paxman.parse_contract(stored["contract"])
rehydrated = paxman.canonicalize(stored["value"], contract)
assert rehydrated.value == stored["value"]
assert rehydrated.contract.as_dict() == stored["contract"]
assert rehydrated.version_stamp == paxman.VersionStamp(**stored["version_stamp"])
```

This lighter form verifies the value, contract, and version stamp only. It does **not** preserve the original evidence list (re-canonicalizing a canonical value does not re-fire transformation rules), and it cannot verify the `replay_hash` — store the full canonical bytes (above) if you need evidence fidelity or replay-hash integrity.

## Using a Database

The serialization pattern works with any key-value or document store. Store the dict as JSON, BSON, MessagePack, or whatever your stack uses. The `replay_hash` is a 64-character hex string; index on it if you need to look up artifacts by hash.

When reading back, deserialize the dict, re-canonicalize the value, and verify the full record. If verification fails, the record is corrupt — do not trust its data.

## What Not to Do

- **Do not pickle artifacts.** Pickling a frozen attrs dataclass works, but it bypasses the deterministic byte form. Replay verifies the hash of `canonical_bytes()`, not the pickle bytes. A pickled artifact that has been mutated after construction would not be caught by pickle's checks (pickle deserializes whatever bytes you give it).
- **Do not reconstruct the artifact by hand.** The `ExecutionArtifact` is `@attrs.frozen`; you can construct it with `attrs.evolve()` if you must, but always re-canonicalize and verify the hash. Hand-construction without verification loses the replay guarantee.
- **Do not store the artifact as Python object only.** Storing the artifact as a Python object without serializing means it never leaves memory, and a process restart loses it. Serialize for any storage that survives a process boundary.

## Where to Go Next

- [Replay for verification](replay-for-verification.md) — verify an artifact after reconstruction.
- [The three invariants](../concepts/the-three-invariants.md) — why idempotence makes this pattern work.
- [Reference: `ExecutionArtifact`](../reference/api.md#executionartifact) — the full schema.

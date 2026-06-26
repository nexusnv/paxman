# How to Replay an Artifact

> **Status:** V1
> **Audience:** Paxman users storing and rehydrating artifacts.
> **Related docs:** [docs/concepts/replay.md](../concepts/replay.md),
> [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md) (the
> full deep dive), [GLOSSARY.md §Replay](../../GLOSSARY.md).

This guide is a **focused quick-start** for using `paxman.replay()`.
The full deep dive is in
[REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md); this
document is a 5-minute checklist.

---

## 1. The basic pattern

```python
import paxman

# 1. Run paxman.normalize(...) and capture the artifact.
artifact = paxman.normalize(
    input_data=b"raw input bytes",
    contract=my_contract,
)

# 2. Store the artifact somewhere (your choice: S3, Postgres, the
#    filesystem, …). Paxman does not store artifacts; the caller is
#    responsible for storage.

# 3. Later, with just the artifact and the SAME contract:
rehydrated = paxman.replay(artifact, contract=my_contract)
assert rehydrated == artifact  # byte-equal
```

That's the basic pattern. The rest of this document covers
serialization, version compatibility, and failure modes.

---

## 2. Serializing the artifact

The artifact is JSON-serializable. Use the stable encoder:

```python
import json
from paxman.artifact.artifact import ExecutionArtifact

# Serialize
payload = json.dumps(
    artifact.to_dict(),
    sort_keys=True,
    separators=(",", ":"),  # RFC 8785-style; deterministic
)

# Store `payload` somewhere (caller's responsibility).

# Rehydrate
artifact = ExecutionArtifact.from_dict(json.loads(payload))
rehydrated = paxman.replay(artifact, contract=my_contract)
```

`artifact.to_dict()` returns a `dict[str, object]` with all
artifact fields (including `replay_hash`). The output is stable
across Paxman versions within a major version.

### 2.1 The replay hash

`artifact.replay_hash` is a 64-character lowercase hex string
(SHA-256 over the concatenation of the artifact's hash-relevant
fields, separated by `|`). It is the artifact's tamper-detection
signature. See
[REPLAY_AND_DETERMINISM.md §2](../../REPLAY_AND_DETERMINISM.md) and
[`docs/concepts/replay.md`](../concepts/replay.md) §2.1 for the
exact list of fields that go into the hash.

### 2.2 What goes in the serialized form

The serialized artifact includes:

- `paxman_version` — the Paxman version that produced the artifact.
- `planner_version` — the planner version (`"1"`).
- `replay_version` — the replay-protocol version (`"1"`).
- `capability_versions` — the capability → version map.
- `contract_id` — the contract's stable id.
- `execution_plan` — the deterministic `ExecutionPlan` (or `null`).
- `field_results` — the per-field resolved result.
- `unresolved_fields` — fields that could not be resolved.
- `evidence` — the per-field evidence references.
- `diagnostics` — the per-field diagnostics.
- `statistics` — capability invocation counts, latency, cost.
- `replay_hash` — the deterministic signature.

The artifact does **not** include raw input, prompts, or completions
(default: `Policy.log_raw_input=False`,
`Policy.record_inference_io=False`).

---

## 3. Version compatibility

Replay is **fail-closed**: a version mismatch raises
`VersionMismatchError`. The caller must take explicit action.

| Scenario | Behavior |
|---|---|
| Same major, same minor, same patch | Replay succeeds. |
| Same major, older minor (e.g. 1.5 artifact on 1.0) | Replay succeeds if the artifact's planner version and capability versions are still supported. |
| Same major, newer minor | Replay succeeds if the artifact's planner version and capability versions are still supported in the new Paxman. |
| Different major | `VersionMismatchError`. Regenerate the artifact under the new major. |
| Missing capability | `CapabilityNotFoundError`. Register the missing capability or regenerate. |

See [REPLAY_AND_DETERMINISM.md §4](../../REPLAY_AND_DETERMINISM.md)
for the full version-compatibility matrix.

---

## 4. Failure modes

| Error | Cause | Action |
|---|---|---|
| `HashMismatchError` | The artifact was modified or corrupted. | Investigate the source of modification. The artifact is no longer trustworthy. |
| `VersionMismatchError` | The Paxman version does not support the artifact. | Upgrade Paxman or regenerate the artifact under the current version. |
| `CapabilityNotFoundError` | A pinned capability is no longer registered. | Register the missing capability or regenerate the artifact with available capabilities. |
| `InvalidContractError` | The contract supplied to replay is invalid or has been tampered. | Investigate the source of the contract. |

All four errors are subclasses of `paxman.ReplayError` (which
itself is a subclass of `PaxmanError`). Catch `ReplayError` for a
catch-all; catch a specific subclass for fine-grained handling.

```python
from paxman import replay, ReplayError, HashMismatchError

try:
    rehydrated = replay(artifact, contract=my_contract)
except HashMismatchError:
    log.error("Artifact was modified; aborting")
except ReplayError as e:
    log.error(f"Replay failed: {e}")
```

---

## 5. Replay and the contract

Replay requires the **same contract** you used originally. This is
a structural guarantee: the artifact's `normalized_data` shape is
the contract's shape, so a different contract would not match.

```python
# Original
artifact = paxman.normalize(input_data, contract=Invoice)

# Replay — MUST use the same contract
rehydrated = paxman.replay(artifact, contract=Invoice)  # OK
rehydrated = paxman.replay(artifact, contract=Quotation)  # WRONG — InvalidContractError
```

Paxman detects the mismatch in two ways:

1. The `contract_id` is part of the hash inputs (per §2.1). If the
   contract supplied to replay is not the one used originally, the
   `replay_hash` will not match → `HashMismatchError`.
2. If the supplied contract fails to adapt to a
   `CanonicalContract` (e.g. the user passes a malformed string or
   an unknown format), replay raises `InvalidContractError`.

This is intentional: the contract is part of the artifact's
identity. Storing an artifact without its contract is not
sufficient.

---

## 6. Replay and storage

The caller is responsible for **storing** the artifact. Paxman does
not store artifacts; it does not provide a storage backend; it does
not provide encryption at rest. The recommended storage pattern:

1. Serialize the artifact to a stable JSON form.
2. Store the JSON in a tamper-evident store (write-once storage,
   append-only log, signed S3 object, …).
3. Store the `replay_hash` separately if you need a fast integrity
   check before deserialization.
4. Replay the artifact by re-deserializing and calling
   `paxman.replay(...)`.

For regulated industries, see
[SECURITY.md §6](../../SECURITY.md) for the audit-trail and
tamper-evident storage guidance.

---

## 7. Replay in tests

The replay path is **fast** (no capability invocation, no I/O). Use
it in tests:

```python
def test_artifact_round_trips():
    artifact = paxman.normalize(input_data, contract=Invoice)
    rehydrated = paxman.replay(artifact, contract=Invoice)
    assert rehydrated == artifact
    assert rehydrated.replay_hash == artifact.replay_hash
```

For property tests, use `paxman.testing.artifacts()` (a Hypothesis
strategy that generates random artifacts with stable
`replay_hash`):

```python
from hypothesis import given
from paxman.testing import artifacts, contracts


@given(artifact=artifacts(), contract=contracts())
def test_replay_is_byte_equal(artifact, contract):
    rehydrated = paxman.replay(artifact, contract=contract)
    assert serialize(rehydrated) == serialize(artifact)
```

---

## 8. Common pitfalls

| Pitfall | Why it bites | Fix |
|---|---|---|
| Serializing with `json.dumps(artifact)` instead of `artifact.to_dict()` | The default encoder does not handle `MappingProxyType`, `attrs`-generated classes, or `Decimal`. | Use `artifact.to_dict()` and the stable encoder. |
| Storing the artifact without the contract | Replay will fail with `InvalidContractError`. | Store the contract alongside the artifact, or use a contract registry. |
| Modifying the JSON before storing it | The `replay_hash` will not match on replay. | Store the JSON verbatim. If you need to sign it, sign the bytes; do not modify the contents. |
| Replaying with a different Paxman major | `VersionMismatchError`. | Regenerate the artifact under the new major. |
| Replaying with a missing capability | `CapabilityNotFoundError`. | Register the missing capability or regenerate. |

---

## 9. See also

- [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md) — the
  full deep dive on replay and determinism.
- [docs/concepts/replay.md](../concepts/replay.md) — the conceptual
  overview of replay.
- [GLOSSARY.md §Replay](../../GLOSSARY.md) — vocabulary.
- [paxman.artifact.artifact](../../EXTENDING.md) — the
  `ExecutionArtifact` data model.
- [paxman.artifact.replay](../../EXTENDING.md) — the replay path.

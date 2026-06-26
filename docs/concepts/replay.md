# Replay

> **Status:** V1
> **Audience:** Paxman users storing and rehydrating artifacts; Paxman
> contributors extending the artifact subsystem.
> **Related docs:** [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md)
> (the full deep dive), [GLOSSARY.md §Replay](../../GLOSSARY.md),
> [ARCHITECTURE.md §8 Artifact Subsystem](../../ARCHITECTURE.md).

**Replay** is the act of rehydrating a previously produced
`ExecutionArtifact` to its original state **without recomputation**.
It is the **only** mechanism for rehydrating an artifact. Paxman
never recomputes from a replayed artifact.

This document explains the replay hash, the replay protocol, version
compatibility, and what determinism does and does not guarantee. For
the full deep dive, see
[REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md).

---

## 1. Definitions

- **Determinism** — a property of the **planner** and **executor**:
  given the same inputs, the planner produces the same
  `ExecutionPlan` and the executor runs the same capabilities in the
  same order.
- **Reproducibility** — a property of the **artifact**: given the
  same Paxman version, the same inputs, and the same capability
  versions, the artifact is byte-equal.
- **Replay** — the act of rehydrating a previously produced
  `ExecutionArtifact` to its original state **without recomputation**.

Determinism does **not** require capabilities to be deterministic. A
non-deterministic capability (e.g. `inference` backed by a remote
LLM) may produce different output for the same input; Paxman records
the actual output as evidence and the replay path does not
re-invoke the capability.

Reproducibility requires determinism **plus** recorded capability
outputs. Replay is the **only** mechanism for rehydrating an
artifact.

---

## 2. The replay hash

The `replay_hash` is a deterministic signature over the inputs that
uniquely identify an artifact's content.

### 2.1 What goes into the hash

The hash is computed over a canonical JSON document containing:

| Field | Source |
|---|---|
| `paxman_version` | `paxman.__version__` |
| `planner_version` | Internal constant (e.g. `"planner_v1"`). |
| `capability_versions` | Per-FieldPlan capability chain. |
| `contract_canonical_hash` | SHA-256 of the canonical contract's deterministic JSON. |
| `input_fingerprint` | SHA-256 of the input's deterministic fingerprint (size, type, content hash). |
| `budget` | Deterministic JSON of the `Budget`. |
| `policy` | Deterministic JSON of the `Policy`. |
| `field_resolved_values` | Per-field resolved value (post-Reconciler). |
| `field_confidence` | Per-field final confidence. |
| `evidence_refs` | Per-field evidence references. |
| `diagnostics` | Per-field diagnostics. |
| `statistics` | Capability invocation counts, latency, cost. |

The hash is **deterministic**: the same inputs always produce the
same hash. The hash is computed using a stable JSON encoder
(RFC 8785-style: sorted keys, no whitespace, canonical number
formatting).

### 2.2 What does NOT go into the hash

- Wall-clock timestamps (determinism-safe: no clock in the replay
  path).
- Random number generator state.
- The Paxman process ID.
- The order in which fields appear in a Python dict (canonical JSON
  normalizes this).

### 2.3 Hash algorithm

V1 uses SHA-256. The hash is hex-encoded in the artifact.

### 2.4 What the hash protects against

The hash detects **any** modification to the artifact's content:

- Changing a resolved value.
- Removing or adding an evidence reference.
- Changing a confidence score.
- Removing a diagnostic.
- Changing the planner or capability version.

Any change produces a different hash. The replay path recomputes
the hash and compares; mismatch raises `HashMismatchError`.

### 2.5 What the hash does NOT protect against

- A re-signing attack: if an attacker has full control of the
  artifact, they can recompute the hash. Paxman is a library; the
  caller is responsible for storing the artifact securely.
- Time-of-creation metadata: the artifact does not embed creation
  time (deliberate, for determinism).

---

## 3. The replay protocol

```text
Caller
  │
  │  artifact: ExecutionArtifact
  │  contract: same contract used originally (caller-supplied)
  ▼
paxman.replay(artifact, contract)
  │
  ├── 1. Check paxman_version compatibility
  │     - if artifact.paxman_version not in supported set → VersionMismatchError
  │
  ├── 2. Check planner_version compatibility
  │     - if artifact.planner_version not supported by this Paxman → VersionMismatchError
  │
  ├── 3. Check capability_versions
  │     - if any pinned capability not in registry → CapabilityNotFoundError
  │
  ├── 4. Re-validate the contract
  │     - if the contract fails validation → InvalidContractError
  │     - this is to detect contract tampering
  │
  ├── 5. Recompute the canonical contract hash
  │     - if contract_canonical_hash in artifact doesn't match → HashMismatchError
  │
  ├── 6. Recompute the replay_hash
  │     - if recomputed hash != artifact.replay_hash → HashMismatchError
  │
  └── 7. Return a rehydrated ExecutionArtifact (byte-equal to input)
```

Replay is **read-only** in the strict sense: it does not invoke any
capability, planner, executor, or reconciler. It is pure
deserialization.

---

## 4. Version compatibility

The replay path enforces version compatibility along three dimensions:

| Dimension | Strictness | Behavior on mismatch |
|---|---|---|
| `paxman_version` | Same major version (semver) | `VersionMismatchError` |
| `planner_version` | Must be supported by current Paxman | `VersionMismatchError` |
| `capability_versions` | All pinned capabilities must be in the registry | `CapabilityNotFoundError` |

### 4.1 Cross-major replay

Cross-major replay (e.g. Paxman 1.x artifact on Paxman 2.0) raises
`VersionMismatchError`. The caller must regenerate the artifact
under the new major.

### 4.2 Cross-minor replay

Cross-minor replay (e.g. Paxman 1.0 artifact on Paxman 1.5) **must
succeed** if the artifact's planner version and capability versions
are still supported. If the new Paxman has dropped support for a
planner version or capability version, it raises
`VersionMismatchError` (or `CapabilityNotFoundError`).

### 4.3 Cross-patch replay

Cross-patch replay is always allowed.

---

## 5. Determinism guarantees

Paxman guarantees the following:

### 5.1 What is deterministic

- The Planner output (`ExecutionPlan`) is deterministic given the
  same canonical contract, input profile, configuration, capability
  registry, budget, and policy.
- The Executor invocation order is deterministic given the same
  `ExecutionPlan`.
- The Reconciler output (`ResolvedResult[]`) is deterministic given
  the same `CandidateResult[]` and `CanonicalContract`.
- The Artifact is deterministic given the same `ResolvedResult[]`,
  `ExecutionPlan`, evidence, and configuration.
- The replay hash is deterministic given the same inputs.

### 5.2 What is NOT deterministic

- Capability outputs from non-deterministic capabilities (e.g.
  `inference` backed by a remote LLM) may differ between runs. Paxman
  records the actual output as evidence and the replay path does not
  re-invoke the capability.
- Wall-clock latency.
- Cost (depends on provider pricing at the time of the call).

### 5.3 Determinism in the presence of non-deterministic capabilities

Paxman does **not** require capabilities to be deterministic. A
non-deterministic capability is allowed, and its output is recorded
as evidence. The artifact includes the recorded output, so replay
reproduces the same artifact without re-invoking the capability.

This means:

- A Paxman run with only deterministic capabilities is **fully
  reproducible** (same inputs → same artifact, byte-equal).
- A Paxman run with non-deterministic capabilities is **replayable**
  (the recorded artifact rehydrates) but **not reproducible**
  (re-running the same inputs may produce a different artifact
  because the non-deterministic capability produced different
  output).

Both cases satisfy the PRD's determinism requirement: "The same
input, contract, version set, and execution constraints must yield
the same plan and replayable result." (PRD §4.5).

---

## 6. Property tests

Determinism is verified by Hypothesis property tests. Examples:

```python
@given(contract=contracts(), input_data=inputs(), budget=budgets(), policy=policies())
def test_planner_is_deterministic(contract, input_data, budget, policy):
    plan_a = planner.plan(contract, profile(input_data), budget, policy, registry)
    plan_b = planner.plan(contract, profile(input_data), budget, policy, registry)
    assert serialize(plan_a) == serialize(plan_b)


@given(artifact=artifacts(), contract=contracts())
def test_replay_is_byte_equal(artifact, contract):
    rehydrated = paxman.replay(artifact, contract)
    assert serialize(rehydrated) == serialize(artifact)
```

These tests run in CI on every PR.

---

## 7. The replay API

```python
import paxman

# Original run
artifact = paxman.normalize(
    input_data=b"raw input",
    contract=my_contract,
    budget=paxman.Budget(max_total_cost_usd=Decimal("0.10")),
    policy=paxman.Policy(allow_remote_inference=True),
)

# ... store artifact somewhere (caller's responsibility) ...

# Later, with just the artifact and the contract
rehydrated = paxman.replay(artifact, contract=my_contract)
assert rehydrated == artifact  # byte-equal
```

The `paxman.replay()` function:

- Takes the captured `ExecutionArtifact` and the **same contract**
  used originally.
- Returns a rehydrated `ExecutionArtifact` that is byte-equal to the
  input.
- Raises `ReplayError` (or one of its subclasses:
  `HashMismatchError`, `VersionMismatchError`,
  `CapabilityNotFoundError`, `InvalidContractError`) on any failure.

### 7.1 Serialization round-trip

The artifact is JSON-serializable. You can:

```python
import json
from paxman.artifact.artifact import ExecutionArtifact

# Serialize
payload = json.dumps(artifact.to_dict(), sort_keys=True, separators=(",", ":"))

# ... store payload somewhere ...

# Rehydrate
artifact = ExecutionArtifact.from_dict(json.loads(payload))
rehydrated = paxman.replay(artifact, contract=my_contract)
```

The serialization format is stable and versioned. A `paxman_version`
field in the JSON is used by the replay path to enforce version
compatibility.

### 7.2 Golden artifacts

Paxman ships a set of **golden artifact** fixtures in
`tests/fixtures/artifacts/`. Each golden is a JSON snapshot of a
real `paxman.normalize()` run. Replay-equality tests verify that
`paxman.replay(golden, contract)` returns a rehydrated artifact that
is byte-equal to the golden.

The goldens are bootstrapped from real implementations, never
predicted. The bootstrap procedure is documented in
`tests/fixtures/artifacts/GENERATION.md`.

---

## 8. What to do if replay fails

| Error | Likely cause | Caller action |
|---|---|---|
| `HashMismatchError` | The artifact was modified or corrupted. | Investigate the source of modification. The artifact is no longer trustworthy. |
| `VersionMismatchError` | The Paxman version does not support the artifact. | Upgrade Paxman or regenerate the artifact under the current version. |
| `CapabilityNotFoundError` | A pinned capability is no longer registered. | Register the missing capability or regenerate the artifact with available capabilities. |
| `InvalidContractError` | The contract supplied to replay is invalid or has been tampered. | Investigate the source of the contract. |

Replay is **fail-closed**: a failure means the artifact cannot be
trusted, and the caller must take explicit action.

---

## 9. See also

- [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md) — the
  full deep dive on replay and determinism.
- [ARCHITECTURE.md §8 Artifact Subsystem](../../ARCHITECTURE.md) —
  internal architecture of the artifact subsystem.
- [ARCHITECTURE.md §9 Versioning Strategy](../../ARCHITECTURE.md) —
  version compatibility policy.
- [GLOSSARY.md §Replay](../../GLOSSARY.md) — vocabulary.
- [ADR-0005](../adr/0005-confidence-ownership.md) — confidence
  ownership (related: confidence is deterministic for replay).
- [docs/howto/replay_artifact.md](../howto/replay_artifact.md) —
  a quick start for using replay.

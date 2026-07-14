# The three invariants

Paxman rests on exactly three invariants. Every design decision in the library — the design of the artifact, the registry, the contract system, the evidence list — exists to support one or more of these invariants.

## 1. Identity

> Paxman only canonicalizes. It never interprets. It never infers. It never orchestrates.

This is what keeps Paxman out of AI and workflow-engine territory. The library has no confidence scores, no best-match algorithms, no probability thresholds, no language-model paths, no user-defined pipelines.

If you find yourself wanting Paxman to "figure out the right form" or "try a few approaches and pick the best one," the answer is that the use case is outside the library's identity boundary. The contract is the source of truth, and the capability satisfies it. There is no third step that picks between options.

## 2. Determinism

> The same `input`, `contract`, registered `capabilities`, `configuration`, and Paxman `version` always produce the same artifact.

The five inputs that shape a canonicalization are:

- The `input` you pass to `paxman.canonicalize()`.
- The `contract` you pass to the same call.
- The set of registered `capabilities` — frozen at the first canonicalize call, so the set is fixed before any execution.
- The `configuration` — Paxman has no user-visible configuration in v2.0.0; the configuration version is currently `"0"`. It is reserved for future use.
- The Paxman `version` — the version string reported by `paxman.__version__`.

All five are recorded on the artifact's `VersionStamp`. Run the same call in two different processes, on two different machines, a year apart — same artifact, byte-for-byte.

## 3. Replay

> Every artifact is independently verifiable: `replay(artifact, contract) == artifact` byte-for-byte, without re-executing capabilities.

Given an artifact and its contract, `paxman.replay()` rehydrates the artifact from its stored form. The capability is not invoked. The version stamp is checked; the content is hashed and compared to the recorded `replay_hash`. If anything is off, `replay()` raises `VersionMismatchError` or `CanonicalizationError`.

This property is unusual. Most libraries cannot promise it. Paxman can, because every input to canonicalization is explicitly versioned and recorded on the artifact.

Replay matters because:

- **It catches tampering.** A stored artifact whose `replay_hash` no longer matches its content is detected at replay time, not silently trusted.
- **It catches version drift.** A stored artifact produced under Paxman v1 cannot be replayed under v2 if the version stamp differs.
- **It enables safe re-canonicalization.** If a user re-canonicalizes the canonical value, the result is byte-equal to the original artifact. Idempotence follows from the replay property.

## How the three invariants reinforce each other

A capability that depends on hidden state — a network call, a current-time read, a random number, a file lookup — breaks all three:

- **Identity** — the capability is no longer a pure function of `(value, contract)`; it is interpreting.
- **Determinism** — the same input produces different artifacts on different runs.
- **Replay** — replaying the artifact from storage does not give the same result, because the hidden state has moved on.

This is why Paxman's design refuses these inputs. A capability may only depend on inputs that are explicitly versioned and recorded on the artifact. A pure function of `(value, contract)` is allowed. A lookup into a bundled, versioned dataset is allowed (the dataset's version is on the artifact). A network call to fetch a fresh result is not.

## What this means for you

- If you call `paxman.canonicalize(x, c)` and then call `paxman.canonicalize(x, c)` again, the artifacts are byte-equal.
- If you store the artifact and call `paxman.replay(artifact, c)` a year later under the same Paxman version, you get the same artifact back.
- If you change the Paxman version, the artifact's `paxman_version` no longer matches and `replay()` raises `VersionMismatchError`. This is the right behavior: the canonical form may have changed between versions, and silent acceptance would be worse than the explicit error.
- If you change the contract, the artifact's `contract_version` no longer matches and `replay()` raises `VersionMismatchError`. Same reasoning.

The three invariants are why Paxman is small, slow, and trusted. Small, because there is no configuration to tune. Slow, because every transformation is sequential and pure. Trusted, because the same input always produces the same output and every output can be independently verified.

## Where to go next

- [What canonicalization is](canonicalization.md) — the conceptual background to these invariants.
- [Contracts](contracts.md) — why the contract is the source of truth.
- [Status and evidence](status-and-evidence.md) — what an artifact actually looks like.

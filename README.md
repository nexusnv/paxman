# Paxman

> Paxman is a deterministic canonicalization engine. It transforms equivalent representations of known information into a single canonical form. When the input does not contain enough information to determine a unique result, Paxman reports that fact rather than guessing.

Paxman is not deterministic-first. Paxman is deterministic, full stop.

## Philosophy & paradigm

From this version onward, Paxman identifies as a **deterministic canonicalization engine** — and explicitly **not** as a normalizer, a deterministic parser, a workflow engine, or an AI extraction system. The distinction is load-bearing:

- **Canonicalization, not normalization.** Normalization is a wider, fuzzier category that admits heuristics, scoring, and interpretation. Paxman does not interpret; it rewrites equivalent representations of *known* information into a single chosen form. Normalization can guess; canonicalization cannot.
- **Canonicalization, not parsing.** A parser maps text → structured value against a grammar. Paxman operates on any representation of known information and produces a canonical form, not a syntax tree. Calling Paxman a parser mis-sets the expected input and output.
- **Capabilities, not pipelines.** Users may contribute new deterministic capabilities; they may not redefine Paxman's pipeline. The pipeline is part of the promise.
- **Resolver, not planner.** "Planner" implies intelligence and strategy. Paxman discovers which capability explicitly declares that it canonicalizes the contract — a deterministic lookup, not a guess.

The complete mandate — thirteen constitutional laws, the SPI rules, the vocabulary to retire, and the contributor litmus test — is recorded in [`MANDATE.md`](./MANDATE.md). That document supersedes the v1.x "contract-driven normalization" framing and is the boundary no future contributor may silently cross.

> Paxman would rather reject a value than silently canonicalize it incorrectly.

## What Paxman does

Paxman takes input that has many valid representations (free text, structured records, etc.) and produces a single canonical output. If the input admits more than one canonical form, Paxman does not pick one. It tells you the input is ambiguous and stops.

## What Paxman does not do

- It does not guess. If the canonical form is not determined by the input and the contract, Paxman does not produce an output.
- It does not call external services. There is no LLM path, no remote inference, no network I/O. Determinism is a property of the library, not a default you can opt out of.
- It does not run in parallel. Capability invocation is sequential.
- It does not improvise. A field the contract does not describe is left alone. A field the input cannot populate is reported as unresolvable.

## Public API

```python
import paxman

result = paxman.canonicalize(
    input_data=raw_input,
    contract=MyContract,
)

rehydrated = paxman.replay(result, contract=MyContract)
assert rehydrated == result  # byte-equal
```

- `canonicalize(input_data, contract) -> ExecutionArtifact` — produce a canonical artifact.
- `replay(artifact, contract) -> ExecutionArtifact` — rehydrate the artifact from the stored form, without re-execution.

The `replay_hash` on the artifact is the deterministic signature that proves the artifact can be rehydrated byte-for-byte.

## Status

v2 is in active development. The previous v1.x releases were retracted on 2026-07-12; see [`RETRACTION.md`](./RETRACTION.md) and the audit postmortem in [`.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md`](./.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md).

This branch is a fresh start. The working tree does not contain the v1.x implementation; that history is preserved in the git log on the `recovery/sprint-1-6` branch.

## Install

There is no `pip install paxman` path yet. To work with the v2 source, install from this working tree:

```bash
git clone https://github.com/nexusnv/paxman.git
cd paxman
uv sync
```

## License

MIT. See [`LICENSE`](./LICENSE).

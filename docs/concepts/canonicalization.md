# What Canonicalization Is

Paxman is a **deterministic canonicalization engine**. This page explains what that means and how it differs from related ideas.

## Canonicalization, in One Sentence

Canonicalization is the selection of exactly one representation from a set of semantically equivalent representations.

For example, the strings `"John.Doe@Gmail.COM"`, `"johndoe@gmail.com"`, and `"  JohnDoe@GMAIL.com  "` are all valid representations of the same email address. A canonicalization engine selects one — `"johndoe@gmail.com"` after lowercasing and Gmail's dot-ignoring rule — and rewrites the input to match.

## What Canonicalization Is Not

Paxman canonicalizes. It does not:

- **Normalize.** Normalization is a wider, fuzzier category that admits guessing, scoring, and interpretation. Paxman does not interpret; it rewrites equivalent representations of *known* information into one chosen form. Normalization can guess; canonicalization cannot.
- **Parse.** A parser maps text to a structured value against a grammar. Paxman operates on any representation of known information and produces a canonical form, not a syntax tree. Calling Paxman a parser mis-sets the expected input and output.
- **Orchestrate.** Paxman does not let you define a pipeline of operations to apply to the input. The pipeline is fixed. You can teach Paxman new transformations (called *capabilities*); you cannot rearrange the order in which Paxman applies them.
- **Infer.** Paxman does not use any form of AI, language model, or statistical guess. If the canonical form is not determined by the input and the contract, Paxman reports the situation and stops.

## The Three Properties Paxman Guarantees

Every `paxman.canonicalize()` call returns an artifact that satisfies three properties. The full formal statement is in [The three invariants](the-three-invariants.md); the short version is:

1. **Determinism.** The same input, contract, registered capabilities, configuration, and Paxman version always produce the same artifact. Run the call twice in two different processes; the artifacts are byte-for-byte identical.
2. **Idempotence.** Re-canonicalizing a canonical value yields the same value. `canonicalize(canonicalize(x)) == canonicalize(x)`. This eliminates a whole class of bugs where re-running canonicalization on already-canonical data drifts.
3. **Replay.** Given an artifact and its contract, `replay()` returns the same artifact without re-executing the capability. The artifact is independently verifiable.

## The Role of the Contract

The contract declares *what* the canonical form is, never *how* to produce it. The contract is the source of truth; the capability is the mechanism that satisfies it.

For example, `Email(provider_aliases="gmail")` declares that the canonical form is "the Gmail-canonicalized form of an email address." It does not say "use regex X, then call function Y." A capability that satisfies the contract is free to implement it however it likes, as long as two independent implementations produce the same canonical form for the same input.

This separation — *what* from *how* — is the central design decision of Paxman. It is what makes the determinism and replay guarantees enforceable: a contract is a closed declaration of policy, and the contract is part of the artifact's identity.

## What Happens When Canonicalization Is Not Possible

If the input does not contain enough information to determine a unique canonical form, Paxman does not guess. It reports one of the four non-success outcomes on the artifact:

- `Status.INVALID` — the input cannot satisfy the contract (e.g. `"foo"` is not a valid email).
- `Status.MISSING` — the contract requires information the input does not provide (a future Money contract might require a currency that the input does not specify).
- `Status.AMBIGUOUS` — more than one registered capability claims the same `(contract, value)` pair. Paxman refuses to pick one; either narrow the registry, or treat the outcome as a rejection.
- `Status.UNSUPPORTED` — the contract's shape is recognized but no registered capability declares that it canonicalizes it.

These are not errors. They are outcomes, recorded on the artifact. Your code is expected to handle them. See [Interpret the five outcomes](../how-to/interpret-the-5-statuses.md) for the recommended pattern.

## Where to Go Next

- [The three invariants](the-three-invariants.md) — the formal statement of the three guarantees.
- [Contracts](contracts.md) — what a contract is, and why the contract is the truth.
- [Status and evidence](status-and-evidence.md) — the five outcomes and the evidence list.

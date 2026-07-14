# Philosophy

Paxman exists because deterministic canonicalization is a different problem from normalization, parsing, AI extraction, and workflow orchestration. This page explains the philosophical foundation and the design decisions that follow from it.

## The Identity Statement

Paxman is a **deterministic canonicalization engine**. It transforms equivalent representations of known information into a single canonical form. When the input does not contain enough information to determine a unique result, Paxman reports that fact rather than guessing.

Three things follow from this identity statement:

1. **Determinism is non-negotiable.** Same input + same contract + same registered capabilities + same configuration + same Paxman version = same artifact. Always. There is no "best effort" mode, no scoring mode, no "fast but less accurate" mode.
2. **Paxman does not interpret.** If the input is `"03/04/2025"`, Paxman does not guess whether it is March 4 or April 3. The contract must specify the locale, or the input is `AMBIGUOUS`. Interpretation is the caller's responsibility, encoded in the contract.
3. **Paxman does not orchestrate.** You cannot write a "pipeline" of operations and have Paxman execute it. The pipeline is fixed; you can teach Paxman new transformations (capabilities), but you cannot rearrange how they are applied.

## What Paxman Is Not

A non-exhaustive list of things Paxman is explicitly not:

- **A normalizer.** Normalization is a wider, fuzzier category that admits ranking, scoring, and interpretation. Paxman rewrites; it does not score.
- **A parser.** A parser maps text to a structured value against a grammar. Paxman operates on representations of known information and produces a canonical form, not a syntax tree.
- **A workflow engine.** You cannot define a DAG of operations and have Paxman execute it. That is a workflow engine. Paxman is not one.
- **An AI system.** Paxman has no language model path, no inference step, no numeric score. If the canonical form is not determined by the inputs, Paxman reports the situation and stops.

## The Three Pillars

Paxman rests on three invariants. Every design decision in the library supports one or more of them.

### Identity

Paxman only canonicalizes. It never interprets, infers, or orchestrates. This is what keeps Paxman out of AI and workflow-engine territory.

### Determinism

The same five inputs (input value, contract, registered capabilities, configuration, Paxman version) always produce the same artifact. Run the call twice in two different processes on two different machines a year apart — same artifact, byte-for-byte.

### Replay

Every artifact is independently verifiable. `replay(artifact, contract) == artifact` byte-for-byte, without re-executing the capability. The artifact carries everything replay needs: the contract, the version stamp, the evidence, the canonical value.

The full statement is in [The three invariants](../concepts/the-three-invariants.md).

## The Role of Evidence

Most libraries that produce a "result" also produce a numeric score. Paxman produces **evidence** instead.

A numeric score is opinion: "I'm 91% sure this is right." Where did `0.91` come from? Can it change? Why `0.91` and not `0.75`?

Evidence is fact: "I applied rule X, which cites specification Y, and the result is Z." Every canonical-form rule in a Paxman capability cites one of three sources (the named dispatch-invariant rules, such as `not_a_string_value`, are the only exception allowed to carry an empty provenance, per Law 14):

1. An authoritative specification (RFC, ISO standard).
2. A documented platform behavior (vendor help article, versioned and dated).
3. A declared Paxman policy (a spec document, with a section reference).

A user who disputes a canonical form can read the evidence, find the rule, look up the citation, and decide for themselves. Numeric scores do not support that workflow. Evidence does.

The full citation policy is in [Why rules cite sources](../concepts/why-rules-cite-sources.md).

## The Role of the Contract

The contract is the source of truth. It declares *what* the canonical form is, never *how* to produce it.

This separation is the central design decision. The contract is a closed declaration of policy; the capability is a mechanism that, given a contract and an input, produces a canonical form that satisfies the contract. A contract that says `Email(provider_aliases="gmail")` declares "the canonical form is the Gmail-canonicalized form of an email address." It does not say "use regex X, then call function Y."

A user who needs different behavior builds a different capability. A user who needs a different policy declares a different contract. The capability implements the contract; the contract does not constrain the implementation.

The full treatment is in [Concepts: Contracts](../concepts/contracts.md).

## The Role of the Capability

A capability is a pure, deterministic transformation that satisfies a contract. It is the only extension point of Paxman.

The capability SPI is narrow on purpose. There is no `next()`, no `execute()`, no `pipeline`, no `stage`. A capability transforms; it does not orchestrate. The narrow SPI is what keeps Paxman from becoming a workflow engine.

The litmus test for whether a candidate capability belongs in Paxman:

> Can two independent implementations of this capability produce different outputs for the same `(value, contract)` pair while both correctly implementing the SPI?

If yes, the dispatch is underdetermined. Paxman rejects underdetermined capabilities at the SPI boundary.

The full treatment is in [Concepts: Capabilities and the SPI](../concepts/capabilities-and-spi.md).

## Why Paxman Is Small

Paxman v2.0.0 ships with one built-in capability, one contract type, and three user-facing functions. This is intentional.

A library that promises to "handle anything" usually handles nothing reliably. A library that promises to handle a small set of cases *correctly* can be trusted. Paxman would rather reject an input than canonicalize it incorrectly. The constraint is the credibility.

The roadmap is to add more built-in capabilities (Date, Money, URL, etc.) one at a time, with the same discipline: each one is a deterministic transformation, each rule cites a source, each contract is a closed declaration of policy.

## Where to Go Next

- [The three invariants](../concepts/the-three-invariants.md) — the formal statement of determinism and replay.
- [What canonicalization is](../concepts/canonicalization.md) — the conceptual background.
- [Stability](stability.md) — the versioning policy and stability guarantees.

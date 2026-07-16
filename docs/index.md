# Paxman

Paxman is a deterministic canonicalization engine. It transforms equivalent representations of known information into a single canonical form. When the input does not contain enough information to determine a unique result, Paxman reports that fact rather than guessing.

## What Paxman Does

You give Paxman an input and a contract. The contract declares what the canonical form must be. Paxman returns a single artifact with one of five outcomes:

- `CANONICALIZED` — the input was canonicalized; the artifact holds the canonical form.
- `INVALID` — the input cannot satisfy the contract.
- `MISSING` — the contract requires information the input does not provide.
- `AMBIGUOUS` — the input admits more than one canonical reading; Paxman will not pick one.
- `UNSUPPORTED` — no registered capability declares that it canonicalizes this contract and value.

Every successful call returns an `ExecutionArtifact`. The artifact is immutable. You can rehydrate it byte-for-byte with `replay()` without calling the underlying transformation again.

## What Paxman Does Not Do

- It does not guess. If the canonical form is not determined by the input and the contract, Paxman does not produce an output.
- It does not call external services. There is no LLM path, no remote inference, no network I/O. Determinism is a property of the library, not a default you can opt out of.
- It does not run in parallel. Each capability is invoked sequentially.
- It does not improvise. A field the contract does not describe is left alone. A field the input cannot populate is reported as unresolvable.

## Try It in Five Minutes

```bash
git clone https://github.com/nexusnv/paxman.git
cd paxman
uv sync
uv run python quickstart.py
```

The quickstart runs without any private-module imports and without a capability registration step. It demonstrates the core loop: `canonicalize()` followed by `replay()`.

See [Getting Started](getting-started/install.md) for the full walkthrough.

## Where to Go Next

- **New to Paxman** — start with [Getting Started](getting-started/install.md) and the [Quickstart walkthrough](getting-started/quickstart.md).
- **Want to understand the design** — read [Concepts](concepts/canonicalization.md) in order. Start with "What canonicalization is" and end with "Why rules cite sources."
- **Have a specific task** — go to [How-to guides](how-to/canonicalize-a-value.md). One page per task.
- **Looking up a function or type** — go to [Reference](reference/api.md).
- **Extending Paxman with your own capability** — read [Concepts: Capabilities and the SPI](concepts/capabilities-and-spi.md), then the [how-to guide for writing a compliant capability](how-to/write-a-compliant-capability.md).
- **Want to know what shipped** — see the [Email capability spec](capabilities/email/index.md), the [UUID capability spec](capabilities/uuid/index.md), the [Date capability spec](capabilities/date/index.md), the [Phone capability spec](capabilities/phone/index.md), and the [URL capability spec](capabilities/url/index.md), and their changelogs.

# Paxman

> Paxman is a deterministic canonicalization engine. It transforms equivalent representations of known information into a single canonical form. When the input does not contain enough information to determine a unique result, Paxman reports that fact rather than guessing.

Paxman is not deterministic-first. Paxman is deterministic, full stop.

## Philosophy & Paradigm

From this version onward, Paxman identifies as a **deterministic canonicalization engine** — and explicitly **not** as a normalizer, a deterministic parser, a workflow engine, or an AI extraction system. The distinction is load-bearing:

- **Canonicalization, not normalization.** Normalization is a wider, fuzzier category that admits guessing, scoring, and interpretation. Paxman does not interpret; it rewrites equivalent representations of *known* information into a single chosen form. Normalization can guess; canonicalization cannot.
- **Canonicalization, not parsing.** A parser maps text → structured value against a grammar. Paxman operates on any representation of known information and produces a canonical form, not a syntax tree. Calling Paxman a parser mis-sets the expected input and output.
- **Deterministic capabilities, not pipelines.** Users may contribute new deterministic capabilities; they may not redefine Paxman's pipeline. The pipeline is part of the promise.
- **Resolver, not planner.** "Planner" implies intelligence and strategy. Paxman discovers which capability explicitly declares that it canonicalizes the contract — a deterministic lookup, not a guess.

The complete mandate — fourteen constitutional laws, the SPI rules, the vocabulary to retire, and the contributor litmus test — is recorded in [`MANDATE.md`](./MANDATE.md). That document supersedes the v1.x "contract-driven normalization" framing and is the boundary no future contributor may silently cross.

> Paxman would rather reject a value than silently canonicalize it incorrectly.

## What Paxman Does

Paxman takes input that has many valid representations (free text, structured records, etc.) and produces a single canonical output. If the input admits more than one canonical form, Paxman does not pick one. It tells you the input is ambiguous and stops.

## What Paxman Does Not Do

- It does not guess. If the canonical form is not determined by the input and the contract, Paxman does not produce an output.
- It does not call external services. There is no LLM path, no remote inference, no network I/O. Determinism is a property of the library, not a default you can opt out of.
- It does not run in parallel. Each capability is invoked sequentially.
- It does not improvise. A field the contract does not describe is left alone. A field the input cannot populate is reported as unresolvable.

## Quickstart

```python
import paxman
from paxman import Email

result = paxman.canonicalize(
    "  John.Doe@Gmail.COM  ",
    Email(provider_aliases="gmail"),
)
print(result.status.name, "->", result.value)
print("evidence:", [(e.rule, e.detail) for e in result.evidence])

rehydrated = paxman.replay(result, Email(provider_aliases="gmail"))
assert rehydrated == result
print("replay ok")
```

Expected output:

```text
CANONICALIZED -> johndoe@gmail.com
evidence: [('stripped_whitespace', ''), ('lowercased_local_part', ''), ('lowercased_domain', ''), ('stripped_dots_in_local_part', '')]
replay ok
```

### Dates

```python
import paxman
from paxman import Date

result = paxman.canonicalize("03/04/2025", Date(locale="US"))
print(result.status.name, "->", result.value)  # CANONICALIZED -> 2025-03-04

result = paxman.canonicalize("2025-01-01T07:00:00-05:00", Date(locale="ISO"))
print(result.value)  # 2025-01-01T12:00:00Z
```

Install with `git clone https://github.com/nexusnv/paxman.git && cd paxman && uv sync`, then `uv run python quickstart.py`.

- `canonicalize(input_data, contract) -> ExecutionArtifact` — produce a canonical artifact.
- `replay(artifact, contract) -> ExecutionArtifact` — rehydrate the artifact from the stored form, without re-execution.
- `Email(*, strict=False, provider_aliases="none", lowercase=True, strip_whitespace=True) -> CanonicalEmailContract` — declare the email contract (your vocabulary, not Paxman's).

## Status

v2 is in active development.


## Install

There is no `pip install paxman` path yet. To work with the v2 source, install from this working tree:

```bash
git clone https://github.com/nexusnv/paxman.git
cd paxman
uv sync
```

## License

MIT. See [`LICENSE`](./LICENSE).

## Extending Paxman

Paxman ships with six built-in capabilities: `email_canonicalization`,
`uuid_canonicalization`, `date_canonicalization`, `phone_canonicalization`,
`url_canonicalization`, and `boolean_canonicalization`. To register your own
custom deterministic capability (a new canonical type, or an alternative
implementation of an existing one), use the SPI:

```python
import paxman
from paxman import Capability, register_capability

class MyCapability:
    name: str = "my_canonicalization"

    def can_handle(self, contract, value) -> bool:
        # Your deterministic predicate here.
        ...

    def canonicalize(self, value, contract):
        # Your pure (value, contract) -> CapabilityResult transform here.
        ...

# Register BEFORE your first canonicalize call.
register_capability(MyCapability())
```

**Because the registry freezes on the first `paxman.canonicalize(...)` call,
register custom capabilities BEFORE your first canonicalize in the process.
Calling `register_capability` after the first canonicalize raises
`FrozenRegistryError`.**

The built-in `EmailCapability` lives at
`paxman._capabilities.email.EmailCapability` (private module —
the import path is part of the SPI surface; user-facing vocabulary is
`Email()`, not `EmailCapability()`). The built-in is auto-loaded on the
first canonicalize; you do not need to register it yourself.

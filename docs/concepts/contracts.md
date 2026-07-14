# Contracts

A contract is a value that declares what the canonical form must be for an input. It is the source of truth in Paxman. The capability is the mechanism that satisfies it.

## What a Contract Declares

A contract declares *what* the canonical form is. It does not declare *how* to produce it.

For example, `Email(provider_aliases="gmail")` declares:

- The canonical form is the Gmail-canonicalized form of an email address.
- Specifically: lowercase the local part and domain, strip leading/trailing ASCII whitespace, normalize `googlemail.com` to `gmail.com`, remove dots in the local part, strip `+tag` suffixes.

It does not say "use regex X, then call function Y, then validate against RFC 5322." A capability that satisfies the contract is free to implement it however it likes — as long as two independent implementations produce the same canonical form for the same input.

This separation is the central design decision of Paxman. The contract is a closed declaration of policy. The capability is a mechanism that, given a contract and an input, produces a canonical form that satisfies the contract.

## How You Write a Contract

There are two equivalent ways to express a contract. They round-trip through each other; pick whichever is more readable in context.

### The Factory Form

```python
from paxman import Email

contract = Email(provider_aliases="gmail")
```

`Email()` is a domain-type factory. It returns a `CanonicalEmailContract` value object. The factory signature is keyword-only:

```python
Email(
    *,
    strict: bool = False,
    provider_aliases: Literal["none", "gmail"] = "none",
    lowercase: bool = True,
    strip_whitespace: bool = True,
) -> CanonicalEmailContract
```

### The Dict DSL Form

```python
import paxman
from paxman import parse_contract

contract = parse_contract({
    "kind": "canonical_email",
    "provider_aliases": "gmail",
    "lowercase": True,
    "strip_whitespace": True,
    "strict": False,
})
```

`parse_contract()` accepts a dict with a `kind` discriminator and the contract fields. It also accepts an already-parsed `CanonicalEmailContract` and returns it unchanged.

`parse_contract()` raises `ContractError` at parse time for an unknown `kind` value, a missing `kind`, a wrong-type field, or a `provider_aliases` value outside the closed set. The parse error happens *before* capability dispatch, so a bad contract is a programming error caught at the call site, not an `Status` outcome on the artifact.

## Why the Contract Is the Truth

Three reasons:

1. **It is closed.** The contract has a fixed set of fields. There is no `auto_detect`, no `infer_provider`, no way for the contract to ask the system to figure something out. Every field is a policy declaration that you, the caller, control.
2. **It is immutable.** `CanonicalEmailContract` is a frozen value object. Once you build it, you cannot mutate it. This is part of what makes the artifact immutable and replay-safe.
3. **It is on the artifact.** The contract is recorded on the artifact. Replay takes both the artifact *and* the contract, and verifies they still match. If the contract has been updated since the artifact was produced, replay refuses to return a result that might no longer reflect the original canonical form.

## The Contract's Relationship to the Artifact

The artifact is produced from three things: the input, the contract, and the registered capabilities. All three are part of the artifact's identity:

- The input is reflected in the canonical value (and in the `AMBIGUOUS` / `INVALID` / `UNSUPPORTED` cases, in the outcome and the evidence).
- The contract is reflected in the artifact's `contract` field. Calling `artifact.contract.as_dict()` returns the same dict you would pass to `parse_contract()`.
- The registered capabilities are reflected in the `capabilities_hash` component of the `VersionStamp`.

This is what makes the artifact replayable. The same input under the same contract and the same capability set produces the same artifact. Change any of the three and you get a different artifact (or `replay()` raises).

## What a Contract Is Not

A contract is not:

- **A configuration file.** Contracts are values, not files. You build them in code, pass them to `canonicalize()`, and they live on the artifact.
- **A pipeline.** A contract does not list operations to apply. It declares a target form. The library's pipeline is fixed.
- **A plugin configuration.** A contract does not say which capability to invoke. The resolver (the registry) decides which capabilities claim the contract, based on whether they declare they can handle it. The contract has no say in that.
- **A regex.** A contract is a typed value object, not a pattern. The string `"User@Example.com"` is an input, not a contract. `Email()` is a contract, not a pattern.

## Where to Go Next

- [The three invariants](the-three-invariants.md) — the determinism and replay guarantees that contracts support.
- [Capabilities and the SPI](capabilities-and-spi.md) — what a capability is and how it relates to a contract.
- [Reference: Contracts](../reference/contracts.md) — the full contract reference.
- [How-to: Canonicalize a value](../how-to/canonicalize-a-value.md) — first canonicalize call.

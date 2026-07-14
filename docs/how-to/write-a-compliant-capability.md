# Write a compliant capability

A capability is the only way to extend Paxman. This page shows how to write one that is fully deterministic, fully cited, and fits Paxman's identity boundary.

## When you need a custom capability

You need a custom capability if you want to canonicalize something Paxman does not ship a built-in for. For example, a future v2.x might ship a `Money` or `Date` capability; in the meantime, you can write your own.

You do **not** need a custom capability to:

- Use a different policy for the email contract (use `Email(...)` with different fields).
- Reject more inputs (use `Email(strict=True)`).
- Apply Gmail's rules (use `Email(provider_aliases="gmail")`).

These are all variations of the built-in email contract, not new capabilities.

## The minimum viable capability

A capability has three members: a `name`, a `can_handle` predicate, and a `canonicalize` method.

```python
import paxman
from paxman import (
    Capability, CapabilityResult, Status, Evidence,
    register_capability,
)


class UppercaseStringCapability:
    """A trivial capability: canonicalize a string to its uppercase form.

    Not a real canonicalization (it conflates 'John' and 'JOHN'), but it
    illustrates the SPI shape.
    """

    name = "uppercase_string"

    def can_handle(self, contract, value):
        # A custom contract type would go here. For this example, claim
        # any string value when the contract is a specific dict shape.
        return (
            isinstance(contract, dict)
            and contract.get("kind") == "uppercase_string"
            and isinstance(value, str)
        )

    def canonicalize(self, value, contract):
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(Evidence(rule="not_a_string_value"),),
            )

        canonical = value.upper()
        evidence = ()
        if canonical != value:
            evidence = (Evidence(
                rule="uppercased",
                detail=f"{value!r} -> {canonical!r}",
                provenance="RFC 3986 §2.1 (reserved characters are case-insensitive in URIs)",
            ),)

        return CapabilityResult(
            status=Status.CANONICALIZED,
            value=canonical,
            evidence=evidence,
        )


# Register BEFORE the first canonicalize call.
register_capability(UppercaseStringCapability())

result = paxman.canonicalize("Hello", {"kind": "uppercase_string"})
assert result.status is Status.CANONICALIZED
assert result.value == "HELLO"
```

The capability:

- Has a unique `name` (used as the registry key and on the artifact's `VersionStamp`).
- Has a `can_handle` predicate that returns `True` for the pairs it claims. The predicate is pure.
- Has a `canonicalize` method that returns a `CapabilityResult` with a `Status`, a value (if canonicalized), and a tuple of evidence entries.

## What every rule must have

Every `Evidence` entry you emit must have a non-empty `provenance` field, citing one of the three sources:

1. An authoritative specification (RFC, ISO standard).
2. A documented platform behavior (vendor help article, versioned and dated).
3. A declared Paxman policy (a spec document, with a section reference).

A rule with no `provenance` is a rule invented because it "felt right." Paxman does not allow that.

For example, in the capability above, the `uppercased` rule cites RFC 3986 §2.1. The `not_a_string_value` rule is a dispatch invariant (it describes a routing failure, not a canonical-form rule) and is allowed to have an empty `provenance`.

In production code, you should maintain a rule→citation manifest the way the email capability does:

```python
_RULE_PROVENANCE = {
    "not_a_string_value": "",  # dispatch invariant
    "uppercased": "RFC 3986 §2.1 (reserved characters are case-insensitive in URIs)",
}

def _evidence(rule, detail=""):
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])
```

The manifest is the single source of truth. A rule with no manifest entry raises `KeyError` at the exact site where the rule is emitted. This makes "I forgot to cite a rule" a build error, not a documentation oversight.

## The SPI litmus test

Before registering, ask: *can two independent implementations of this capability produce different outputs for the same `(value, contract)` pair while both correctly implementing the SPI?*

- If **yes** — the capability is a heuristic. Do not register it.
- If **no** — the capability is a deterministic transformation. Register it.

The `uppercase_string` example above is borderline. Two implementations both produce `"HELLO"` for `"Hello"`, so the test passes. But the capability conflates "John" and "JOHN" (they become the same canonical form), which is a real-world problem. The litmus test is necessary, not sufficient.

## What you cannot do

A capability cannot:

- **Call out to the network.** If the canonical form depends on external data, bundle the data with the capability and record its version on the artifact.
- **Read the current time.** Time is hidden mutable state.
- **Use random numbers.** They are hidden mutable state.
- **Define a pipeline.** A capability is one transformation. The library owns the pipeline.
- **Throw exceptions for outcomes representable as `Status`.** Use `Status.INVALID`, `Status.MISSING`, `Status.AMBIGUOUS`, or `Status.UNSUPPORTED`. Reserve exceptions for the cases the library raises (broken contract, version mismatch, internal invariant violation).
- **Branch on heuristics.** "If the input looks like X, try Y first" is a heuristic. Express it as a deterministic matching rule instead.

## How registration works

```python
import paxman
from paxman import register_capability

register_capability(YourCapability())
```

`register_capability()` adds the capability to the default registry. The registry is **frozen** after the first `paxman.canonicalize()` call. Registering after the first call raises `FrozenRegistryError`.

If you need to use a custom registry (for example, in tests), instantiate `CapabilityRegistry` directly:

```python
from paxman import CapabilityRegistry

registry = CapabilityRegistry()
registry.register(YourCapability())
registry.freeze()
```

The default `paxman.canonicalize()` uses the module-level default registry. To use a custom registry, you would have to call its methods directly (the `CapabilityRegistry` class is part of the public surface, but wiring it into `paxman.canonicalize()` is not yet exposed as a public API in v2.0.0).

## A real-world example: the email capability

The shipped `email_canonicalization` capability is the reference implementation. Read its source for a thorough example:

- `EmailCapability.can_handle` — claims any `CanonicalEmailContract` and string value.
- `EmailCapability.canonicalize` — applies the contract's policy fields in a fixed order, returns `Status.CANONICALIZED` with the canonical form or `Status.INVALID` with a rejection rule.

The capability demonstrates the patterns above:

- Rule→citation manifest in `_RULE_PROVENANCE`.
- Pure function of `(value, contract)`.
- All rejection outcomes expressed as `Status.INVALID`, not exceptions.
- Every rule (except the two dispatch invariants) cites a real source.

See the [Email capability spec](../capabilities/email/index.md) for the rule table.

## Where to go next

- [Capabilities and the SPI](../concepts/capabilities-and-spi.md) — the conceptual background.
- [Why rules cite sources](../concepts/why-rules-cite-sources.md) — the citation policy.
- [The three invariants](../concepts/the-three-invariants.md) — why the narrow SPI exists.

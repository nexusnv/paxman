# Write a Compliant Capability

A capability is the only way to extend Paxman. This page shows how to write one that is fully deterministic, fully cited, and fits Paxman's identity boundary.

## When You Need a Custom Capability

You need a custom capability if you want to canonicalize something Paxman does not ship a built-in for. For example, a future v2.x might ship a `Money` or `Date` capability; in the meantime, you can write your own.

You do **not** need a custom capability to:

- Use a different policy for the email contract (use `Email(...)` with different fields).
- Reject more inputs (use `Email(strict=True)`).
- Apply Gmail's rules (use `Email(provider_aliases="gmail")`).

These are all variations of the built-in email contract, not new capabilities.

## The Minimum Viable Capability

A capability has three members: a `name`, a `can_handle` predicate, and a `canonicalize` method.

```python
import paxman
from paxman import (
    Capability, CapabilityResult, Status, Evidence,
    register_capability,
)


class UriPercentEncodingCapability:
    """A trivial capability: percent-encode reserved characters in a URI.

    This is a real (if narrow) canonicalization. RFC 3986 §2.1 fixes
    the reserved set, and §2.4 fixes the percent-encoding grammar.
    The example is RFC-citable. A similar example that uppercases
    *arbitrary* strings would NOT be RFC-citable; that rule
    invents a canonical form for inputs that do not admit one.
    """

    name = "uri_percent_encoding"

    def can_handle(self, contract, value):
        return (
            isinstance(contract, dict)
            and contract.get("kind") == "uri_percent_encoding"
            and isinstance(value, str)
        )

    def canonicalize(self, value, contract):
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(Evidence(
                    rule="not_a_string_value",
                    provenance="",  # dispatch invariant
                ),),
            )

        # RFC 3986 §2.2 reserved characters that must be percent-encoded
        # when they appear in a URI component. §2.4 fixes the grammar.
        RESERVED = ":/?#[]@!$&'()*+,;="
        canonical = "".join(
            f"%{ord(ch):02X}" if ch in RESERVED else ch
            for ch in value
        )
        evidence = ()
        if canonical != value:
            evidence = (Evidence(
                rule="percent_encoded_reserved",
                detail=f"{value!r} -> {canonical!r}",
                provenance="RFC 3986 §2.2 (reserved characters) + §2.4 (percent-encoding grammar)",
            ),)

        return CapabilityResult(
            status=Status.CANONICALIZED,
            value=canonical,
            evidence=evidence,
        )


# Register BEFORE the first canonicalize call.
register_capability(UriPercentEncodingCapability())

result = paxman.canonicalize("a b/c", {"kind": "uri_percent_encoding"})
assert result.status is Status.CANONICALIZED
assert result.value == "a%20b/c"
```

The capability:

- Has a unique `name` (used as the registry key and on the artifact's `VersionStamp`).
- Has a `can_handle` predicate that returns `True` for the pairs it claims. The predicate is pure.
- Has a `canonicalize` method that returns a `CapabilityResult` with a `Status`, a value (if canonicalized), and a tuple of evidence entries.

## What Every Rule Must Have

Every `Evidence` entry you emit must have a non-empty `provenance` field, citing one of the three sources (MANDATE Law 14):

1. An authoritative specification (RFC, ISO standard).
2. A documented platform behavior (vendor help article, versioned and dated).
3. A declared Paxman policy (a spec document, with a section reference).

A rule with no `provenance` is a rule invented because it "felt right." Paxman does not allow that.

The two named dispatch invariants (`not_a_string_value`, `not_an_email_contract`) are the only entries allowed to carry an empty `provenance`: they describe a routing failure, not a canonical-form rule. Every other entry must cite one of the three sources.

In production code, you should maintain a rule-to-citation manifest the way the email capability does. The manifest is the single source of truth: a rule with no manifest entry raises `KeyError` at the exact site where the rule is emitted, and a rule whose manifest entry is empty (and is not a named dispatch invariant) is a Law 14 violation caught at code review:

```python
_RULE_PROVENANCE = {
    # The only entries with empty provenance (dispatch invariants).
    "not_a_string_value": "",
    "not_an_email_contract": "",
    # Every other rule must cite a source.
    "percent_encoded_reserved": (
        "RFC 3986 §2.2 (reserved characters) + §2.4 (percent-encoding grammar)"
    ),
}

def _evidence(rule, detail=""):
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])
```

A rule with no manifest entry raises `KeyError` at the exact site where the rule is emitted. This makes "I forgot to cite a rule" a build error, not a documentation oversight.

## The SPI Litmus Test

Before registering, ask: *can two independent implementations of this capability produce different outputs for the same `(value, contract)` pair while both correctly implementing the SPI?*

- If **yes** — the capability's dispatch is underdetermined. Do not register it.
- If **no** — the capability is a deterministic transformation. Register it.

The `uri_percent_encoding` example passes the test: every compliant implementation must produce the same `percent_encoded_reserved` output for the same input, because RFC 3986 §2.4 fixes the grammar. A capability that uppercased arbitrary strings would not pass the test in spirit (two implementations could choose different canonical forms for `"JOHN"` and `"john"`), even though the SPI itself does not forbid it.

## What You Cannot Do

A capability cannot:

- **Call out to the network.** If the canonical form depends on external data, bundle the data with the capability and record its version on the artifact.
- **Read the current time.** Time is hidden mutable state.
- **Use random numbers.** They are hidden mutable state.
- **Define a pipeline.** A capability is one transformation. The library owns the pipeline.
- **Throw exceptions for outcomes representable as `Status`.** Use `Status.INVALID`, `Status.MISSING`, `Status.AMBIGUOUS`, or `Status.UNSUPPORTED`. Reserve exceptions for the cases the library raises (broken contract, version mismatch, internal invariant violation).
- **Branch on "looks like X" guesses.** "If the input looks like X, try Y first" is a guess; express it as a deterministic matching rule.

## How Registration Works

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

## A Real-World Example: The Email Capability

The shipped `email_canonicalization` capability is the reference implementation. Read its source for a thorough example:

- `EmailCapability.can_handle` — claims any `CanonicalEmailContract` and string value.
- `EmailCapability.canonicalize` — applies the contract's policy fields in a fixed order, returns `Status.CANONICALIZED` with the canonical form or `Status.INVALID` with a rejection rule.

The capability demonstrates the patterns above:

- Rule-to-citation manifest in `_RULE_PROVENANCE`.
- Pure function of `(value, contract)`.
- All rejection outcomes expressed as `Status.INVALID`, not exceptions.
- Every rule (except the two named dispatch invariants) cites a real source.

See the [Email capability spec](../capabilities/email/index.md) for the rule table.

## Where to Go Next

- [Capabilities and the SPI](../concepts/capabilities-and-spi.md) — the conceptual background.
- [Why rules cite sources](../concepts/why-rules-cite-sources.md) — the citation policy.
- [The three invariants](../concepts/the-three-invariants.md) — why the narrow SPI exists.

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

A capability has three members: a `name`, a `can_handle` predicate, and a `canonicalize` method. Subclass `CapabilityBase` and lean on the shared helpers so the only domain-specific code you write is the canonicalization itself.

The shared helpers (in `paxman._capabilities._shared.base`) remove the boilerplate every capability used to repeat:

- `make_can_handle(contract_cls, *, accept_none=False)` — returns a `can_handle` method that claims the pair when the contract is an instance of `contract_cls` and the value is a string (or `None` too, when `accept_none=True`, so a missing value routes to `Status.MISSING` rather than `Status.UNSUPPORTED`).
- `reject_contract(contract, expected_cls, _evidence, rule)` — returns a rejecting `CapabilityResult` when the contract is not an instance of `expected_cls`, else `None`.
- `reject_non_string(value, _evidence, rule="not_a_string_value")` — returns a rejecting `CapabilityResult` for non-string, non-`None` values, else `None`.
- `reject_missing(value, _evidence, rule="missing_value")` — returns a `Status.MISSING` result for `None`/whitespace-only values, else `None`.

The `_evidence` closure is supplied by the caller so each capability cites its own Law 14 manifest (see below).

```python
import paxman
from paxman._capabilities._shared.base import (
    CapabilityBase,
    make_can_handle,
    reject_contract,
    reject_non_string,
    reject_missing,
)
from paxman._capabilities._shared.evidence import rule_authorities
from paxman._capabilities._shared.grammar import (
    Grammar,
    make_grammar,
    recognize_grammars,
)
from paxman._capabilities._shared.contract import CanonicalXContract
from paxman._provenance import Authority
from paxman._provenance import registries as R
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


# Law 14 rule->authority manifest. Dispatch invariants carry ``None``
# (they describe a routing failure, not a canonical-form rule). Every
# canonical-form rule cites an authoritative source.
_RULE_AUTHORITIES = {
    "not_a_x_contract": None,
    "not_a_string_value": None,
    "missing_value": None,
    "percent_encoded_reserved": (
        "RFC 3986 §2.2 (reserved characters) + §2.4 (percent-encoding grammar)"
    ),
}
_evidence = rule_authorities(_RULE_AUTHORITIES)

GRAMMARS: tuple[Grammar, ...] = (
    make_grammar(
        "x_reserved",
        "RFC 3986 §2.2 (reserved character set)",
        r"^(?P<value>.+)$",
        shape="x",
    ),
)


class XCapability(CapabilityBase):
    """A trivial capability: percent-encode reserved characters in a URI.

    This is a real (if narrow) canonicalization. RFC 3986 §2.1 fixes
    the reserved set, and §2.4 fixes the percent-encoding grammar.
    The example is RFC-citable. A similar example that uppercases
    *arbitrary* strings would NOT be RFC-citable; that rule
    invents a canonical form for inputs that do not admit one.
    """

    name = "x_canonicalization"

    # Helper-derived predicate: claims any CanonicalXContract + string value.
    can_handle = make_can_handle(CanonicalXContract, accept_none=False)

    def canonicalize(self, value, contract, engine=None):
        # Dispatch guards — pure, shared, preserve exact Status/evidence shapes.
        r = reject_contract(contract, CanonicalXContract, _evidence, "not_a_x_contract")
        if r is not None:
            return r
        r = reject_non_string(value, _evidence)
        if r is not None:
            return r
        r = reject_missing(value, _evidence)
        if r is not None:
            return r

        # Recognition layer (anchored-regex domains) — shape classification only.
        reps = recognize_grammars(GRAMMARS, value, contract, CanonicalXContract)
        if not reps:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format"),)
            )

        # RFC 3986 §2.2 reserved characters that must be percent-encoded.
        RESERVED = ":/?#[]@!$&'()*+,;="
        canonical = "".join(
            f"%{ord(ch):02X}" if ch in RESERVED else ch for ch in value
        )
        evidence = ()
        if canonical != value:
            evidence = (_evidence("percent_encoded_reserved", f"{value!r} -> {canonical!r}"),)
        return CapabilityResult(
            status=Status.CANONICALIZED, value=canonical, evidence=evidence
        )


# Register BEFORE the first canonicalize call (built-ins are auto-registered).
paxman.register_capability(XCapability())

result = paxman.canonicalize("a b/c", CanonicalXContract())
assert result.status is Status.CANONICALIZED
assert result.value == "a%20b%2Fc"  # space -> "%20", "/" -> "%2F"
```

The capability:

- Has a unique `name` (used as the registry key and on the artifact's `VersionStamp`).
- Declares `can_handle` as a class attribute via `make_can_handle(...)` — no hand-written predicate.
- Opens `canonicalize` with the three shared dispatch guards (`reject_contract` → `reject_non_string` → `reject_missing`), each returning early with the exact `Status`/`evidence` shape the inline code used to produce.
- Returns a `CapabilityResult` with a `Status`, a value (if canonicalized), and a tuple of evidence entries.

### Recognition: the shared seam and the two escapes

For anchored-regex domains, recognition is a single call to `recognize_grammars(GRAMMARS, value, contract, CanonicalXContract)`, which full-matches the input against your `GRAMMARS` tuple and returns `RecognizedRep` objects carrying each grammar's `source` (Law 14). Recognition classifies shape only — it assigns no canonical meaning; the resolver does. The shipped `ip` capability is the canonical simple example of this seam (`ip/grammar.py` + `ip/rules.py` + `ip/canonicalizer.py`).

Two built-ins bring their own recognition and are the documented escapes from `recognize_grammars`:

- **`date`** — its grammars are expressed in a small *bracket notation* (a date-specific shape vocabulary compiled to anchored regexes), so it owns a bespoke `recognize` in `date/grammar.py` rather than calling `recognize_grammars` directly.
- **`money`** — it folds recognition into a *structured parser* (`money/grammar.py: parse_amount` / `recognize_money`) because amount + currency layout is not a single anchored regex; recognition lives inside `canonicalize`.

If your domain is a plain anchored-regex shape, use `recognize_grammars`. Reach for the date/money pattern only when a bracket notation or a structured parser is genuinely required.

## What Every Rule Must Have

Every `Evidence` entry you emit must cite one of the three sources (MANDATE Law 14):

1. An authoritative specification (RFC, ISO standard).
2. A documented platform behavior (vendor help article, versioned and dated).
3. A declared Paxman policy (a spec document, with a section reference).

A rule with no citation is a rule invented because it "felt right." Paxman does not allow that.

The dispatch invariants (`not_a_string_value`, `not_a_x_contract`, `missing_value`, …) are the only entries allowed to carry a `None` authority: they describe a routing failure, not a canonical-form rule. Every other entry must cite one of the three sources.

In production code, you maintain a rule-to-authority manifest — a `_RULE_AUTHORITIES` mapping — and bind it to an `_evidence` closure via `rule_authorities` (from `paxman._capabilities._shared.evidence`). The manifest is the single source of truth: a rule with no manifest entry raises `KeyError` at the exact site where the rule is emitted, and a rule whose manifest entry is `None` (and is not a named dispatch invariant) is a Law 14 violation caught at code review. Citations come from `paxman._provenance` — `Authority` objects and the `registries` module (`R`) in `src/paxman/_provenance/registries/`, plus the spec documents under `src/paxman/_provenance/specs/` (see `src/paxman/_provenance/evidence.py` for the `Evidence` shape).

```python
from paxman._capabilities._shared.evidence import rule_authorities
from paxman._provenance import Authority
from paxman._provenance import registries as R

# Law 14 rule->authority manifest. Dispatch invariants carry ``None``
# (Law 14 §3.6 allow-list). Every canonical-form rule cites a source.
_RULE_AUTHORITIES = {
    # --- dispatch invariants (no authority — Law 14 §3.6 allow-list) ---
    "not_a_x_contract": None,
    "not_a_string_value": None,
    "missing_value": None,
    # --- canonical-form rules (cite an authoritative source) ---
    "percent_encoded_reserved": (
        "RFC 3986 §2.2 (reserved characters) + §2.4 (percent-encoding grammar)"
    ),
}

_evidence = rule_authorities(_RULE_AUTHORITIES)
```

A rule with no manifest entry raises `KeyError` at the exact site where the rule is emitted. This makes "I forgot to cite a rule" a build error, not a documentation oversight.

## The SPI Litmus Test

Before registering, ask: *can two independent implementations of this capability produce different outputs for the same `(value, contract)` pair while both correctly implementing the SPI?*

- If **yes** — the capability's dispatch is underdetermined. Do not register it.
- If **no** — the capability is a deterministic transformation. Register it.

The `uri_percent_encoding` example passes the test: every compliant implementation must produce the same `percent_encoded_reserved` output for the same input, because RFC 3986 §2.4 fixes the grammar. A capability that uppercased arbitrary strings would not pass the test in spirit (two implementations could choose different canonical forms for `"JOHN"` and `"john"`), even though the SPI itself does not forbid it.

## The Three Invariants

Every capability must preserve the three invariants (MANDATE §1.2). A capability that breaks one broke the contract:

- **Identity** — canonicalize only; never interpret, infer, or orchestrate. A capability rewrites equivalent representations of *known* information into one chosen form. It does not guess, score, or decide what the input "means."
- **Determinism** — same input + contract + registered capabilities + config + version → same artifact. The `can_handle` predicate and `canonicalize` are pure functions of `(value, contract)` (plus the threaded `engine`, which is itself fixed for a given call). No clock, no randomness, no hidden state.
- **Replay** — `replay(artifact, contract) == artifact` byte-for-byte, without re-executing the capability. Every emitted `Evidence` entry is recorded so the artifact rehydrates exactly.

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

## The Registration and Export Contract

Adding a new built-in capability touches exactly two places, and only your own package plus one line of shared wiring:

1. **Your domain package** — `src/paxman/_capabilities/<domain>/` — containing `contract.py` (`CanonicalXContract` + the user-facing `X` vocabulary), `canonicalizer.py` (the `CapabilityBase` subclass), `grammar.py` (the `GRAMMARS` + `recognize` seam, if anchored-regex), and `rules.py` (the `_RULE_AUTHORITIES` manifest + `_evidence` closure).
2. **One line in `src/paxman/_capabilities/discovery.py`** — add `XCapability()` to the `builtin_capabilities()` list. That single line makes the capability auto-registered before the first `canonicalize`; the user does not register it themselves.

The public surface is **auto-derived** — you do not hand-edit a `Contract` union or an `__all__` literal. `paxman/__init__.py` derives both the `Contract` union and the `Canonical*` `__all__` entries from `builtin_capabilities()`. The only manual export step is the user-facing vocabulary line:

```python
from paxman._capabilities.<domain>.contract import X, CanonicalXContract
```

Keep that line — it is the public name users type (`from paxman import X`). Everything else (the `Contract` union member, the `__all__` entry, the `CanonicalXContract` re-export) is generated from it. This is what makes the next 50 capabilities cheap to add: one package, one discovery line, one vocabulary import.

## Scaling Tax (Known)

Finding D: the `_RULE_AUTHORITIES` manifest is required **per capability**, and at 50 capabilities it will be the dominant authoring cost. Every canonical-form rule must cite a Law 14 source — an authoritative spec, documented platform behavior, or a declared Paxman policy. The citations are sourced from `src/paxman/_provenance/evidence.py` (the `Evidence`/`Authority` shape) and the spec + registry documents under `src/paxman/_provenance/specs/` and `src/paxman/_provenance/registries/`. Budget for the manifest as the real work of each new capability; the `can_handle` predicate and the dispatch guards are already free via the shared helpers.

## A Real-World Example: The Email Capability

The shipped `email_canonicalization` capability is the reference implementation. Read its source for a thorough example:

- `EmailCapability.can_handle` — claims any `CanonicalEmailContract` and string value.
- `EmailCapability.canonicalize` — applies the contract's policy fields in a fixed order, returns `Status.CANONICALIZED` with the canonical form or `Status.INVALID` with a rejection rule.

The capability demonstrates the patterns above:

- Rule-to-authority manifest in `_RULE_AUTHORITIES` (via `rule_authorities`).
- Pure function of `(value, contract)`.
- All rejection outcomes expressed as `Status.INVALID` (or `Status.MISSING`), not exceptions.
- Every rule (except the named dispatch invariants) cites a real source.

See the [Email capability spec](../capabilities/email/index.md) for the rule table.

## Where to Go Next

- [Capabilities and the SPI](../concepts/capabilities-and-spi.md) — the conceptual background.
- [Why rules cite sources](../concepts/why-rules-cite-sources.md) — the citation policy.
- [The three invariants](../concepts/the-three-invariants.md) — why the narrow SPI exists.

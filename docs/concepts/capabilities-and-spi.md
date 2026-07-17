# Capabilities and the SPI

A capability is a pure, deterministic transformation that satisfies a contract. It is the only extension point of Paxman.

## What a Capability Does

A capability answers one question: *"Can I canonicalize this value, given this contract?"* If yes, it returns a `CapabilityResult` with the canonical value and a list of evidence entries.

A capability is:

- **Pure.** A function of `(value, contract)`. No network calls, no filesystem access, no current-time reads, no random numbers. The same inputs always produce the same output.
- **Deterministic.** Given the same input and contract, the capability always returns the same `CapabilityResult`. The order in which the registry sees the capabilities does not change the result.
- **Bounded.** A capability transforms. It does not orchestrate, branch, or sequence. The Paxman pipeline is fixed; the capability plugs into one stage of it.

## What a Capability Does Not Do

A capability does not:

- Call out to the network. If you need data from the network, you must bundle it with the capability (and the bundled dataset's version must be part of the artifact's `VersionStamp`).
- Read the current time. Time is hidden mutable state; a capability that depends on time is not deterministic.
- Throw exceptions for outcomes that can be represented as `Status` values. A capability that fails a grammar check returns `Status.INVALID`, not a `ValueError`. Exceptions are reserved for situations where the call cannot proceed at all (and are raised by the library, not by the capability).
- Define a pipeline. A capability is one transformation, not a chain of transformations. The library owns the pipeline; the user owns the knowledge the pipeline applies.

## The SPI

The SPI (service provider interface) is the protocol a capability must satisfy. In its narrowest form, it has three members:

```python
class Capability(Protocol):
    name: str

    def can_handle(self, contract, value) -> bool: ...

    def canonicalize(self, value, contract) -> CapabilityResult: ...
```

- `name` is a unique identifier. It appears in the artifact's evidence, in the `capabilities_hash` component of the `VersionStamp`, and in error messages. Two capabilities with the same name cannot both be registered.
- `can_handle(contract, value)` returns `True` if the capability declares it can canonicalize the pair, `False` otherwise. It must be deterministic.
- `canonicalize(value, contract)` does the work. It returns a `CapabilityResult` with a `Status`, an optional canonical value, and a tuple of evidence entries.

Notice what is *not* in the SPI. There is no `next()`, no `execute()`, no `pipeline`, no `stage`, no context switching, no branching. A capability does not orchestrate; it transforms.

## Why the SPI Is Narrow

The narrowness is the central design decision. It is what keeps Paxman from becoming a workflow engine.

If the SPI allowed a capability to return "I have a result, and now run this other capability," the system would have a pipeline. Once you have a pipeline, you have control flow in the user's hands. Once you have control flow, the user can encode ranking, fallbacks, and probabilistic logic. Once ranking or probability enters the dispatch, determinism has been silently forfeited.

The narrow SPI prevents this. A capability answers one question and returns one result. The library owns the question of *how* to combine multiple capabilities' answers (currently: if exactly one claims the pair, use it; if zero claim it, return `UNSUPPORTED`; if more than one claims it, return `AMBIGUOUS`).

## The SPI Litmus Test

Before registering a new capability, run it through this question:

> Can two independent implementations of this capability produce different outputs for the same `(value, contract)` pair while both correctly implementing the SPI?

If the answer is **yes**, the capability is not a Paxman capability. The abstraction is underdetermined; the dispatch would have to pick a winner. Paxman rejects underdetermined abstractions at the SPI boundary.

For example:

- A `CanonicalDate.parse("2025-01-01")` capability is good: every compliant implementation must produce exactly `"2025-01-01"`.
- A `infer_vendor_name(text)` capability is bad: one implementation might pick `"ABC Ltd"`, another `"ABC Holdings"`, and both would satisfy the SPI. The SPI itself was not deterministic.

The litmus test is the filter for whether a candidate capability belongs in Paxman.

## How Capabilities Are Registered

You register a capability before your first `paxman.canonicalize()` call:

```python
import paxman
from paxman import register_capability

class MyCapability:
    name = "my_canonicalization"

    def can_handle(self, contract, value):
        ...

    def canonicalize(self, value, contract):
        ...

register_capability(MyCapability())
```

After the first `canonicalize()` call, the registry is frozen. Further `register_capability()` calls raise `FrozenRegistryError`. This is by design: the capability set is part of the determinism invariant, so it must be fixed before the first execution.

See the [How-to: Write a compliant capability](../how-to/write-a-compliant-capability.md) page for a full worked example.

## What Comes in the Box

Paxman v2.0.0 ships nine built-in capabilities:

- `email_canonicalization` — see the [Email capability spec](../capabilities/email/index.md).
- `uuid_canonicalization` — see the [UUID capability spec](../capabilities/uuid/index.md).
- `phone_canonicalization` — see the [Phone capability spec](../capabilities/phone/index.md).
- `url_canonicalization` — see the [URL capability spec](../capabilities/url/index.md).
- `date_canonicalization` — see the [Date capability spec](../capabilities/date/index.md).
- `boolean_canonicalization` — see the [Boolean capability spec](../capabilities/boolean/index.md).
- `ip_canonicalization` — see the [IP capability spec](../capabilities/ip/index.md).
- `money_canonicalization` — see the [Money capability spec](../capabilities/money/index.md).
- `geolocation_canonicalization` — see the [Geolocation capability spec](../capabilities/geolocation/index.md).

The built-in is auto-loaded on the first `canonicalize()` call. You do not need to register it yourself. If you register a capability named `email_canonicalization` before the first call, your registration wins; the built-in is skipped.

## Where to Go Next

- [Why rules cite sources](why-rules-cite-sources.md) — what makes a capability compliant.
- [The three invariants](the-three-invariants.md) — why the narrow SPI exists.
- [How-to: Write a compliant capability](../how-to/write-a-compliant-capability.md) — the worked example.
- [Email capability](../capabilities/email/index.md) — the shipped capability, studied as a reference.

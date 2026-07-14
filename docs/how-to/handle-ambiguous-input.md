# Handle Ambiguous Input

`Status.AMBIGUOUS` means more than one registered capability claimed the same `(contract, value)` pair. Paxman refuses to pick one. This page explains what to do.

## What Ambiguity Means

Each capability's `can_handle(contract, value)` method returns `True` if the capability declares it can canonicalize the pair. The registry collects every capability whose `can_handle` returned `True`. If the list has:

- **One entry** — that capability is used. The artifact has `Status.CANONICALIZED` (or whatever the capability returned).
- **Zero entries** — the artifact has `Status.UNSUPPORTED`.
- **More than one entry** — the artifact has `Status.AMBIGUOUS`. The capability is *not* invoked.

Paxman does not pick between claimants. The reason: if two capabilities both return `True` for the same pair, by construction there is no unique canonical answer — the system has, in effect, two equally-valid definitions of "canonical" for that input. The library reports the situation and stops.

## A Contrived Example

Suppose you have two capabilities registered:

- `EmailUppercase` — claims `can_handle(c, v) == True` for any email contract, and canonicalizes by uppercasing the local part.
- `EmailLowercase` — claims `can_handle(c, v) == True` for any email contract, and canonicalizes by lowercasing the local part.

If you call `paxman.canonicalize("John@Example.com", Email())`:

- Both capabilities claim the pair.
- The registry returns a list of length 2.
- The orchestrator classifies `Status.AMBIGUOUS`.
- Neither capability is invoked.

The artifact's `value` is `None`. The evidence contains a `multiple_claimants` rule listing both capabilities.

## How to Fix It

The fix is to remove the ambiguity. Three options:

1. **Unregister the duplicate.** If you control the registry, remove one of the capabilities. The library's invariant is that a `(contract, value)` pair is canonicalized by at most one capability.
2. **Narrow the `can_handle` predicate.** Make one of the capabilities more specific so it only claims a subset of pairs. For example, `EmailUppercase` could be renamed and registered under a different contract `kind` that only uppercase-canonicalization declares.
3. **Use a more specific contract.** A more specific contract (with stricter fields) might be claimed by only one capability. The contract is the policy; if the policy is clear, the ambiguity goes away.

## What to Do at Runtime

If ambiguity comes back and you cannot change the registry, you have three options at runtime:

1. **Escalate to a human.** Surface the ambiguous pair to a user. The user picks which canonical form to use. The choice is recorded in your system, not in Paxman.
2. **Pick deterministically by capability name.** If the two capabilities have different names, you can pick by name (alphabetically first, for example). This is *your* choice, not Paxman's. Document the policy in your application.
3. **Reject the input.** Some applications have a rule: "if the system cannot decide, the input is invalid." Treat `AMBIGUOUS` the same way you treat `INVALID` and reject.

In all three cases, log the evidence. The `multiple_claimants` rule lists the claiming capabilities, which is the information you need to debug.

## A Worked Example

```python
import paxman
from paxman import Email, Status, register_capability, Capability, CapabilityResult

# Two overlapping capabilities, both claim any email contract.
class EmailUppercase:
    name = "email_uppercase"

    def can_handle(self, contract, value):
        from paxman import CanonicalEmailContract
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(self, value, contract):
        local, _, domain = value.partition("@")
        return CapabilityResult(
            status=Status.CANONICALIZED,
            value=f"{local.upper()}@{domain.lower()}",
            evidence=(),
        )


class EmailLowercase:
    name = "email_lowercase"

    def can_handle(self, contract, value):
        from paxman import CanonicalEmailContract
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(self, value, contract):
        return CapabilityResult(
            status=Status.CANONICALIZED,
            value=value.lower(),
            evidence=(),
        )


# Register BOTH before the first canonicalize.
register_capability(EmailUppercase())
register_capability(EmailLowercase())

# The first canonicalize freezes the registry. Both capabilities are
# in the claimant set; the orchestrator classifies AMBIGUOUS.
result = paxman.canonicalize("John@Example.com", Email())
assert result.status is Status.AMBIGUOUS
print(result.evidence)
```

If you re-run this code after removing one of the `register_capability` calls, the artifact's status becomes `CANONICALIZED`.

## When Ambiguity Should Not Happen

In a well-designed system, ambiguity should be rare. Most use cases have a single capability per contract `kind`. Ambiguity is a sign that:

- Two capabilities overlap on purpose (rare; usually a refactor in progress).
- A custom capability was registered that duplicates a built-in.
- A custom capability's `can_handle` is too permissive.

If ambiguity comes back and you did not expect it, audit the registered capabilities. The registry's `CapabilityRegistry.capabilities_hash()` returns the sorted list of registered capability names; you can compare it against your expected set.

## Where to Go Next

- [Interpret the five outcomes](interpret-the-5-statuses.md) — the full pattern.
- [Status and evidence](../concepts/status-and-evidence.md) — what the evidence list contains.
- [Reference: `Status`](../reference/api.md#status) — the enum reference.

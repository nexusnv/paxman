# Canonicalize a value

This is the most basic Paxman operation. You give it an input and a contract. It gives you back an artifact with the canonical form (or an outcome explaining why it could not).

## The minimal call

```python
import paxman
from paxman import Email, Status

result = paxman.canonicalize("User@Example.com", Email())

assert result.status is Status.CANONICALIZED
print(result.value)  # "user@example.com"
```

The two required arguments:

- `input_data` — the value to canonicalize. For the email capability, this is a string. Other capabilities (current and future) may accept other types.
- `contract` — the value object that declares the canonical form. For email, you build it with `Email(...)`.

The return value is an `ExecutionArtifact`. It always has a `status` field. If the status is `CANONICALIZED`, the `value` field holds the canonical form. Otherwise, `value` is `None` and the `evidence` field explains what happened.

## Choosing the contract

The contract is the policy. Pick the policy that matches what "canonical" means for your use case:

```python
# Strict email — reject anything with whitespace or non-ASCII.
paxman.canonicalize(input_str, Email(strict=True))

# Gmail canonicalization — apply Gmail's documented alias rules.
paxman.canonicalize(input_str, Email(provider_aliases="gmail"))

# Conservative — preserve case but still strip whitespace.
paxman.canonicalize(input_str, Email(lowercase=False, strip_whitespace=True))

# Exact — preserve the input as-is.
paxman.canonicalize(input_str, Email(lowercase=False, strip_whitespace=False))
```

See [Contracts](../concepts/contracts.md) for what each field means.

## Reading the result

Every artifact has six fields. The three you will read most often:

| Field | Type | What it tells you |
|---|---|---|
| `status` | `Status` | One of the five outcomes. |
| `value` | `str \| None` | The canonical form if `status` is `CANONICALIZED`, else `None`. |
| `evidence` | `tuple[Evidence, ...]` | The ordered list of rules that fired, with citations. |

The other three (`contract`, `version_stamp`, `replay_hash`) are used by `replay()` and for storage. You usually do not read them directly.

For the full artifact schema, see [Reference: ExecutionArtifact](../reference/api.md#executionartifact).

## Inspecting the evidence

To understand what a canonicalize call did, read the `evidence` list:

```python
result = paxman.canonicalize(
    "  John.Doe@Gmail.COM  ",
    Email(provider_aliases="gmail"),
)

for entry in result.evidence:
    print(f"  - {entry.rule}: {entry.detail}  [{entry.provenance}]")
```

Output for the input above:

```text
  - stripped_whitespace:  [RFC 5322 §2.1 + §3.6.3]
  - lowercased_local_part:  [Paxman spec/email §1.3]
  - lowercased_domain:  [RFC 5321 §2.4]
  - domain_synonym_gmail: googlemail.com -> gmail.com  [Google Help: "Use aliases on your Account" (retrieved 2026-07-14)]
  - stripped_dots_in_local_part:  [Google Help: dots don't matter in Gmail addresses]
  - stripped_plus_tag:  [Google Help: Gmail +alias addressing]
```

Each rule has a `provenance` field. The `provenance` is a citation. See [Why rules cite sources](../concepts/why-rules-cite-sources.md) for the citation policy.

## What if the call returns a non-success status?

The call did not fail — it succeeded in reporting the situation. Your code should handle each of the five outcomes. See [Interpret the five outcomes](interpret-the-5-statuses.md) for the recommended pattern.

## What if the call raises an exception?

A canonicalize call should not raise for any outcome representable as a `Status`. Exceptions are reserved for situations the library cannot proceed through:

- `ContractError` — only raised by `parse_contract()`, not by `canonicalize()`.
- `FrozenRegistryError` — you tried to register a capability after the first canonicalize.
- `VersionMismatchError` — only raised by `replay()`, not by `canonicalize()`.

If `paxman.canonicalize()` raises an exception, something unexpected happened. See the [Error reference](../reference/errors.md).

## Where to go next

- [Replay for verification](replay-for-verification.md) — verify an artifact byte-for-byte.
- [Interpret the five outcomes](interpret-the-5-statuses.md) — handle each `Status` value.
- [Reference: `paxman.canonicalize`](../reference/api.md#canonicalize) — the full signature.

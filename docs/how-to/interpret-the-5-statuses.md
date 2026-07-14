# Interpret the Five Outcomes

`paxman.canonicalize()` returns an `ExecutionArtifact` with one of five `Status` values. This page shows the recommended pattern for handling all of them.

## The Five Outcomes

| Status | Meaning |
|---|---|
| `CANONICALIZED` | Success. `artifact.value` holds the canonical form. |
| `INVALID` | The input cannot satisfy the contract. |
| `MISSING` | The contract requires information the input does not provide. |
| `AMBIGUOUS` | More than one capability claimed the `(contract, value)` pair. |
| `UNSUPPORTED` | No registered capability declared it canonicalizes this pair, or the contract's `kind` is not recognized. |

## The Recommended Pattern

```python
import paxman
from paxman import Email, Status

result = paxman.canonicalize(input_data, Email(provider_aliases="gmail"))

if result.status is Status.CANONICALIZED:
    use_canonical_value(result.value)
elif result.status is Status.INVALID:
    log_rejection(result.evidence)
elif result.status is Status.MISSING:
    request_missing_fields()
elif result.status is Status.AMBIGUOUS:
    escalate_to_human(result.evidence)
elif result.status is Status.UNSUPPORTED:
    register_capability_or_fail()
```

Each branch reads the artifact's `evidence` (where appropriate) and takes the right action. The library returns the outcome; your code decides what to do with it.

## CANONICALIZED

The success path. `result.value` holds the canonical form. You can use it directly:

```python
if result.status is Status.CANONICALIZED:
    send_email(result.value)
```

For audit purposes, you may also want to log the evidence:

```python
if result.status is Status.CANONICALIZED:
    canonical = result.value
    log_evidence(canonical, result.evidence)
```

## INVALID

The input cannot be canonicalized. For the email capability, common causes are:

- Missing `@` (e.g. `"johndoe"`).
- Empty local or domain (e.g. `"@example.com"`).
- Failed grammar gate (e.g. `"user@-bad.com"`).
- Strict-mode rejection (e.g. `"user with space@example.com"` under `Email(strict=True)`).

Each cause has a corresponding `Evidence` rule in the artifact. Read the evidence to log the specific reason:

```python
if result.status is Status.INVALID:
    for entry in result.evidence:
        log.warning(f"rejection: {entry.rule} ({entry.provenance})")
```

## MISSING

The contract requires information the input does not provide. The exact meaning depends on the contract. For the v2.0.0 email contract, `MISSING` is rarely returned because the contract has no required fields beyond the input string itself. Future contract types (Money, Date, etc.) will use `MISSING` to mean "the input does not specify a required field, like the currency."

The action is to ask the user (or an upstream system) for the missing information and retry.

## AMBIGUOUS

More than one registered capability claims the `(contract, value)` pair. Paxman refuses to pick one. This is not a bug in your code; it means two capabilities overlap on this input.

The action depends on your application:

- **If you control the registry** — narrow one of the capabilities so it does not claim this pair, or remove the duplicate.
- **If you do not control the registry** — escalate to a human, or pick a capability by `name` (deterministically) and document the choice.

The `evidence` list contains a `multiple_claimants` rule with the names of the claiming capabilities. You can read it to make the choice visible.

## UNSUPPORTED

No registered capability declared it canonicalizes this pair, or the contract's `kind` is not recognized.

For the v2.0.0 release, the only contract `kind` is `"canonical_email"`. If you pass a dict with `kind="canonical_money"` to `parse_contract()`, it raises `ContractError` at parse time (a programming error caught at the call site, not a `Status` outcome on the artifact).

The action depends on the cause:

- **Unknown contract kind** — fix the contract. The valid kinds are enumerated in the [Contracts reference](../reference/contracts.md).
- **No capability claims the pair** — register a capability that does, or stop calling `canonicalize()` for this input.

## What About Exceptions?

A canonicalize call should not raise for any outcome representable as a `Status`. Exceptions are reserved for situations where the call cannot proceed at all. See the [Error reference](../reference/errors.md) for the full list.

If you wrap canonicalize calls in a `try/except`, the only exception you should expect is `ContractError` (from `parse_contract()`, not from `canonicalize()` itself).

## A Complete Example

```python
import paxman
from paxman import Email, Status

def canonicalize_email(raw_input: str) -> str | None:
    """Return the canonical email form, or None if the input cannot be canonicalized."""
    result = paxman.canonicalize(raw_input, Email(provider_aliases="gmail"))

    if result.status is Status.CANONICALIZED:
        return result.value

    if result.status is Status.INVALID:
        log_invalid(raw_input, result.evidence)
        return None

    if result.status is Status.AMBIGUOUS:
        log_ambiguous(raw_input, result.evidence)
        return None

    if result.status is Status.UNSUPPORTED:
        log_unsupported(raw_input, result.evidence)
        return None

    if result.status is Status.MISSING:
        log_missing(raw_input, result.evidence)
        return None

    # Unreachable: the five Status values are exhaustive.
    raise AssertionError(f"unhandled status: {result.status}")
```

The function returns the canonical email or `None`. Each branch logs the reason. The artifact is the result; the function decides what the rest of the application does with it.

## Where to Go Next

- [Handle ambiguous input](handle-ambiguous-input.md) — a deeper look at one branch.
- [Status and evidence](../concepts/status-and-evidence.md) — the artifact fields.
- [Reference: `Status`](../reference/api.md#status) — the enum reference.

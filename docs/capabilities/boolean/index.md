# Boolean Capability

The boolean capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings into boolean representations. It is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `boolean_canonicalization`

**Contract kind:** `canonical_boolean`

**Contract factory:** `Boolean()`

## What It Does

The boolean capability rewrites a string into a single canonical form. The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Boolean(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Evidence Rules

| Rule | Citation |
|---|---|
| `not_a_boolean_contract` | (dispatch invariant) |\n| `not_a_string_value` | (dispatch invariant) |\n| `trimmed_whitespace` | paxman spec/boolean §3.2 (ASCII whitespace trim) |\n| `matched_boolean_token` | paxman spec/boolean §3.2 (token -> canonical) |\n| `missing_value` | paxman spec/boolean §3.3 (Law 8 — required value absent) |\n| `policy_disabled_token` | paxman spec/boolean §3.2 + §3.3 (contract policy disables token) |\n| `unrecognized_token` | paxman spec/boolean §3.3 (input matched no boolean grammar) |

## Recognition Layer 1

Before any rewriting, the capability runs `grammar.recognize` over the input. Recognition assigns **no meaning** — it returns only raw captures. The resolver then assigns meaning to the captures and maps the survivors to a `Status`.

## Status Outcomes

- **CANONICALIZED:** The input was successfully matched and canonicalized.
- **INVALID:** The input was rejected due to an unrecognized format or policy restriction.
- **MISSING:** The input was empty or purely whitespace.
- **AMBIGUOUS:** (where applicable) The input could not be definitively resolved.
- **UNSUPPORTED:** (where applicable) The input format is known but explicitly not supported.

## Quickstart

```python
import paxman
from paxman import Boolean, Status

result = paxman.canonicalize("example_input", Boolean())
```

## References

- **Source Module:** [`src/paxman/_capabilities/boolean`](../../../src/paxman/_capabilities/boolean)
- **Contracts Reference:** [Contracts](../../reference/contracts.md)

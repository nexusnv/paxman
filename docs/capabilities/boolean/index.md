# Boolean Capability

The boolean capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings that represent boolean values (true/false) into a single canonical form. It accepts a wide vocabulary of boolean tokens, including numeric `1`/`0`, word forms (`yes`/`no`/`on`/`off`/`enabled`/`disabled`), and single-letter abbreviations (`t`/`f`/`y`/`n`). The capability is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `boolean_canonicalization`

**Contract kind:** `canonical_boolean`

**Contract factory:** `Boolean()`

## What It Does

The boolean capability rewrites a string into a single canonical boolean form: the lowercase strings `"true"` or `"false"`. It does not interpret or score inputs. Each token maps deterministically to one canonical value; inputs that match no boolean grammar are rejected with `Status.INVALID`.

The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Boolean(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

### Accepted Tokens

With the default contract (`accept_numeric=True`, `accept_words=True`, `case_sensitive=False`), the capability accepts:

| Canonical `"true"` tokens | Canonical `"false"` tokens |
|---|---|
| `true`, `t`, `yes`, `y`, `on`, `enabled`, `1` | `false`, `f`, `no`, `n`, `off`, `disabled`, `0` |

Matching is case-insensitive by default (`case_sensitive=False`). Already-canonical inputs (`"true"` / `"false"`) are always accepted, even when `accept_numeric` or `accept_words` is `False`, preserving idempotence (mandate Law 2).

## The Contract Fields

Every field is a policy declaration. There is no auto-detection; the contract declares what canonical means, and the capability applies it.

| Field | Type | Default | What it does |
|---|---|---|---|
| `accept_numeric` | `bool` | `True` | Accept `"1"` as true and `"0"` as false. When `False`, numeric tokens are rejected with `policy_disabled_token`. |
| `accept_words` | `bool` | `True` | Accept word forms (`yes`/`no`/`y`/`n`/`on`/`off`/`enabled`/`disabled`). When `False`, word tokens are rejected with `policy_disabled_token`. |
| `case_sensitive` | `bool` | `False` | When `True`, tokens must match exactly (e.g. only `"True"` not `"TRUE"`). When `False`, matching is case-insensitive. |
| `output_format` | `"truefalse"` | `"truefalse"` | The canonical output form. Only `"truefalse"` is supported in v2.0.0. |

The `kind` and `version` fields are fixed (`"canonical_boolean"` and `1` respectively). They are not part of the `Boolean()` factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Transforming Rules (Fire on Success)

These rules rewrite the input into the canonical form. They are recorded on the artifact in execution order.

| Rule | When it fires | Citation |
|---|---|---|
| `trimmed_whitespace` | Leading or trailing ASCII whitespace was removed from the input. | Paxman spec/boolean section 3.2 (ASCII whitespace trim) |
| `matched_boolean_token` | The input matched a boolean grammar and was mapped to its canonical form. The detail includes the mapping (e.g. `"yes" -> "true"`). | Paxman spec/boolean section 3.2 (token to canonical) |

### Rejecting Rules (Fire on Rejection)

These rules cause the capability to return `Status.INVALID` with a single evidence entry. The string is *not* canonicalized; the artifact holds no `value`.

| Rule | When it fires | Citation |
|---|---|---|
| `not_a_boolean_contract` | The contract is not a `CanonicalBooleanContract`. (Defensive; the orchestrator normally routes boolean contracts to this capability.) | (dispatch invariant) |
| `not_a_string_value` | The value is not a `str`. | (dispatch invariant) |
| `missing_value` | The value is `None` or whitespace-only. | Paxman spec/boolean section 3.3 (Law 8: required value absent) |
| `unrecognized_token` | The input did not match any boolean grammar (not a recognized token). | Paxman spec/boolean section 3.3 (input matched no boolean grammar) |
| `policy_disabled_token` | The input matched a token that the contract policy disables (e.g. numeric token with `accept_numeric=False`, or word token with `accept_words=False`). | Paxman spec/boolean section 3.2 + section 3.3 (contract policy disables token) |

## Worked Examples

### Example 1: A Normal Boolean

```python
import paxman
from paxman import Boolean, Status

result = paxman.canonicalize("YES", Boolean())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"true"`
- `result.evidence` includes `Evidence(rule="matched_boolean_token", detail="'yes' -> 'true'", ...)`

### Example 2: Numeric Token with Policy

```python
result = paxman.canonicalize("1", Boolean(accept_numeric=True))
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"true"`
- `result.evidence` includes `Evidence(rule="matched_boolean_token", detail="'1' -> 'true'", ...)`

### Example 3: Policy Rejection

```python
result = paxman.canonicalize("1", Boolean(accept_numeric=False))
```

- `result.status` is `Status.INVALID`
- `result.value` is `None`
- `result.evidence` is `(Evidence(rule="policy_disabled_token", ...),)`

## Limitations of v2.0.0

The v2.0.0 boolean capability is intentionally narrow. It does not accept:

- Multi-word expressions (`"of course"`, `"absolutely not"`).
- Numeric values other than `"1"` and `"0"` (e.g. `"2"`, `"42"`).
- Localized boolean tokens (`"ja"`/`"nein"`, `"oui"`/`"non"`).
- Null/nil/undefined as boolean values (these route to `Status.MISSING`).

Future v2.x versions may add localized token support. The contract `version` is part of the artifact's `VersionStamp`; expanding the vocabulary is a contract-version bump.

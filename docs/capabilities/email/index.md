# Email Capability

The email capability is the only built-in capability shipped with Paxman v2.0.0. It canonicalizes strings that represent email addresses.

**Capability name:** `email_canonicalization`

**Contract kind:** `canonical_email`

**Contract factory:** `Email()`

## What It Does

The email capability rewrites a string into a single canonical email form. It does not interpret — it only rewrites representations of *known* email addresses into the chosen form.

The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Email(...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Contract Fields

Every field is a policy declaration. There is no auto-detection; the contract declares what canonical means, and the capability applies it.

| Field | Type | Default | What it does |
|---|---|---|---|
| `lowercase` | `bool` | `True` | Lowercase the local part and the domain. |
| `strip_whitespace` | `bool` | `True` | Strip leading and trailing ASCII whitespace. |
| `provider_aliases` | `"none"` or `"gmail"` | `"none"` | Apply a specific provider's documented alias rules. Only `"gmail"` is supported in v2.0.0. |
| `strict` | `bool` | `False` | Reject inputs with embedded whitespace or non-ASCII characters before any rewriting. |

The `kind` and `version` fields are fixed (`"canonical_email"` and `1` respectively). They are not part of the `Email()` factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Transforming Rules (Fire on Success)

These rules rewrite the input into the canonical form. They are recorded on the artifact in execution order.

| Rule | When it fires | Citation |
|---|---|---|
| `stripped_whitespace` | `strip_whitespace=True` and leading/trailing ASCII whitespace was removed. | RFC 5322 §2.1 + §3.6.3 |
| `lowercased_local_part` | `lowercase=True` and the local part contained uppercase characters. | Paxman spec/email §1.3 |
| `lowercased_domain` | `lowercase=True` and the domain contained uppercase characters. | RFC 5321 §2.4 |
| `domain_synonym_gmail` | `provider_aliases="gmail"` and the domain was `googlemail.com`. | Google Help: "Use aliases on your Account" |
| `stripped_dots_in_local_part` | `provider_aliases="gmail"` and dots in the local part were removed. | Google Help: dots don't matter in Gmail addresses |
| `stripped_plus_tag` | `provider_aliases="gmail"` and a `+tag` suffix was stripped from the local part. | Google Help: Gmail +alias addressing |

### Rejecting Rules (Fire on Rejection)

These rules cause the capability to return `Status.INVALID` with a single evidence entry. The string is *not* canonicalized; the artifact holds no `value`.

| Rule | When it fires | Citation |
|---|---|---|
| `not_an_email_contract` | The contract is not a `CanonicalEmailContract`. (Defensive; the orchestrator normally routes email contracts to this capability.) | (dispatch invariant) |
| `not_a_string_value` | The value is not a `str`. | (dispatch invariant) |
| `strict_rejected_whitespace` | `strict=True` and the value contains spaces, tabs, or newlines. | Paxman spec/email §1.5 |
| `strict_rejected_non_ascii` | `strict=True` and the value contains non-ASCII characters. | Paxman spec/email §1.5 |
| `missing_at_sign` | The value does not contain `@`. | RFC 5322 §3.6 |
| `empty_local_or_domain` | The local part or domain is empty. | RFC 5322 §3.6 |
| `grammar_rejected` | After all rewrites, the result fails RFC 5322 §3.2.3 dot-atom (local part) or RFC 5321 §3.4 / RFC 1035 §2.3.1 (domain) grammar. | RFC 5322 §3.2.3 + RFC 5321 §3.4 + RFC 1035 §2.3.1 |

Two of the rejecting rules — `not_an_email_contract` and `not_a_string_value` — have empty citations. They are dispatch invariants: they describe a routing failure, not a canonical-form rule. The remaining rejecting rules all cite a specification.

## The Grammar Gate

After all rewrites, the capability checks the result against the RFC grammar. Inputs that fail the gate return `Status.INVALID` with a `grammar_rejected` evidence entry.

The local part must match RFC 5322 §3.2.3 `dot-atom`:

- A run of `atext` characters, optionally separated by single dots.
- No leading dot, no trailing dot, no consecutive dots.
- The `atext` set is the RFC's ASCII atom-text class — letters, digits, and `!#$%&'*+-/=?^_` followed by a literal backtick and `{|}~`.
- Quoted-string local parts (`"foo"@example.com`) are not accepted in v2.0.0.

The domain must match RFC 5321 §3.4 + RFC 1035 §2.3.1:

- One or more labels separated by single dots.
- Each label is 1–63 characters, starts and ends with a letter or digit, interior characters may be letters, digits, or hyphens.
- Total domain length is at most 253 characters.
- Bracketed domain-literals (`user@[127.0.0.1]`, `user@[IPv6:::1]`) are not accepted in v2.0.0.

Single-label domains like `user@localhost` are accepted under the v2.0.0 grammar gate.

## Worked Examples

### Example 1: A Normal Email

```python
import paxman
from paxman import Email, Status

result = paxman.canonicalize("User@Example.com", Email())
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"user@example.com"`
- `result.evidence` is `(Evidence(rule="lowercased_local_part", ...), Evidence(rule="lowercased_domain", ...))`

### Example 2: Gmail Aliases

```python
result = paxman.canonicalize(
    "  John.Doe+Work@GoogleMail.COM  ",
    Email(provider_aliases="gmail"),
)
```

- `result.status` is `Status.CANONICALIZED`
- `result.value` is `"johndoe@gmail.com"`
- `result.evidence` has six entries, in order: `stripped_whitespace`, `lowercased_local_part`, `lowercased_domain`, `domain_synonym_gmail`, `stripped_dots_in_local_part`, `stripped_plus_tag`

### Example 3: Strict Rejection

```python
result = paxman.canonicalize(
    "user with space@example.com",
    Email(strict=True),
)
```

- `result.status` is `Status.INVALID`
- `result.value` is `None`
- `result.evidence` is `(Evidence(rule="strict_rejected_whitespace", ...),)`

### Example 4: Grammar Rejection

```python
result = paxman.canonicalize("user@-bad.com", Email())
```

- `result.status` is `Status.INVALID`
- `result.value` is `None`
- `result.evidence` includes `Evidence(rule="grammar_rejected", ...)`

## Limitations of v2.0.0

The v2.0.0 email capability is intentionally narrow. It does not accept:

- Quoted-string local parts (`"foo bar"@example.com`).
- Bracketed IPv4 domain-literals (`user@[127.0.0.1]`).
- Bracketed IPv6 domain-literals (`user@[IPv6:::1]`).
- Internationalized email addresses (the `strict=True` policy rejects non-ASCII; `strict=False` accepts only ASCII content).

Future v2.x versions may extend the grammar gate. The contract `version` is part of the artifact's `VersionStamp`; upgrading the grammar is a contract-version bump that will be visible on every new artifact.

See the [changelog](changelog.md) for the history of grammar changes.

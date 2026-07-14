# Status and Evidence

Every `paxman.canonicalize()` call returns an `ExecutionArtifact`. The artifact has a `status` (one of five values) and a list of `evidence` entries. This page explains both.

## The Five Outcomes

`Status` is an enum with five values. They are mutually exclusive; an artifact has exactly one.

| Status | Meaning | Is `value` set? |
|---|---|---|
| `CANONICALIZED` | The capability produced a canonical form. | Yes — the canonical value. |
| `INVALID` | The input cannot satisfy the contract (e.g. malformed grammar, strict-mode rejection). | No — `None`. |
| `MISSING` | The contract requires information the input does not provide. | No — `None`. |
| `AMBIGUOUS` | More than one capability claimed the `(contract, value)` pair. Paxman refuses to pick one. | No — `None`. |
| `UNSUPPORTED` | No registered capability declared it canonicalizes this `(contract, value)` pair, or the contract's `kind` is not recognized. | No — `None`. |

These are **outcomes**, not exceptions. A canonicalize call that returns an artifact with `Status.INVALID` did not fail; it succeeded in reporting that the input was invalid. You handle each outcome in your code.

For the distinction between outcomes and exceptions, see the [Error reference](../reference/errors.md). The short version: outcomes are returned on the artifact; exceptions are raised only when the call cannot proceed at all (broken contract, version mismatch, internal invariant violation, frozen registry after first use).

## Reading the Status

```python
import paxman
from paxman import Email, Status

result = paxman.canonicalize("User@Example.com", Email())
assert result.status is Status.CANONICALIZED
print(result.value)  # "user@example.com"
```

`result.status` is a `Status` enum. Compare with `is` (or `==`). The five values are `Status.CANONICALIZED`, `Status.INVALID`, `Status.MISSING`, `Status.AMBIGUOUS`, and `Status.UNSUPPORTED`.

## The Evidence List

The artifact's `evidence` field is a tuple of `Evidence` entries. Each entry has three fields:

| Field | Type | What it is |
|---|---|---|
| `rule` | `str` | A machine-readable rule name. For the email capability, examples are `stripped_whitespace`, `lowercased_domain`, `grammar_rejected`, `domain_synonym_gmail`. |
| `detail` | `str` | A human-readable description of what the rule did. May be empty. |
| `provenance` | `str` | A citation: the source of the rule. For Paxman v2.0.0, this is an RFC section, a Google Help article (for Gmail's rules), or a Paxman policy declaration. See [Why rules cite sources](why-rules-cite-sources.md). |

The evidence list is ordered: rules are appended in the order they fired. A `CANONICALIZED` artifact's evidence tells you the sequence of transformations the capability applied. An `INVALID` artifact's evidence tells you which rule caused the rejection.

## Why Evidence Instead of Numeric Scores

Some libraries report a numeric score — a value between 0 and 1 that says "how sure am I?" Paxman does not do this. Two reasons:

1. **A score is opinion, not fact.** Where did `0.91` come from? Can it change? Why `0.91` and not `0.75`? Once subjective judgment enters, the result is no longer fully determined by the inputs.
2. **Evidence is auditable.** A `rule` name and a `provenance` citation can be checked. A numeric score cannot. If a user disputes a canonical form, they can read the evidence, find the rule, look up the citation, and decide for themselves whether the rule applies.

This is why the artifact's `Status` is one of five discrete values, not a number. The library either canonicalized the input, or it reports *exactly why* it did not. There is no "sort of" outcome.

## A Worked Example

For the input `"  John.Doe+Work@GoogleMail.COM  "` under `Email(provider_aliases="gmail")`:

```python
result = paxman.canonicalize(
    "  John.Doe+Work@GoogleMail.COM  ",
    Email(provider_aliases="gmail"),
)
```

- `result.status` is `Status.CANONICALIZED`.
- `result.value` is `"johndoe@gmail.com"`.
- `result.evidence` has six entries, in order:
  1. `Evidence(rule="stripped_whitespace", detail="", provenance="RFC 5322 §2.1 + §3.6.3")`
  2. `Evidence(rule="lowercased_local_part", detail="", provenance="Paxman spec/email §1.3")`
  3. `Evidence(rule="lowercased_domain", detail="", provenance="RFC 5321 §2.4")`
  4. `Evidence(rule="domain_synonym_gmail", detail="googlemail.com -> gmail.com", provenance='Google Help: "Use aliases on your Account" (retrieved 2026-07-14)')`
  5. `Evidence(rule="stripped_dots_in_local_part", detail="", provenance="Google Help: dots don't matter in Gmail addresses")`
  6. `Evidence(rule="stripped_plus_tag", detail="", provenance="Google Help: Gmail +alias addressing")`

Six rules fired. Each one has a citation. If a user disputes the canonical form, they can read the evidence, find the rule, look up the citation, and decide whether the rule applies to their input.

For the input `"user with space@example.com"` under `Email(strict=True)`:

- `result.status` is `Status.INVALID`.
- `result.value` is `None`.
- `result.evidence` has one entry:
  1. `Evidence(rule="strict_rejected_whitespace", detail="", provenance="Paxman spec/email §1.5")`

One rule fired, the rejection rule, with a citation.

## The Full Rule Table for the Email Capability

The complete list of rules the email capability can emit, with what triggers them, is in the [Email capability spec](../capabilities/email/index.md#the-rules).

## Where to Go Next

- [Why rules cite sources](why-rules-cite-sources.md) — the citation policy in detail.
- [How-to: Interpret the five outcomes](../how-to/interpret-the-5-statuses.md) — the recommended if/elif pattern.
- [Reference: Status](../reference/api.md#status) — the full Status reference.

# Why rules cite sources

Every rule in a Paxman capability has a citation. The citation is part of the `Evidence` entry on the artifact. This page explains why.

## The rule

Every transformation or rejection that a capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` field.

The `provenance` field is non-empty for every rule except two dispatch invariants (`not_an_email_contract` and `not_a_string_value`, which describe a routing failure rather than a canonical-form rule). Every other rule cites one of three sources:

1. **An authoritative specification.** Examples: RFC 5322 §2.1, RFC 5321 §2.4, RFC 5322 §3.2.3, RFC 5321 §3.4, RFC 1035 §2.3.1.
2. **A documented platform behavior.** Examples: Google Help: "Use aliases on your Account" (retrieved 2026-07-14), Google Help: dots don't matter in Gmail addresses, Google Help: Gmail +alias addressing.
3. **A declared Paxman policy.** Examples: Paxman spec/email §1.3 (Paxman policy; diverges from RFC 5321 §2.4), Paxman spec/email §1.5 (strict-mode policy).

A rule whose source is none of these is, by construction, a rule invented because it "felt right." Paxman does not allow invented rules.

## Why this matters

Consider two capabilities, A and B, that both canonicalize the same input differently. Without citations, a user has no way to decide which one is right. With citations, the user can read each capability's evidence, find the rule, look up the citation, and decide for themselves.

For example, the email capability lowercases the local part of an email address, even though RFC 5321 §2.4 explicitly says local parts are case-sensitive. The rule is intentional, and the `provenance` field says so: it cites the Paxman policy document, not the RFC. A user who needs the RFC-strict behavior can build a different capability whose `lowercased_local_part` rule cites the RFC and produces a different result.

If the rule had no citation, the user would have to guess. The guess might be wrong. The wrong guess would propagate to every artifact produced under the wrong assumption.

## The three sources, in detail

### Authoritative specifications

These are documents published by a standards body, with a clear identifier. RFCs are the common case (RFC 5321, RFC 5322, RFC 1035, RFC 4122, ISO 4217, etc.). The citation is the document number and the section number:

- `RFC 5321 §2.4 (domain is case-insensitive)`
- `RFC 5322 §3.2.3 (dot-atom)`
- `RFC 1035 §2.3.1 (label rules)`

The library does not fetch the RFC at canonicalize time. The citation is a string on the artifact; the user can look it up out of band.

### Documented platform behavior

Some rules reflect how a real-world system (Gmail, Outlook, etc.) treats an input. These are not standards; they are observations. The citation records the platform, the document, the version (or retrieval date), and the relevant section.

- `Google Help: "Use aliases on your Account" (retrieved 2026-07-14)`
- `Google Help: dots don't matter in Gmail addresses (retrieved 2026-07-14)`
- `Google Help: Gmail +alias addressing (retrieved 2026-07-14)`

The retrieval date is part of the citation. If the platform updates the document, the citation on existing artifacts still points to the document as it was at retrieval. A new artifact that wants to cite the new behavior gets a new capability version and a new `capabilities_hash`.

### Declared Paxman policy

Sometimes the canonical form is a choice Paxman makes because no specification covers it. These choices are recorded in a Paxman document (the MANDATE, a capability spec, or another declared Paxman policy document) and cited by section:

- `Paxman spec/email §1.3 (Paxman policy; diverges from RFC 5321 §2.4)`
- `Paxman spec/email §1.5 (strict-mode policy)`

The Paxman spec is the source of truth for these decisions. If you disagree with a Paxman policy, the right response is to write a different capability with different rules — not to ask the existing capability to behave differently.

## What is not a citation

A rule whose `provenance` is one of the following is rejected:

- "I thought it made sense."
- "It works on most inputs."
- "Most users expect this."
- An empty string.
- A link to a tutorial, blog post, or Stack Overflow answer.
- A claim that the rule is "industry standard" without naming the document.

These are heuristics in disguise. The library does not have heuristics.

## The rule→citation manifest

Every capability maintains a manifest that maps rule names to citations. The manifest is the single source of truth. A rule with no manifest entry raises `KeyError` at the exact site where the rule is emitted. This makes "I forgot to cite a rule" a build error, not a documentation oversight.

For the email capability, the manifest is `_RULE_PROVENANCE` in the capability source. See the [Email capability spec](../capabilities/email/index.md) for the full rule table.

## How this affects you

- When you read an artifact, the evidence tells you exactly which rules fired and where each rule came from.
- When you write a new capability, every rule you add must cite one of the three sources. The manifest is the spec.
- When you read another library's output, you can compare its evidence against Paxman's to see where the two differ.

## Where to go next

- [Status and evidence](status-and-evidence.md) — the artifact fields the citations appear in.
- [How-to: Write a compliant capability](../how-to/write-a-compliant-capability.md) — the manifest is part of the contract for a new capability.
- [Email capability: the rules](../capabilities/email/index.md#the-rules) — the complete rule table for the shipped capability.

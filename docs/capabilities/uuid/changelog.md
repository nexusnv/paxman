# UUID capability — changelog

The UUID capability is versioned. Each entry below records a contract-version bump and what changed. The contract `version` field appears on every artifact, so any old artifact can be replayed against the rules that produced it.

## v1 (current — v2.0.0-rc1 release)

**Contract version:** `1`

**Capability name:** `uuid_canonicalization`

**Shipped:** v2.0.0-rc1

**What it does:**

- Accepts only the RFC 4122 §3 canonical form (36 lowercase hex chars, 8-4-4-4-12 grouping).
- Emits the same canonical form.
- Optional `version` filter (`"any"`, `"1"`, `"3"`, `"4"`, `"5"`, `"7"`) rejects other versions with `Status.INVALID` and a `version_mismatch` evidence rule.

**What it does not do (intentionally):**

- Does not accept 32-hex without hyphens.
- Does not accept the braced `{...}` form.
- Does not accept the URN `urn:uuid:...` form.
- Does not accept uppercase hex characters.
- Does not accept inputs with extra whitespace.

These are deferred to future versions.

**Citation policy:** Every rule in the capability cites either RFC 4122 (the canonical authority) or the Law 14 §3.6 dispatch-invariant allow-list. The complete rule→citation manifest is in the capability source. See the [UUID capability spec](index.md#the-rules) for the rule table.

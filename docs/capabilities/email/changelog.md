# Email Capability — Changelog

The email capability is versioned. Each entry below records a contract-version bump and what changed. The contract `version` field appears on every artifact, so any old artifact can be replayed against the rules that produced it.

## v1 (Current — v2.0.0 Release)

**Contract version:** `1`

**Capability name:** `email_canonicalization`

**Shipped:** v2.0.0

**What it does:**

- Strips leading and trailing ASCII whitespace (configurable via `strip_whitespace=True`).
- Lowercases the local part and the domain (configurable via `lowercase=True`).
- Applies Gmail's documented alias rules when `provider_aliases="gmail"`:
  - `googlemail.com` is normalized to `gmail.com`.
  - Dots in the local part are removed.
  - `+tag` suffixes in the local part are stripped.
- Rejects malformed inputs at the grammar gate (RFC 5322 §3.2.3 dot-atom local part + RFC 5321 §3.4 / RFC 1035 §2.3.1 domain).
- Provides a `strict` policy that rejects inputs with embedded whitespace or non-ASCII characters before any rewriting.

**What it does not do (intentionally):**

- Does not accept quoted-string local parts (`"foo"@example.com`).
- Does not accept bracketed IPv4 domain-literals (`user@[127.0.0.1]`).
- Does not accept bracketed IPv6 domain-literals (`user@[IPv6:::1]`).
- Does not handle internationalized email addresses (IDN).

These are deferred to future versions.

**Citation policy:** Every rule in the capability cites one of three sources — an RFC, a documented platform behavior (Google Help), or a Paxman policy. The complete rule-to-citation manifest is in the capability source. See the [Email capability spec](index.md#the-rules) for the rule table.

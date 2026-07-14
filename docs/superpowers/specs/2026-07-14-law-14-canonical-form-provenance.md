# Law 14 — Canonical Form Provenance: EmailCapability Recalibration

**Status:** Design spec — 1 of 1 (per user direction on 2026-07-14).
**Authority:** [`MANDATE.md`](../../../MANDATE.md) §7 Law 14. Where this
spec conflicts with MANDATE, MANDATE wins.
**Date:** 2026-07-14.
**Branch:** `feat/law-14-canonical-provenance`.

---

## 0. Scope

Adopt [Law 14](../../../MANDATE.md#law-14--canonical-forms-have-provenance)
into the codebase and recalibrate every shipped capability rule against
it. The exit criteria are:

1. Every `Evidence` entry carries a `provenance: str` field citing one of
   the three Law 14 authoritative sources (spec / documented platform
   behavior / declared Paxman policy). A rule with empty provenance is a
   violation and is rejected at code-review time (and surfaced at runtime
   via test assertions).
2. The EmailCapability passes a surface-grammar gate (RFC 5322 §3.2.3 +
   RFC 5321 §3.4 + RFC 1035 §2.3.1) before any rewriting. Malformed inputs
   that previously returned `Status.CANONICALIZED` (the user-experiment
   permissiveness cases) now return `Status.INVALID` with a
   `grammar_rejected` evidence rule citing RFC 5322 §3.2.3.
3. A new golden regression corpus (`test_email_law14_corp.py`) pins the
   expected `(Status, canonical value, set of evidence rule names)` for
   100+ emails, including the 9 permissiveness cases surfaced by the
   user experiment. Any drift blocks merge.

Out of scope:
- README / docs-site / batch API (the "first-time user experience" report's
  remaining items are deferred; this spec only addresses Law 14
  recalibration, not the docs follow-ups).
- Quoted-string local parts (`"user name"@example.com`) and bracketed
  domain literals (`user@[127.0.0.1]`, `user@[IPv6:...]`). These are
  RFC 5321/5322 legal but a deferred v2.x phase. The grammar gate rejects
  them with `grammar_rejected` for v2.0.0; an explicit comment records
  that they are v2.x additions, not Law 14 violations.
- New capability implementations. Only the shipped EmailCapability is in
  scope.

---

## 1. Why this spec exists

The user-experiment report (`paxman (updated)` first-time-user feedback,
2026-07-14) surfaced that the EmailCapability returned
`Status.CANONICALIZED` for nine malformed inputs:

| Input | Returned pre-Law 14 | Law 14 verdict |
|---|---|---|
| `user @example.com` | `CANONICALIZED` — space in local part | INVALID (grammar) |
| `user@ example.com` | `CANONICALIZED` — space in domain | INVALID (grammar) |
| `user..name@example.com` | `CANONICALIZED` — consecutive dots in local | INVALID (grammar) |
| `user@[127.0.0.300]` | `CANONICALIZED` — invalid IP octet | INVALID (grammar) — `[]` brackets are v2.x |
| `user@[127.0.0.1` | `CANONICALIZED` — unclosed bracket | INVALID (grammar) |
| `(comment)user@example.com` | `CANONICALIZED` — RFC comment syntax | INVALID (grammar) |
| `user@example.com/` | `CANONICALIZED` — trailing slash | INVALID (grammar) |
| `user@example.com@example.com` | `CANONICALIZED` — double `@` | INVALID (grammar) |
| `user@-domain.com` | `CANONICALIZED` — leading dash in domain | INVALID (grammar) |

Pre-Law 14, returning `CANONICALIZED` was *not* a violation of any of the
thirteen laws: the rule was deterministic, idempotent, pure, replayable,
and logged evidence. The thirteen laws described *how* Paxman behaves; none
described *where canonical forms come from*. Law 14 closes that gap. Every
rule now must cite one of three sources; "because I wrote it that way" is no
longer a citation, and silently accepting malformed input is, by
construction, canonical-form invention without provenance.

---

## 2. Rule-by-rule audit of `EmailCapability`

The current `EmailCapability` (file:
`src/paxman/_capabilities/builtins/email.py`) emits twelve evidence rules.
We audit each one against Law 14.

### 2.1 Rejection rules (Law 14 boundary — citations classify the rejection)

| Rule name | Pre-Law 14 | Law 14 provenance category | Citation | v2.0.0 action |
|---|---|---|---|---|
| `not_an_email_contract` | defensive dispatch | runtime invariant (not a canonical-form rule) | n/a (Mandate §5 SPI) | keep — provenance `""` allowed for dispatch invariants |
| `not_a_string_value` | defensive typecheck | runtime invariant | n/a | keep — provenance `""` allowed |
| `strict_rejected_whitespace` | strict-mode policy | declared Paxman policy | spec §1.5 / MANDATE Law 7 | keep — cite `paxman/spec/email §1.5` |
| `strict_rejected_non_ascii` | strict-mode policy | declared Paxman policy | spec §1.5 | keep |
| `missing_at_sign` | grammar rejection | authoritative spec | RFC 5322 §3.6 (mailbox = local-part "@" domain) | keep |
| `empty_local_or_domain` | grammar rejection | authoritative spec | RFC 5322 §3.6 | keep |
| `grammar_rejected` | **NEW** | authoritative spec | RFC 5322 §3.2.3 (atom / dot-atom) + RFC 5321 §3.4 (domain) + RFC 1035 §2.3.1 (label) | **add** |

### 2.2 Transforming rules (Law 14 binds these directly)

| Rule name | Pre-Law 14 | Law 14 provenance category | Citation | v2.0.0 action |
|---|---|---|---|---|
| `stripped_whitespace` | leading/trailing CFWS removal | authoritative spec | RFC 5322 §2.1 (line with leading/trailing CFWS) + §3.6.3 (CFWS) | keep |
| `lowercased_local_part` | lowercasing local part | **declared Paxman policy** | spec §1.3 (local part case-folding is a contract-declared convenience; RFC 5321 §2.4 says the local part is case-sensitive) | keep — but cite `paxman/spec/email §1.3` and document the policy divergence from RFC 5321 §2.4 |
| `lowercased_domain` | lowercasing domain | authoritative spec | RFC 5321 §2.4 (domain is case-insensitive) | keep |
| `domain_synonym_gmail` | gmail/googlemail collapse | documented platform behavior | Google Help: "Use aliases on your Account" (retrieved 2026-07-14) | keep |
| `stripped_dots_in_local_part` | Gmail dot-ignoring | documented platform behavior | Google Help: "Dots don't matter in Gmail addresses" (retrieved 2026-07-14) | keep |
| `stripped_plus_tag` | Gmail `+tag` removal | documented platform behavior | Google Help: "Add a '+' to your Gmail address" / "alias" (retrieved 2026-07-14) | keep |

### 2.3 The "silent CANONICALIZED" rule — to be removed

Pre-Law 14, the capability accepted any input containing exactly one `@`
with non-empty local and domain parts as `CANONICALIZED`, regardless of
whether the local / domain parts were RFC 5322-valid. In Law 14 terms, this
is a **canonical-form rule with no provenance** — it is silent invention.
This code path is now preceded by the `grammar_rejected` gate; the silent
CANONICALIZED path for malformed input is removed.

### 2.4 The `lowercased_local_part` policy divergence

`lowercased_local_part` is the most interesting Law 14 finding. RFC 5321
§2.4 says: "the local-part of a mailbox MUST BE treated as case sensitive."
The capability nonetheless lowercases the local part, because the
`CanonicalEmailContract.lowercase: bool = True` default declares a Paxman
policy that fold-cases *for matching convenience* across providers that
treat local parts case-insensitively in practice (Gmail, Yahoo).
Under Law 14, this is legal — it falls in category 3 (declared Paxman
policy) — but the divergence from RFC 5321 §2.4 is made explicit in the
provenance string and in the spec §1.3. The contract author can opt out via
`lowercase=False`; the capability does not infer.

The Law 14 fix here is documentation, not behavior: the rule's provenance
must record *which* of the three Law 14 sources it derives from, and the
spec §1.3 must record that the RFC and the policy disagree. The user
experiments' "I had to guess if paxman was correct" complaint is exactly
what surfacing this divergence fixes.

---

## 3. Implementation

### 3.1 Schema change: `Evidence.provenance`

```python
@attrs.frozen
class Evidence:
    rule: str
    detail: str = ""
    provenance: str = ""
```

The third field carries the Law 14 citation. Default `""` means "no
provenance cited" — a violation of Law 14 — surfaced by an audit test
(`test_no_empty_provenance_in_email_capability`) that greps the
`_RULE_PROVENANCE` manifest against the rule names fired by a curated
input set.

### 3.2 Replay-hash serialization change

`canonical_bytes()` is updated to include `provenance`:
```python
"evidence": [(e.rule, e.detail, e.provenance) for e in self.evidence]
```
This is a breaking change to the replay-hash byte layout — any artifact
serialized pre-Law 14 will fail `replay(...)` post-Law 14. This is
intentional and is the right behavior under Law 12: changing provenance
is a capability-version change; the hash records version-level
information. v2 has no pre-Law 14 production artifacts; there is no
migration problem in practice. A regression test asserts the new layout.

### 3.3 Provenance manifest — `_RULE_PROVENANCE`

A module-level constant in `email.py`:
```python
_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType({
    "not_an_email_contract": "",  # dispatch invariant — no canonical form rule
    "not_a_string_value": "",       # same
    "strict_rejected_whitespace": "paxman spec/email §1.5 (strict-mode policy)",
    "strict_rejected_non_ascii": "paxman spec/email §1.5 (strict-mode policy)",
    "missing_at_sign": "RFC 5322 §3.6 (mailbox = local-part \"@\" domain)",
    "empty_local_or_domain": "RFC 5322 §3.6",
    "grammar_rejected": "RFC 5322 §3.2.3 + RFC 5321 §3.4 + RFC 1035 §2.3.1",
    "stripped_whitespace": "RFC 5322 §2.1 + §3.6.3 (CFWS)",
    "lowercased_local_part": "paxman spec/email §1.3 (Paxman policy; diverges from RFC 5321 §2.4)",
    "lowercased_domain": "RFC 5321 §2.4 (domain is case-insensitive)",
    "domain_synonym_gmail": "Google Help: \"Use aliases on your Account\" (retrieved 2026-07-14)",
    "stripped_dots_in_local_part": "Google Help: dots don't matter in Gmail addresses (retrieved 2026-07-14)",
    "stripped_plus_tag": "Google Help: Gmail +alias addressing (retrieved 2026-07-14)",
})
```

Every `Evidence(...)` construction in the capability pulls its
provenance from this manifest by rule name. A new rule added without
a manifest entry is detected by a unit test that greps the capability
source for `rule="..."` literals and asserts every literal is keyed in
`_RULE_PROVENANCE` (the Law 14 manifestation of Mandate §10.2's reviewer
gate).

### 3.4 Surface-grammar gate — `grammar_rejected`

The local part is accepted iff it matches RFC 5322 §3.2.3 `dot-atom`:

```
atext = ALPHA / DIGIT / "!" / "#" / "$" / "%" / "&" / "'" / "*" /
        "+" / "-" / "/" / "=" / "?" / "^" / "_" / "`" / "{" /
        "|" / "}" / "~"
dot-atom = atext *("." atext)
```

Disallowed: empty, consecutive dots, leading/trailing dot, non-atext
characters (including internal whitespace, parentheses, slashes,
`@`, commas, semicolons). Quoted-string local parts are out of v2.0.0
scope and fail this gate with `grammar_rejected`.

The domain is accepted iff it matches RFC 5321 §3.4 dot-atom form:

```
sub-domain = Let-dig *Ldh-str
Ldh-str = Let-dig | "-"
Let-dig = ALPHA | DIGIT
dot-atom-domain = sub-domain *("." sub-domain)
```

Each label length ≤ 63 (RFC 1035 §2.3.1); no leading/trailing hyphen;
no consecutive dots; total length ≤ 253. Bracketed literals (`[127.0.0.1]`,
`[IPv6:...]`) are out of v2.0.0 scope and fail with `grammar_rejected`.

Two `@` symbols in the input (e.g. `user@example.com@example.com`) are
caught by the `local.partition("@")` step — `domain` will contain `@`,
which fails the dot-atom-domain gate.

### 3.5 Where the grammar gate sits in the pipeline

Pre-Law 14 pipeline:
1. Strict check (whitespace / ASCII).
2. `@` presence check.
3. Empty local/domain check.
4. Rewrite (strip, lowercase, gmail).
5. Return.

Post-Law 14 pipeline:
1. Strict check (whitespace / ASCII).
2. `@` presence check.
3. Empty local/domain check.
4. **NEW**: grammar gate (RFC 5322 dot-atom local + RFC 1035 dot-atom
   domain). On failure: `Status.INVALID`, `grammar_rejected` evidence.
5. Rewrite (strip, lowercase, gmail).
6. **NEW**: post-rewrite grammar re-check (stripping could empty the
   local part — already detected; stripping dots in a quoted-string
   local part would break grammar, but `provider_aliases="gmail"` only
   fires on a real gmail domain, where the local part was already
   dot-atom — already covered).
7. Return.

Idempotence is preserved: re-canonicalizing a *canonical* dot-atom email
passes the grammar gate trivially (it's already dot-atom).

### 3.6 Empty-provenance allow-list

`not_an_email_contract` and `not_a_string_value` are dispatch
invariants (Law 5 SPI), not canonical-form rules. Their `provenance`
defaults to `""` because they do not define a canonical form; they
describe a routing failure inside the capability. The audit test
explicitly allowlists these two rule names with empty provenance and
fails on any *other* empty-provenance rule.

---

## 4. Public-API impact

| Surface element | Change |
|---|---|
| `paxman.__all__` | unchanged (no new public symbols) |
| `paxman.api.types.__all__` | n/a in this repo state |
| `Evidence` dataclass | +1 field (`provenance: str = ""`) |
| `Status` enum | unchanged |
| `Email()` factory signature | unchanged |
| `CanonicalEmailContract` shape | unchanged |
| `canonicalize()` / `replay()` signatures | unchanged |
| `replay_hash` byte layout | changes (evidence triple instead of pair) |
| `_RULE_PROVENANCE` constant | new (internal to `email.py`) |
| publication snapshot | regenerated |

The exact-set public surface test (`test_public_api.py`) continues to
pass: no new symbols are added; the `Evidence` dataclass field count is
not part of the public-symbol assertion.

---

## 5. Test plan

### 5.1 Unit tests — extend `tests/unit/test_email_capability.py`

- `test_evidence_carries_provenance_citation`: every Evidence entry on a
  CANONICALIZED or INVALID artifact has a non-empty `provenance` (except
  the two dispatch-invariant rules).
- `test_grammar_rejects_internal_whitespace_in_local_part`.
- `test_grammar_rejects_whitespace_in_domain`.
- `test_grammar_rejects_consecutive_dots_in_local_part`.
- `test_grammar_rejects_bracketed_domain_literal_v1_scope`.
- `test_grammar_rejects_unclosed_bracket`.
- `test_grammar_rejects_parenthesized_comment`.
- `test_grammar_rejects_trailing_slash_in_domain`.
- `test_grammar_rejects_double_at_sign`.
- `test_grammar_rejects_leading_dash_in_domain`.
- `test_grammar_rejects_invalid_ip_octet`.
- `test_grammar_rejects_non_atext_in_local_part`.
- `test_grammar_rejects_quoted_string_local_part_v1_scope`.
- `test_rule_provenance_manifest_has_entry_for_every_rule_literal`: the
  audit test described in §3.3.

### 5.2 New integration test — `tests/integration/test_email_law14_corp.py`

The golden regression corpus. 100+ emails, each with pinned:

```python
EmailCorpusEntry(
    input_email: str,
    contract_kwargs: dict[str, object],
    expected_status: Status,
    expected_value: str | None,
    expected_evidence_rules: frozenset[str],
)
```

Construction:
- Reuse the 95 canonicalizable inputs from `test_five_minute_100_emails.py`
  (all valid dot-atom @ dot-atom forms → still CANONICALIZED, exact
  values pinned).
- Reuse the 5 invalid inputs (still INVALID).
- Add the 9 user-experiment permissiveness cases (now INVALID under
  `grammar_rejected`).
- Add ~30 additional grammar-boundary cases: valid quoted-string local
  parts (rejected under v2.0.0 grammar gate, pending v2.x), valid
  IP-literal domains (rejected under v2.0.0 grammar gate, pending v2.x),
  domains with leading hyphens, single-label domains (localhost),
  overlong label (64+ chars), unicode local part chars, etc.

Each entry asserts status, value, and evidence rule set. The test
fails on *any* drift, not just status.

### 5.3 Property tests — schedule re-check

The existing Hypothesis property tests
(`test_replay_invariant.py`, `test_idempotence_invariant.py`,
`test_canonicalization_invariant.py`) are unaffected in shape:

- Idempotence: the test skips the second `canonicalize` when the first
  returns non-`CANONICALIZED`. Tightening the gate means more inputs skip
  the second call; the property is preserved.
- Replay byte-equality: the test compares `art == rehydrated` and
  `canonical_bytes()` equality; both sides see the same (rule, detail,
  provenance) triple, so byte equality still holds.
- Replay-hash matches `sha256(canonical_bytes())`: the test recomputes
  the hash from `canonical_bytes()` and compares it to the stored hash;
  updating `canonical_bytes()` to include provenance is a synchronized
  change; the property is preserved.

### 5.4 Audit gate test — `test_no_empty_provenance_in_email_capability`

A unit test that runs the canonicalize pipeline on a curated input
covering every rule in the manifest and asserts every Evidence entry has
non-empty `provenance` *except* the two allow-listed dispatch invariants
(`not_an_email_contract`, `not_a_string_value`).

This test makes Law 14 machine-checkable at the unit level: a contributor
who adds a rule and forgets the manifest entry fails CI.

---

## 6. Out-of-scope follow-ups recorded for the backlog

These are *not* part of Law 14 recalibration but are surfaced by the audit;
filing in the v2 backlog:

1. Quoted-string local parts (`RFC 5322 §3.2.4`) — currently grammar-rejected
   under `grammar_rejected`; needs its own capability work in v2.x. Manifest
   entry when landed.
2. Bracketed domain literals (`RFC 5321 §3.4.1` IPv4 / RFC §3.4.2 IPv6).
   Currently grammar-rejected. Same as above.
3. Internationalized email (`RFC 6530`/`6531`) — non-ASCII in local part or
   domain continues to be grammar-rejected. Resolution tied to SMTPUTF8
   support design.
4. README "Status Reference" + "Email defaults" + "no batch API" docs
   gaps surfaced by the user-experiment report — explicitly deferred per
   user direction.
5. `canonicalize_many` batch API — explicitly deferred (probably never
   shipped, per user direction).

---

## 7. Exit verification

Before this spec is considered "delivered":

1. `uv run pytest -q` exits 0 across unit, property, integration.
2. The new `test_email_law14_corp.py` passes (golden regression).
3. The new `test_no_empty_provenance_in_email_capability` passes.
4. `mypy --strict`, `pyright`, lint, interrogate (100% docstring),
   bandit all clean on changed files.
5. The retired-vocabulary grep (§6.3 / `.coderabbit.yaml`) returns zero
   matches across `src/paxman/`.
6. Manual run of the README quickstart:
   `paxman.canonicalize("  John.Doe@Gmail.COM  ", Email(provider_aliases="gmail"))`
   continues to return `johndoe@gmail.com` with the same evidence rule
   set as before.
7. The MANDATE.md update is merged (Law 14 in §7, audit reference in
   §11).
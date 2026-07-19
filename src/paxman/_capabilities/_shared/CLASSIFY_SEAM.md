# The `classify` / `_Candidate` / `_Survivor` Seam

This document records a **deliberate architectural decision**: the
`classify(...)` function and the `_Candidate` / `_Survivor` value types inside
each capability canonicalizer are **domain-local by design**. They are NOT a
shared scaffold and must NOT be lifted into `_shared.classify` or a generic
`_shared.Candidate` / `_shared.Survivor` type.

## Why this is intentional (not duplication to be removed)

A prior plan (Candidate 1B) proposed centralizing the 4-stage
`classify` / `_Candidate` / `_Survivor` ladder into a single `_shared.classify`
module. On audit that premise was found to be **wrong**, for two independent
reasons:

### 1. The field sets are incompatible

There is no common generic type. Each domain's `_Candidate` / `_Survivor`
carry domain-specific fields that the others do not share. Forcing one would
create a lowest-common-denominator union type that none of them actually
satisfy — the exact "shared module grows domain cruft" anti-pattern that
`CODING_GUIDELINES.md` §10 warns against.

| Domain | `_Candidate` fields | `_Survivor` fields | `classify()` return type |
| --- | --- | --- | --- |
| email | `value, rule, source, evidence` | `value, rule, source, evidence` | `tuple[Status, str \| None, tuple[Evidence, ...], tuple[str, ...] \| None]` |
| uuid | `value, rule, source, evidence` | `value, rule, source, evidence` | same |
| boolean | `value, token, rule, source, evidence` | `value, rule, source, evidence` | same |
| country | `value, rule, evidence` | `value, rule, evidence` | same |
| date | `year, yy, month, day, century_ambiguous, rule, ordering, weekday` | `year, month, day, rule, ordering, century_ambiguous` | same |
| ip | `value, family, rule, source, evidence` | `value, rule, source, evidence` | same |
| phone | `value, rule, source, evidence` | `value, rule, source, evidence` | same |
| url | `value, rule, source, evidence` | `value, evidence` | same (extra `contract` param) |
| geolocation | `value, rule, source, evidence` | *(none — uses `_Candidate` directly)* | same (different params: `rep, candidates, contract`) |

Note the divergence is not cosmetic: `date` carries calendar-specific fields
(`year`, `month`, `day`, `ordering`, `century_ambiguous`); `boolean` carries a
`token`; `ip` carries a `family`; `url`'s `_Survivor` drops `rule`/`source`;
`geolocation` has no `_Survivor` at all. A single shared type would have to
accommodate all of these, which is precisely the cruft the shared seam exists
to avoid.

### 2. The `Status.AMBIGUOUS` branch is live (Don't-Guess)

The plan also claimed that some domains (e.g. uuid / boolean) carry a "dead
AMBIGUOUS branch" that could be deleted. This is **false**. `Status.AMBIGUOUS`
is genuinely reached in every domain — it is the "Don't Guess → surface
ambiguity" outcome required by the MANDATE (Law 3). Deleting it would break the
Don't-Guess invariant. The branch stays.

Confirmed `Status.AMBIGUOUS` reach sites:

- `boolean/canonicalizer.py:144`
- `country/canonicalizer.py:202`
- `date/canonicalizer.py:529, 677, 728, 778`
- `email/canonicalizer.py:307`
- `geolocation/canonicalizer.py:323`
- `ip/canonicalizer.py:147`
- `phone/canonicalizer.py:159`
- `url/canonicalizer.py:332`
- `uuid/canonicalizer.py:168`

## On "shared-looking" helper logic

Some survivor-handling loops *look* similar across domains (e.g. the
value-de-duplication loop `seen`/`survivor.value not in seen` in email and
phone; the AMBIGUOUS evidence-merge loop in email/uuid/ip/boolean/country).
These are **not** a shared scaffold: they operate on domain-specific
`_Survivor` shapes and sit inside domain-specific control flow (drop-reason
handling, `ordering`/`century_ambiguous` checks for date, `family` policy for
ip, etc.). They are small, local, and intentionally duplicated. Do not extract
them into `_shared`.

## Relationship to CODING_GUIDELINES.md §10

This matches the project's documented policy: `_shared` is the intentional
recognition seam for *truly* common logic (grammar/evidence/contract helpers).
`classify` / `_Candidate` / `_Survivor` are **intentional escapes** from that
seam — domains whose shapes are incompatible and whose ambiguity handling is
live. They are not a gap to be closed.

## Future guidance

If a *future* domain's `_Candidate` / `_Survivor` happens to share email's
exact `(value, rule, source, evidence)` shape, it **may** reuse email's types
by import (`from paxman._capabilities.email.canonicalizer import _Candidate,
_Survivor`). It should still keep its own `classify(...)` — do NOT presume a
shared `_shared.classify` exists or should exist.

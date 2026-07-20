# Paxman Refactor Architecture — Proposal (revised through Oracle cycles 1–4)

- **Date:** 2026-07-20
- **Status:** Proposed (revised through 4 Oracle review cycles)
- **Scope:** Recognition/resolution/classification pipeline restructuring only.
  Public API (`paxman.canonicalize`, `replay`, contracts) and the three
  invariants (Identity, Determinism, Replay) are OUT of scope and unchanged.
- **Guiding principle:** *The engine owns the algorithm; the contract owns the
  policy.* Capabilities supply domain rules; the engine owns the common pipeline.

---

## 1. Context — what the current code actually shows

Pipeline review of `src/paxman/_capabilities/` confirms three recognition paths:

```
Regex pipeline (8 domains):  input → anchored regex → fullmatch → resolver → classify → result
Date pipeline:               TWO-TIER. Direct-return tier: input → deterministic predicate
                             (Unix epoch / ISO date / ISO datetime / naive datetime / US|EU
                             numeric / RFC 2822) → CapabilityResult returned inline from
                             canonicalize (date/canonicalizer.py:608–777). Enumeration tier:
                             only the text-month + numeric-slash forms that match no direct
                             predicate route to generate_interpretations → resolve_and_validate
                             → date.classify (date/canonicalizer.py:788–794).
Money pipeline:              input → procedural parse → MoneyParts → (inline compose) → result
```

**Date is NOT a `classify`-skeleton domain.** Its INVALID evidence is selected
*inline* by specific failure reasons (`invalid_epoch_value`, `invalid_calendar_date`,
`rejected_two_digit_year`, `invalid_iso_format`, `unrecognized_format`, …) at the
point of failure — not by a survivor→status skeleton. Only the enumeration tier
(`:788–794`) calls `classify`, and that path is the near-uniform resolver shape.
`CODING_GUIDELINES §10` documents date's per-language `RecognizedRep` as an
intentional escape; this proposal does NOT migrate date onto the shared recognizer.

Verified facts (cycle 1–3 confirmed):

- `_shared/grammar.py` centralizes the recognition loop for 8 domains. Date and
  Money do **not** use it. Date is an *intentional escape* (its own per-language
  `RecognizedRep`), documented in `CODING_GUIDELINES §10` — out of scope for
  migration.
- **9 domains** define a local `classify(...)`. NOT uniform:
  - `geolocation.classify` (`:284`) enumerates hemisphere AMBIGUOUS (`:304–336`)
    on **empty `candidates`** (needs `rep` + `contract`), has no `_Survivor`.
  - `email.classify` (`:276`) distinguishes TWO invalid cases: `not candidates`
    → `unrecognized_format` (`:299`), `not survivors` → `grammar_rejected`
    (`:302`); de-dups survivors BEFORE the `len==1` check (`:291–297`).
  - The other 7 (boolean, country, uuid, ip, phone, url, and date's enumeration
    tier) are closer to uniform. Note uuid's `>1` branch is dead (uuid's
    `classify` only ever sees 0 or 1 survivor — the structurally-present AMBIGUOUS
    branch is at uuid/canonicalizer.py:166–179, matching CLASSIFY_SEAM.md:61), so
    uuid is effectively Single-resolution; it is still migrated for consistency,
    not for AMBIGUOUS.
- `_shared/CLASSIFY_SEAM.md` — existing audited decision: domain-local
  `_Candidate`/`_Survivor` types must NOT become a lowest-common-denominator
  `_shared` union type (field sets diverge; geolocation has **no `_Survivor`**).
  `Status.AMBIGUOUS` is live in all 9 (Don't-Guess).
- **`_core/classification.py:24` already exists**: `classify(capability_result,
  validation) -> Status` — the post-validation status override. Distinct from
  the resolver classify. Reconciled, not duplicated.
- Money's `recognize_money` (`grammar.py:258`) **raises `ContractError`** and
  carries a `canonical` idempotency flag (`:254`).

**Conclusion:** The shared part is the *pure status decision over survivors*.
The *candidates-vs-survivors distinction* (email's two INVALID rules) and
*domain AMBIGUOUS enumeration* (geolocation) are domain-specific. All three are
preserved.

---

## 2. The two orthogonal axes

| Axis | Values |
|---|---|
| **Recognition Strategy** | `Regex` (static anchored), `Grammar` (DSL-compiled), `Parser` (procedural) |
| **Resolution Strategy** | `Single` (≤1 interpretation), `Enumerated` (N → disambiguate) |
| **Capability (domain)** | email, phone, uuid, ip, url, country, geolocation, boolean, date, money |

---

## 3. Target architecture (final)

### 3.1 Stages — engine-owned vs domain-owned, in correct order

```
Input
  │
  ▼
[RECOGNIZE]   ENGINE-OWNED strategy: Regex | Grammar | Parser
  │  emits RecognizedRep(s)
  ▼
[RESOLVE]     DOMAIN-OWNED: captures → Candidate(s) → Survivor(s)
  │  (generate_interpretations + resolve_and_validate, domain rules)
  ▼
[POST-RESOLVE]  DOMAIN HOOK (OPTIONAL, runs BEFORE decide): de-dup / domain
  │  AMBIGUOUS enumeration. Receives the resolver's full output
  │  (rep, candidates, survivors, drop_reasons, contract). MUST call decide()
  │  internally — never returns a raw 4-tuple, never re-implements the skeleton.
  ▼
[DECIDE]      ENGINE-OWNED PURE PRIMITIVE (_core/classify.py): survivors → status
  ▼
[RENDER]      DOMAIN-OWNED (inline): Survivor → canonical string + Evidence
  ▼
CapabilityResult → _core/classification.classify(result, validation)  [EXISTING, unchanged]
```

**Ordering:** POST-RESOLVE runs *before* DECIDE (email de-dups survivors first).
DECIDE is the single status decision. POST-RESOLVE feeds it a cleaned/extended
survivor list, or (geolocation empty-candidate case) builds `reading_survivors`
and calls `decide` on them — it never returns a raw tuple.

### 3.2 Reconciliation with `_core/classification.py`

`_core/classification.classify` stays the **final post-validation step**. The
new engine-owned `decide` is an **earlier** stage (resolver survivors → status).
Two distinct stages, no rivalry. Both under `_core/`.

### 3.3 Engine-owned: `_core/classify.py` — the PURE status primitive

Lifts the shared decision. The protocol fields match the **existing** 9
`_Survivor` types (every one has `value` and `evidence`, per CLASSIFY_SEAM.md
table — there is **no** `ambiguity_rule` field on any existing survivor type;
email's AMBIGUOUS evidence is built from the *merged union* of each survivor's
`evidence` plus `ambiguous_provider_equivalence`, see
`email/canonicalizer.py:309–314`). Rule names are **contract-driven** (optional
kwargs; Law 14 provenance); defaults preserve current behavior.

```python
# _core/classify.py
class _SurvivorProtocol(Protocol):
    value: str
    evidence: tuple[Evidence, ...]

def decide(survivors: Sequence[_SurvivorProtocol], *,
           none_rule: str = "unrecognized_format",
           ambiguous_rule: str = "ambiguous") -> tuple[Status, str | None, tuple[Evidence,...], tuple[str,...] | None]:
    # `none_rule` lets a domain distinguish "no candidates" (unrecognized_format)
    # from "no survivors" (grammar_rejected): post_resolve passes the right rule.
    # `ambiguous_rule` is the marker appended when >1 distinct survivor survives.
    if not survivors:
        return Status.INVALID, None, (_evidence(none_rule),), None
    if len(survivors) == 1:
        s = survivors[0]
        return Status.CANONICALIZED, s.value, s.evidence, None
    # >1 survivor -> AMBIGUOUS (Don't Guess). Surface every reading and the union
    # of each survivor's derivation evidence, then mark the ambiguity itself —
    # matching email/canonicalizer.py:309–314 exactly.
    merged: list[Evidence] = []
    for s in survivors:
        for ev in s.evidence:
            if ev not in merged:
                merged.append(ev)
    merged.append(_evidence(ambiguous_rule))
    rendered = tuple(sorted({s.value for s in survivors}))
    return Status.AMBIGUOUS, None, tuple(merged), rendered
```

**Why `none_rule` (not a `candidates` arg):** email needs `unrecognized_format`
when `candidates` is empty but `grammar_rejected` when `survivors` is empty.
The resolver already knows which — `post_resolve` passes the correct
`none_rule` into `decide`. `decide` stays a pure function of survivors + a
caller-supplied invalid-rule name. No new survivor fields invented, replay-safe.

**AMBIGUOUS evidence is real, not a stub.** It is the dedup-merged union of the
survivors' own `evidence` plus a single `ambiguous_rule` marker. This reproduces
email's existing evidence shape (`:309–314`) and geolocation's
`ambiguous_hemisphere` marker can be supplied via `ambiguous_rule=` when
geolocation routes through `decide`. No fabricated `ambiguity_rule` survivor
attribute.

### 3.4 Domain-owned: `post_resolve` hook (optional, anti-reimpl)

Signature carries the resolver's full output so email/geolocation keep their
distinction:

```python
def post_resolve(rep, candidates, survivors, drop_reasons, contract, *,
                 decide=decide) -> tuple[Status, str|None, tuple[Evidence,...], tuple[str,...]|None]:
    ...
    return decide(cleaned_survivors, none_rule=...)   # ALWAYS via decide
```

- **email**: if `not candidates` → `decide([], none_rule="unrecognized_format")`;
  else de-dup `survivors` (`:291–297`) → if `not survivors` →
  `decide([], none_rule="grammar_rejected")`; else `decide(deduped)`. Both
  INVALID rules preserved; no collapse.
- **geolocation**: if `candidates` non-empty → `decide(candidates)` (geolocation
  has no `_Survivor` type — its `_Candidate` is structurally compatible with
  `_SurvivorProtocol` since it carries `value` + `evidence`; CLASSIFY_SEAM.md
  confirms geolocation has no `_Survivor`). If empty AND
  `rep.shape == "geo_decimal_pair"` and `contract.require_hemisphere` → build
  `reading_survivors` from the enumerated hemisphere readings; each
  `reading_survivor` carries `value` = the **rendered** `"lat,lon"` reading
  string (e.g. `"12.3,-45.6"`, per geolocation/canonicalizer.py:325–329) and
  `evidence = (_evidence("ambiguous_hemisphere"),)`, then
  `decide(reading_survivors, ambiguous_rule="ambiguous_hemisphere")`
  (AMBIGUOUS). **Never returns a raw tuple** — this satisfies the cycle-2 "MUST
  call decide" rule and fixes the cycle-3 short-circuit contradiction. The
  `ambiguous_hemisphere` marker is preserved via the `ambiguous_rule` kwarg,
  not via a fabricated survivor field. (The per-survivor `ambiguous_hemisphere`
  evidence plus the kwarg marker collapse to one via `decide`'s dedup at §3.3,
  matching geolocation's single `ambiguous_hemisphere` emission at `:333`.)
- **Other 7 domains:** no `post_resolve`; call `decide(survivors)` directly.

The CI guard (§6) forbids the 4-way skeleton in `post_resolve` bodies too, so the
hook cannot become a second copy of `decide`.

### 3.5 Recognition strategies

- `RegexRecognizer` — wraps `_shared/grammar.recognize_grammars` (8 domains).
- `GrammarRecognizer` — adds a `compile(contract)` hook to `Grammar`; date
  deletes its duplicate `Grammar`/`RecognizedRep`, reuses shared `RecognizedRep`.
- `ParserRecognizer` — wraps `recognize_money`; maps `ContractError` → `INVALID`
  with the explicit rule; preserves the `canonical` idempotency flag. Money's
  parse logic untouched.

### 3.6 Location: engine-owned code under `_core/`

AGENTS.md lists `_core/` as the engine-owned layer (engine.py, replay.py,
artifact.py, status.py, provenance.py) and permits extension. Engine-owned
algorithm goes under `_core/`:
- `_core/classify.py` — `decide` (sibling to `_core/classification.py`).
- `_core/recognize.py` — the `Regex`/`Grammar`/`Parser` recognizer strategies.

`_capabilities/<domain>/` remains the extension point (grammar defs, `resolve.py`,
`post_resolve`, inline render). No new top-level `_pipeline/` package.

---

## 4. Goals satisfied

| Goal | How met |
|---|---|
| Maintainable | `_core/classify.py` + `_core/recognize.py` = engine algorithm, small, single-responsibility. |
| Minimal duplication | Only the pure `decide` lifted (7 near-uniform domains). Domain logic (geolocation/email) stays local via `post_resolve` which *calls* `decide`. Types stay local (CLASSIFY_SEAM.md). |
| Easy to fork/extend | New capability = folder with grammar/parser + resolve.py + post_resolve (if needed) + thin canonicalizer wiring strategy objects. Core untouched. |
| Scalable | New recognizer/resolution strategy = one class in `_core/`. New domain = new folder. |
| Anti-spaghetti | `decide` is the only status skeleton; imported and guarded by CI (§6); `post_resolve` must call `decide`, also guarded. |
| Meaningful structure | `_core/` = engine algorithm; `_capabilities/<domain>/` = rules. Mirrors runtime, matches AGENTS.md. |

---

## 5. Migration path (incremental, gated on `tests/property/`)

1. Add `_core/classify.py` with `decide` **and migrate a domain that exercises
   AMBIGUOUS** (`ip` or `phone` — uuid's `>1` branch is dead at `:166`/`:175`,
   but uuid is still migrated for consistency). Verify `tests/property/` pass and
   add `_core/classify.py` unit tests to keep `_core` ≥90% coverage.
2. Migrate the other near-uniform enumerated domains (boolean, country, uuid,
   url) one per PR, each deleting its local skeleton and calling `decide`. Add
   unit tests for each migrated module's coverage.
3. Migrate **email** and **geolocation** via `post_resolve` (calling `decide`,
   preserving both INVALID rules for email; hemisphere enum via `decide` with
   `ambiguous_rule="ambiguous_hemisphere"` for geolocation).
4. Migrate **date's enumeration tier only** (`:788–794` → `decide` via
   `post_resolve`, carving it out of the "call `decide` directly" path because
   its INVALID evidence is `drop_reasons`-driven, not a uniform `none_rule`).
   **Date's direct-return tier (`:608–777`) is NOT touched.** Do NOT migrate date
   onto the shared `RecognizedRep` — `CODING_GUIDELINES §10` documents date's
   per-language `RecognizedRep` as an intentional escape; this proposal respects
   that boundary and leaves date's recognition layer alone.

   **Adapter contract (must be stated so §3.3 and §5 agree):** date's `_Survivor`
   (date/canonicalizer.py:110–119) has **no `value` field** — it carries
   `year/month/day/rule/ordering/century_ambiguous`. `decide`'s protocol requires
   `value: str` (it reads `s.value` for both the CANONICALIZED return and the
   AMBIGUOUS `rendered` set). Therefore date's `post_resolve` MUST adapt each
   `_Survivor` to a `value`-bearing shape before calling `decide` — concretely,
   build lightweight adapters with `value = _format_date(s.year, s.month, s.day)`
   (the same renderer date's own `classify` uses at `:525`) and
   `evidence = (_evidence(s.rule),)`, then call `decide(adapters, …)`. The
   `none_rule` for date's empty/no-survivor INVALID paths is NOT a uniform string:
   it is derived from `drop_reasons` exactly as date/classify:515–520 does
   (`rejected_two_digit_year` / `weekday_contradicts_date` / `invalid_calendar_date`
   / `unrecognized_format`), so date's `post_resolve` selects the right `none_rule`
   from `drop_reasons` and passes it into `decide`. This preserves date's exact
   evidence fidelity while still routing through the shared `decide` skeleton.
5. Add `ParserRecognizer` + `SingleResolution`; wire `money` (map `ContractError`
   → INVALID, preserve `canonical`). Add `_core/recognize.py` unit tests.
6. Update `CLASSIFY_SEAM.md`: skeleton shared via `_core/classify.decide`;
   types + non-uniform enumeration remain domain-local via `post_resolve`.
7. Add CI guard (§6).

Every PR gated on `tests/property/` — a wrong `decide` that drops geolocation's
hemisphere AMBIGUOUS or email's de-dup/INVALID-rule distinction changes emitted
evidence → a property test fails. **Assumption stated explicitly:** the property
suite (or new unit tests added in step 1) asserts *exact evidence-rule names*,
not merely status, for the date enumeration-tier INVALID rules and email's two
INVALID rules — otherwise a `decide` regression on evidence would pass silently.
Where no such test exists today, the migration PR adds one.

---

## 6. Anti-spaghetti enforcement (concrete, implementable)

The status skeleton is a 3-branch primitive, not 4-way:
`if not <survivors>:` → INVALID; `if len(<survivors>) == 1:` → CANONICALIZED;
`else:` → AMBIGUOUS. The CI guard below forbids re-implementing it anywhere but
`_core/classify.py`.

**Mechanically checkable guard (`scripts/check_single_classify_site.py`):** walk
the AST of `src/paxman/` with `ast`. For every `FunctionDef`/`AsyncFunctionDef`:

1. **Allow-list:** the function named `decide` in `_core/classify.py` is exempt.
2. **Banned-body rule:** reject any function body that (a) contains an `If`
   whose test is `not <name>` (or `len(<name>) == 0`) where the same `<name>`
   is later tested with `len(<name>) == 1`, AND (b) whose `orelse`/`else` branch
   returns `Status.AMBIGUOUS` (attribute access `Status.AMBIGUOUS` or a name
   bound to it). Match on the control-flow shape, not literal variable names.
3. **`post_resolve` scoping:** any `FunctionDef` whose `name == "post_resolve"`
   (or is decorated with `@post_resolve`) is additionally required to contain a
   `Call` to `decide` (Name/Attribute `decide`) in its body; if it contains the
   banned 3-branch skeleton but no `decide` call, reject (this catches the
   cycle-3 "short-circuit" contradiction).
4. Report every violation as a CI failure with file:line.

This is implementable with the stdlib `ast` module (no regex guessing). The
guard is added in migration step 7 and wired into the CI gate alongside the
existing `check_*.py` scripts.

- `CLASSIFY_SEAM.md` updated to name `decide` as the single allowed site.

---

## 7. What this deliberately does NOT do

- No extraction / `embedded` recognition (dropped for v2).
- No `span` field (dropped).
- No lowest-common-denominator `_Candidate`/`_Survivor` union type (CLASSIFY_SEAM.md respected).
- No separate `render.py` stage (render stays inline).
- No duplicate of `_core/classification.classify` (reconciled, §3.2).
- No new top-level `_pipeline/` package (engine-owned code under `_core/`, per AGENTS.md).
- **No migration of date's recognition layer** onto the shared `RecognizedRep`
  — `CODING_GUIDELINES §10` documents it as an intentional escape; respected.
- **No fabricated survivor fields** — `decide`'s AMBIGUOUS evidence reuses the
  survivors' own `evidence` (merged), not a new `ambiguity_rule` attribute.
- No change to public API, contracts, or the three invariants.
- **Coverage gate:** new `_core/classify.py` and `_core/recognize.py` pull
  `_core` into the ≥90%-per-subpackage gate. Each migration PR adds unit tests
  for the new `_core` modules so coverage stays ≥90%.

---

## 8. Review history

- **Cycle 1:** Critical — "uniform skeleton" premise false (geolocation/email);
  ignored existing `_core/classification.py`. Major — protocol forced renames;
  render as separate file; money ContractError path. → Revised.
- **Cycle 2:** Critical — POST-RESOLVE ordering wrong for email. Major —
  post_resolve signature incomplete; re-impl risk. Minor — rule names, dedup_key,
  `_pipeline` location, uuid-first. → Revised (post_resolve before decide;
  post_resolve calls decide; `value` field; contract-driven rules; no dedup_key;
  under `_core/`; ip/phone first).
- **Cycle 3:** Critical — `decide` collapsed email's two INVALID rules;
  geolocation short-circuit contradicted must-call-decide. Major — post_resolve
  signature conflated candidates vs survivors. → Revised (none_rule param;
  post_resolve receives full resolver output; geolocation routes via decide).
- **Cycle 4 (Oracle fresh review):** Critical — §1 date-pipeline description
  false (date is two-tier, mostly direct-return from `canonicalize`, not a single
  `recognize→classify` flow); §5 step 4 "migrate date to shared `RecognizedRep`"
  contradicts `CODING_GUIDELINES §10`. Major — `decide` cannot be a drop-in for
  date's `drop_reasons`-driven INVALID evidence; `ambiguity_rule` protocol field
  is fabricated (no `_Survivor` has it — email builds AMBIGUOUS evidence from
  merged `survivor.evidence`); §6 CI guard too vague to grep. Minor — uuid
  citation off-by-one (`:167`→`:166`/`:175`); property-test evidence-name
  assumption unstated; `_core` coverage gate unmentioned. → Revised (date described
  as two-tier + direct-return; date migration carved to enumeration tier only,
  recognition layer left alone; `ambiguity_rule` removed, AMBIGUOUS evidence
  merged from survivors; §6 rewritten as an `ast`-based `scripts/check_single_
  classify_site.py` guard with `post_resolve`-scoping; coverage note added to §7).

---

# Section B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift the duplicated survivor→status classification skeleton out of every capability domain into one engine-owned primitive (`paxman._core.classify.decide`), preserving each domain's exact current evidence/status behavior, and add a CI guard that forbids re-implementing that skeleton elsewhere.

**Architecture:** `decide(survivors, *, none_rule, ambiguous_rule)` is the sole owner of the 3-branch status decision. Domains that need to pick a *non-default* invalid rule from `drop_reasons` (email, ip, boolean, country, uuid, date-enumeration) wrap it in a `post_resolve` hook that selects `none_rule` then calls `decide`; domains whose invalid rule is always the default call `decide` directly. A new `scripts/check_single_classify_site.py` AST guard enforces that the skeleton lives only in `_core/classify.py` and that every `post_resolve` calls `decide`.

**Tech Stack:** Python 3.11+ (`requires-python >=3.11`), `attrs`, `pytest` + `hypothesis` (property tests), stdlib `ast` (CI guard). Run everything through `uv run`. Type-checked with `mypy`; linted/formatted with `ruff`.

---

## HARD RULE — no external documentation citations

**Every task, docstring, and inline comment in this plan MUST NOT reference any file outside `src/`.** Do NOT cite or mention `ARCHITECTURE_DESIGN_REFACTOR_*.md`, `MANDATE.md`, `CODING_GUIDELINES.md`, `CLASSIFY_SEAM.md`, `AGENTS.md`, `README.md`, or any `docs/` file. These documents will be removed or rewritten after this implementation, so any reference to them would mislead post-implementation. All facts needed are encoded in the task steps (exact paths, line numbers, code). Code comments explain the code itself only; docstrings describe the function contract only.

---

## File Structure

**Created:**
- `src/paxman/_core/classify.py` — `decide` primitive + `_SurvivorProtocol`. Engine-owned.
- `src/paxman/_core/recognize.py` — `RegexRecognizer`, `ParserRecognizer` strategy wrappers. Engine-owned.
- `scripts/check_single_classify_site.py` — AST CI guard.
- `tests/unit/test_core_classify.py` — unit tests for `decide`.
- `tests/unit/test_core_recognize.py` — unit tests for recognizer strategies.

**Modified (each deletes its local skeleton, routes through `decide`/`post_resolve`):**
- `src/paxman/_capabilities/phone/canonicalizer.py` — calls `decide` directly.
- `src/paxman/_capabilities/url/canonicalizer.py` — calls `decide` directly.
- `src/paxman/_capabilities/ip/canonicalizer.py` — `post_resolve`: `policy_disabled_family` from `drop_reasons`.
- `src/paxman/_capabilities/boolean/canonicalizer.py` — `post_resolve`: `policy_disabled_token` from `drop_reasons`.
- `src/paxman/_capabilities/country/canonicalizer.py` — `post_resolve`: `policy_disabled_kind` from `drop_reasons`.
- `src/paxman/_capabilities/uuid/canonicalizer.py` — `post_resolve`: `drop_reasons[0]`.
- `src/paxman/_capabilities/email/canonicalizer.py` — `post_resolve`: two INVALID rules + de-dup.
- `src/paxman/_capabilities/geolocation/canonicalizer.py` — `post_resolve`: hemisphere enum.
- `src/paxman/_capabilities/date/canonicalizer.py` — enumeration tier only via `post_resolve` adapter; direct-return tier (608–777) untouched.
- `src/paxman/_capabilities/money/canonicalizer.py` — wire `ParserRecognizer`; map `ContractError → INVALID`, preserve `canonical`.

**Verification gates (run after each batch):** `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/paxman`, `uv run pytest tests/unit --no-header`, `uv run pytest -m property --no-header`, `uv run pytest tests/integration --no-header`, `uv run python scripts/check_single_classify_site.py`.

---

## Task 1: Create `decide` primitive with failing unit tests

**Files:** Create `src/paxman/_core/classify.py`, Create `tests/unit/test_core_classify.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_core_classify.py
from paxman._core.classify import decide
from paxman._core.status import Status
from paxman._types.evidence import Evidence


def _surv(value: str, *rules: str) -> object:
    class _S:
        def __init__(self, v: str, ev: tuple[Evidence, ...]) -> None:
            self.value = v
            self.evidence = ev
    return _S(value, tuple(Evidence(rule, "") for rule in rules))


def test_empty_uses_default_none_rule() -> None:
    status, value, evidence, rendered = decide([])
    assert status is Status.INVALID
    assert value is None
    assert evidence == (Evidence("unrecognized_format", ""),)
    assert rendered is None


def test_empty_uses_supplied_none_rule() -> None:
    status, _, evidence, _ = decide([], none_rule="grammar_rejected")
    assert status is Status.INVALID
    assert evidence == (Evidence("grammar_rejected", ""),)


def test_single_survivor_canonicalized() -> None:
    status, value, evidence, rendered = decide([_surv("a@b.com", "lowercased_domain")])
    assert status is Status.CANONICALIZED
    assert value == "a@b.com"
    assert evidence == (Evidence("lowercased_domain", ""),)
    assert rendered is None


def test_ambiguous_merges_evidence_and_marks() -> None:
    status, value, evidence, rendered = decide(
        [_surv("1.1,2.2", "ambiguous_hemisphere"), _surv("1.1,-2.2", "ambiguous_hemisphere")],
        ambiguous_rule="ambiguous_hemisphere",
    )
    assert status is Status.AMBIGUOUS
    assert value is None
    assert evidence == (Evidence("ambiguous_hemisphere", ""),)
    assert rendered == ("1.1,-2.2", "1.1,2.2")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_core_classify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'paxman._core.classify'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/paxman/_core/classify.py
"""Engine-owned survivor-to-status decision.

This is the single canonical owner of the status skeleton that previously
lived, duplicated, inside every capability domain. Domains call `decide`
directly when their invalid rule is the default, or wrap it in a `post_resolve`
hook that selects a domain-specific `none_rule` first.
"""

from __future__ import annotations

from collections.abc import Protocol, Sequence

from paxman._core.status import Status
from paxman._types.evidence import Evidence


class _SurvivorProtocol(Protocol):
    """Structural shape `decide` requires from a survivor-like object."""

    value: str
    evidence: tuple[Evidence, ...]


def decide(
    survivors: Sequence[_SurvivorProtocol],
    *,
    none_rule: str = "unrecognized_format",
    ambiguous_rule: str = "ambiguous",
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Map resolver survivors onto a canonicalization outcome.

    Args:
        survivors: The resolver's surviving interpretations, each carrying a
            canonical `value` and its derivation `evidence`.
        none_rule: Evidence rule emitted when no survivor remains. Domains that
            distinguish "no candidates" from "no survivors" pass the correct
            rule via a `post_resolve` hook.
        ambiguous_rule: Evidence rule marking an AMBIGUOUS (>1 survivor) outcome.

    Returns:
        A 4-tuple of (status, value, evidence, candidates). `candidates` is the
        sorted tuple of every survivor value when AMBIGUOUS, else None.
    """
    if not survivors:
        return Status.INVALID, None, (Evidence(none_rule, ""),), None
    if len(survivors) == 1:
        s = survivors[0]
        return Status.CANONICALIZED, s.value, s.evidence, None
    merged: list[Evidence] = []
    for s in survivors:
        for ev in s.evidence:
            if ev not in merged:
                merged.append(ev)
    merged.append(Evidence(ambiguous_rule, ""))
    rendered = tuple(sorted({s.value for s in survivors}))
    return Status.AMBIGUOUS, None, tuple(merged), rendered
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_core_classify.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_core/classify.py tests/unit/test_core_classify.py
git commit -m "feat(core): add engine-owned decide status primitive"
```

---

## Task 2: Pin `decide` AMBIGUOUS shape against phone (no production change)

**Files:** Test `tests/unit/test_core_classify.py` (append)

- [ ] **Step 1: Add a test proving `decide` reproduces phone's current AMBIGUOUS shape**

```python
def test_decide_matches_phone_ambiguous_shape() -> None:
    s1 = _surv("+1", "e164")
    s2 = _surv("+2", "e164")
    status, value, evidence, rendered = decide([s1, s2])
    assert status is Status.AMBIGUOUS
    assert evidence == (Evidence("e164", ""),)
    assert rendered == ("+1", "+2")
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/unit/test_core_classify.py::test_decide_matches_phone_ambiguous_shape -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_core_classify.py
git commit -m "test(core): pin decide AMBIGUOUS shape against phone"
```

---

## Task 3: Migrate `phone` to call `decide` directly

**Files:** Modify `src/paxman/_capabilities/phone/canonicalizer.py:125-169`

- [ ] **Step 1: Write a test pinning phone's no-candidates behavior**

```python
# tests/unit/test_phone_capability.py (append)
def test_phone_no_candidates_invalid() -> None:
    from paxman import Phone, canonicalize
    r = canonicalize("!!!not-a-phone!!!", Phone())
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_format" for e in r.evidence)
```

- [ ] **Step 2: Run to confirm baseline passes**

Run: `uv run pytest tests/unit/test_phone_capability.py::test_phone_no_candidates_invalid -v`
Expected: PASS

- [ ] **Step 3: Replace phone `classify` body (lines 125–169) with**

```python
def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome.

    Returns a 4-tuple (status, value, evidence, candidates). The phone grammars
    are mutually exclusive, so at most one survivor survives; the AMBIGUOUS branch
    is retained via `decide` for parity. Delegates the status decision to the
    engine-owned `decide` primitive.
    """
    return decide(survivors)
```

Add import with the other `_core`/status imports:
```python
from paxman._core.classify import decide
```

- [ ] **Step 4: Run phone unit + property tests**

Run: `uv run pytest tests/unit/test_phone_capability.py tests/property -k phone -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/phone/canonicalizer.py tests/unit/test_phone_capability.py
git commit -m "refactor(phone): route classify through engine-owned decide"
```

---

## Task 4: Migrate `ip` (post_resolve: `policy_disabled_family`)

**Files:** Modify `src/paxman/_capabilities/ip/canonicalizer.py:133-161`; Test `tests/unit/test_ip_capability.py` (append)

- [ ] **Step 1: Add tests for ip's two invalid rules**

```python
def test_ip_no_candidates_unrecognized_format() -> None:
    from paxman import IP, canonicalize
    r = canonicalize("not-an-ip", IP())
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_format" for e in r.evidence)


def test_ip_policy_disabled_family() -> None:
    from paxman import IP, canonicalize
    r = canonicalize("::1", IP(allow_family="ipv4"))
    assert r.status.name == "INVALID"
    assert any(e.rule == "policy_disabled_family" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_ip_capability.py -k "unrecognized_format or policy_disabled_family" -v`
Expected: PASS

- [ ] **Step 3: Replace ip `classify` (lines 133–161) with**

```python
def post_resolve(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
    contract: CanonicalIPContract,
    *,
    decide: Callable[..., tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]] = decide,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Select ip's invalid rule from drop_reasons, then delegate to `decide`."""
    if not candidates:
        return decide([], none_rule="unrecognized_format")
    if not survivors:
        none_rule = "policy_disabled_family" if "policy_disabled_family" in drop_reasons else "unrecognized_format"
        return decide([], none_rule=none_rule)
    return decide(survivors)


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome (see post_resolve)."""
    return post_resolve(candidates, survivors, drop_reasons, contract)
```

Add imports:
```python
from collections.abc import Callable
from paxman._core.classify import decide
```

- [ ] **Step 4: Run ip tests + property**

Run: `uv run pytest tests/unit/test_ip_capability.py tests/property -k ip -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/ip/canonicalizer.py tests/unit/test_ip_capability.py
git commit -m "refactor(ip): route classify through post_resolve + decide"
```

---

## Task 5: Migrate `boolean` (post_resolve: `policy_disabled_token`)

**Files:** Modify `src/paxman/_capabilities/boolean/canonicalizer.py:127-156`; Test `tests/unit/test_boolean_capability.py` (append)

- [ ] **Step 1: Add tests for boolean's two invalid rules**

```python
def test_boolean_no_candidates_unrecognized_token() -> None:
    from paxman import Boolean, canonicalize
    r = canonicalize("maybe", Boolean())
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_token" for e in r.evidence)


def test_boolean_policy_disabled_token() -> None:
    from paxman import Boolean, canonicalize
    r = canonicalize("yes", Boolean(disabled_tokens=["yes"]))
    assert r.status.name == "INVALID"
    assert any(e.rule == "policy_disabled_token" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_boolean_capability.py -k "unrecognized_token or policy_disabled_token" -v`
Expected: PASS

- [ ] **Step 3: Replace boolean `classify` (lines 127–156) with**

```python
def post_resolve(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
    contract: CanonicalBooleanContract,
    *,
    decide: Callable[..., tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]] = decide,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Select boolean's invalid rule from drop_reasons, then delegate to `decide`."""
    if not candidates:
        return decide([], none_rule="unrecognized_token")
    if not survivors:
        none_rule = "policy_disabled_token" if "policy_disabled_token" in drop_reasons else "unrecognized_token"
        return decide([], none_rule=none_rule)
    return decide(survivors)


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome (see post_resolve)."""
    return post_resolve(candidates, survivors, drop_reasons, contract)
```

Add imports:
```python
from collections.abc import Callable
from paxman._core.classify import decide
```

- [ ] **Step 4: Run boolean tests + property**

Run: `uv run pytest tests/unit/test_boolean_capability.py tests/property -k boolean -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/boolean/canonicalizer.py tests/unit/test_boolean_capability.py
git commit -m "refactor(boolean): route classify through post_resolve + decide"
```

---

## Task 6: Migrate `country` (post_resolve: `policy_disabled_kind`)

**Files:** Modify `src/paxman/_capabilities/country/canonicalizer.py:186-214`; Test `tests/unit/test_country_capability.py` (append)

- [ ] **Step 1: Add tests for country's two invalid rules**

```python
def test_country_no_candidates_unrecognized_format() -> None:
    from paxman import Country, canonicalize
    r = canonicalize("atlantis", Country(allow_name=True))
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_format" for e in r.evidence)


def test_country_policy_disabled_kind() -> None:
    from paxman import Country, canonicalize
    r = canonicalize("france", Country(allow_name=True, disabled_kinds=["country"]))
    assert r.status.name == "INVALID"
    assert any(e.rule == "policy_disabled_kind" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_country_capability.py -k "unrecognized_format or policy_disabled_kind" -v`
Expected: PASS

- [ ] **Step 3: Replace country `classify` (lines 186–214) with**

```python
def post_resolve(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
    contract: CanonicalCountryContract,
    *,
    decide: Callable[..., tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]] = decide,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Select country's invalid rule from drop_reasons, then delegate to `decide`."""
    if not candidates:
        return decide([], none_rule="unrecognized_format")
    if not survivors:
        none_rule = "policy_disabled_kind" if "policy_disabled_kind" in drop_reasons else "unrecognized_format"
        return decide([], none_rule=none_rule)
    return decide(survivors)


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome (see post_resolve)."""
    return post_resolve(candidates, survivors, drop_reasons, contract)
```

Add imports:
```python
from collections.abc import Callable
from paxman._core.classify import decide
```

- [ ] **Step 4: Run country tests + property**

Run: `uv run pytest tests/unit/test_country_capability.py tests/property -k country -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/country/canonicalizer.py tests/unit/test_country_capability.py
git commit -m "refactor(country): route classify through post_resolve + decide"
```

---

## Task 7: Migrate `uuid` (post_resolve: `drop_reasons[0]`)

**Files:** Modify `src/paxman/_capabilities/uuid/canonicalizer.py:146-179`; Test `tests/unit/test_uuid_capability.py` (append)

- [ ] **Step 1: Add test for uuid invalid-rule passthrough**

```python
def test_uuid_no_candidates_unrecognized_format() -> None:
    from paxman import UUID, canonicalize
    r = canonicalize("not-a-uuid", UUID())
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_format" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_uuid_capability.py::test_uuid_no_candidates_unrecognized_format -v`
Expected: PASS

- [ ] **Step 3: Replace uuid `classify` (lines 146–179) with**

```python
def post_resolve(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
    contract: CanonicalUUIDContract,
    *,
    decide: Callable[..., tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]] = decide,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Select uuid's invalid rule from drop_reasons, then delegate to `decide`."""
    if not candidates:
        return decide([], none_rule="unrecognized_format")
    if not survivors:
        none_rule = drop_reasons[0] if drop_reasons else "grammar_rejected"
        return decide([], none_rule=none_rule)
    return decide(survivors)


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome (see post_resolve)."""
    return post_resolve(candidates, survivors, drop_reasons, contract)
```

Add imports:
```python
from collections.abc import Callable
from paxman._core.classify import decide
```

- [ ] **Step 4: Run uuid tests + property**

Run: `uv run pytest tests/unit/test_uuid_capability.py tests/property -k uuid -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/uuid/canonicalizer.py tests/unit/test_uuid_capability.py
git commit -m "refactor(uuid): route classify through post_resolve + decide"
```

---

## Task 8: Migrate `url` to call `decide` directly (static two-rule distinction)

**Files:** Modify `src/paxman/_capabilities/url/canonicalizer.py:324-344`; Test `tests/unit/test_url_capability.py` (append)

- [ ] **Step 1: Add tests for url's two invalid rules**

```python
def test_url_no_candidates_unrecognized_format() -> None:
    from paxman import URL, canonicalize
    r = canonicalize("not a url", URL())
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_format" for e in r.evidence)


def test_url_grammar_rejected() -> None:
    from paxman import URL, canonicalize
    r = canonicalize("http://", URL())
    assert r.status.name == "INVALID"
    assert any(e.rule == "grammar_rejected" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_url_capability.py -k "unrecognized_format or grammar_rejected" -v`
Expected: PASS

- [ ] **Step 3: Replace url `classify` (lines 324–344) with**

```python
def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
    contract: CanonicalURLContract,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome.

    Url distinguishes "no candidates" (unrecognized_format) from "no survivors"
    (grammar_rejected); both are static, so `decide` is called directly with the
    appropriate `none_rule`. Delegates the status decision to `decide`.
    """
    if not candidates:
        return decide([], none_rule="unrecognized_format")
    if not survivors:
        return decide([], none_rule="grammar_rejected")
    return decide(survivors)
```

Add import:
```python
from paxman._core.classify import decide
```

- [ ] **Step 4: Run url tests + property**

Run: `uv run pytest tests/unit/test_url_capability.py tests/property -k url -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/url/canonicalizer.py tests/unit/test_url_capability.py
git commit -m "refactor(url): route classify through engine-owned decide"
```

---

## Task 9: Migrate `email` (post_resolve: two INVALID rules + de-dup)

**Files:** Modify `src/paxman/_capabilities/email/canonicalizer.py:276-320`; Test `tests/unit/test_email_capability.py` (append)

- [ ] **Step 1: Add tests for email's two invalid rules + de-dup**

```python
def test_email_unrecognized_format() -> None:
    from paxman import Email, canonicalize
    r = canonicalize("not an email", Email())
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_format" for e in r.evidence)


def test_email_grammar_rejected() -> None:
    from paxman import Email, canonicalize
    # An address shape the grammar rejects but recognises as candidate-shaped.
    r = canonicalize("a@b@c", Email())
    assert r.status.name == "INVALID"
    assert any(e.rule == "grammar_rejected" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_email_capability.py -k "unrecognized_format or grammar_rejected" -v`
Expected: PASS

- [ ] **Step 3: Replace email `classify` (lines 276–320) with `post_resolve` + thin `classify`**

```python
def post_resolve(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
    contract: CanonicalEmailContract,
    *,
    decide: Callable[..., tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]] = decide,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Email classification: de-dup survivors, then delegate to `decide`.

    Email distinguishes two invalid cases: no candidates -> unrecognized_format;
    candidates but no survivors -> grammar_rejected. Identical readings are
    collapsed before the len==1 check so they do not masquerade as AMBIGUOUS.
    """
    seen: set[str] = set()
    unique: list[_Survivor] = []
    for survivor in survivors:
        if survivor.value not in seen:
            seen.add(survivor.value)
            unique.append(survivor)
    survivors = unique
    if not candidates:
        return decide([], none_rule="unrecognized_format")
    if not survivors:
        return decide([], none_rule="grammar_rejected")
    return decide(survivors)


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: list[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome (see post_resolve)."""
    return post_resolve(candidates, survivors, drop_reasons, contract)
```

Add imports:
```python
from collections.abc import Callable
from paxman._core.classify import decide
```

- [ ] **Step 4: Run email tests + property**

Run: `uv run pytest tests/unit/test_email_capability.py tests/property -k email -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/email/canonicalizer.py tests/unit/test_email_capability.py
git commit -m "refactor(email): route classify through post_resolve + decide"
```

---

## Task 10: Migrate `geolocation` (post_resolve: hemisphere enum)

**Files:** Modify `src/paxman/_capabilities/geolocation/canonicalizer.py:284-338`; Test `tests/unit/test_geolocation_capability.py` (append)

- [ ] **Step 1: Add tests for geolocation hemisphere AMBIGUOUS + out_of_range**

```python
def test_geo_hemisphere_ambiguous() -> None:
    from paxman import Geolocation, canonicalize
    r = canonicalize("12.3,45.6", Geolocation(require_hemisphere=True))
    assert r.status.name == "AMBIGUOUS"
    assert any(e.rule == "ambiguous_hemisphere" for e in r.evidence)
    assert r.candidates is not None and len(r.candidates) >= 2


def test_geo_out_of_range() -> None:
    from paxman import Geolocation, canonicalize
    r = canonicalize("999,999", Geolocation())
    assert r.status.name == "INVALID"
    assert any(e.rule == "out_of_range" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_geolocation_capability.py -k "ambiguous_hemisphere or out_of_range" -v`
Expected: PASS

- [ ] **Step 3: Replace geolocation `classify` (lines 284–338) with `post_resolve` + thin `classify`**

```python
def post_resolve(
    rep: RecognizedRep,
    candidates: list[_Candidate],
    contract: CanonicalGeolocationContract,
    *,
    decide: Callable[..., tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]] = decide,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Geolocation classification: empty-candidate hemisphere enum, then `decide`.

    When the resolver rejects an unsigned-axis decimal pair under a
    hemisphere-requiring contract, enumerate the competing readings as AMBIGUOUS
    (never guessed). Otherwise delegate the canonical single-candidate outcome to
    `decide`.
    """
    if not candidates:
        if rep.shape == "geo_decimal_pair" and contract.require_hemisphere:
            caps = rep.captures
            a1_sign, a1_body = _split_sign(caps["a1"])
            a2_sign, a2_body = _split_sign(caps["a2"])
            a1 = _parse_number(a1_body)
            a2 = _parse_number(a2_body)
            if contract.coordinate_order == "lon_lat":
                lon, lon_sign, lat, lat_sign = a1, a1_sign, a2, a2_sign
            else:
                lat, lat_sign, lon, lon_sign = a1, a1_sign, a2, a2_sign
            if _LAT_MIN <= lat <= _LAT_MAX and _LON_MIN <= lon <= _LON_MAX:
                lat_vals = (lat,) if lat_sign != "+" else (lat, -lat)
                lon_vals = (lon,) if lon_sign != "+" else (lon, -lon)
                readings = tuple(
                    f"{_quantize(lv, contract.precision)},{_quantize(lonv, contract.precision)}"
                    for lv in lat_vals
                    for lonv in lon_vals
                )
                reading_survivors = [
                    _Candidate(value=r, rule="ambiguous_hemisphere", source="", evidence=(Evidence("ambiguous_hemisphere", ""),))
                    for r in readings
                ]
                return decide(reading_survivors, ambiguous_rule="ambiguous_hemisphere")
        return decide([], none_rule="out_of_range")
    c = candidates[0]
    return decide([c])


def classify(
    rep: RecognizedRep,
    candidates: list[_Candidate],
    contract: CanonicalGeolocationContract,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify resolver output into a canonicalization outcome (see post_resolve)."""
    return post_resolve(rep, candidates, contract)
```

Add imports:
```python
from collections.abc import Callable
from paxman._core.classify import decide
from paxman._types.evidence import Evidence
```

- [ ] **Step 4: Run geolocation tests + property**

Run: `uv run pytest tests/unit/test_geolocation_capability.py tests/property -k geolocation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/geolocation/canonicalizer.py tests/unit/test_geolocation_capability.py
git commit -m "refactor(geolocation): route classify through post_resolve + decide"
```

---

## Task 11: Migrate `date` enumeration tier only (post_resolve adapter)

**Files:** Modify `src/paxman/_capabilities/date/canonicalizer.py:496-520` (classify body) + `:788-794` (call site); Test `tests/unit/test_date_capability.py` (append). Direct-return tier (`:608-777`) is NOT touched.

- [ ] **Step 1: Add tests for date enumeration-tier invalid rules**

```python
def test_date_enum_unrecognized_format() -> None:
    from paxman import Date, canonicalize
    # A text-month shape the grammar does not recognise as a date.
    r = canonicalize("not a date at all", Date(locale="US"))
    assert r.status.name == "INVALID"
    assert any(e.rule == "unrecognized_format" for e in r.evidence)


def test_date_enum_rejected_two_digit_year() -> None:
    from paxman import Date, canonicalize
    r = canonicalize("03/04/25", Date(locale="US", two_digit_year="reject"))
    assert r.status.name == "INVALID"
    assert any(e.rule == "rejected_two_digit_year" for e in r.evidence)
```

- [ ] **Step 2: Run baseline**

Run: `uv run pytest tests/unit/test_date_capability.py -k "unrecognized_format or rejected_two_digit_year" -v`
Expected: PASS

- [ ] **Step 3: Replace date `classify` (lines 496–520) with `post_resolve` that adapts `_Survivor` → value-bearing, and derive `none_rule` from `drop_reasons`**

```python
def post_resolve(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: set[str],
    contract: CanonicalDateContract,
    *,
    decide: Callable[..., tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]] = decide,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Date enumeration-tier classification, then delegate to `decide`.

    Date's `_Survivor` carries (year, month, day, rule, ...) but no `value` field,
    so survivors are adapted to a value-bearing shape via `_format_date` before
    `decide` reads `value`. The invalid rule is selected from `drop_reasons` to
    preserve the exact evidence emitted by the resolver (rejected_two_digit_year /
    weekday_contradicts_date / invalid_calendar_date / unrecognized_format).
    """
    if not candidates:
        return decide([], none_rule="unrecognized_format")
    if not survivors:
        if "rejected_two_digit_year" in drop_reasons:
            none_rule = "rejected_two_digit_year"
        elif "weekday_contradicts_date" in drop_reasons:
            none_rule = "weekday_contradicts_date"
        else:
            none_rule = "invalid_calendar_date"
        return decide([], none_rule=none_rule)
    adapted = [
        _Candidate(
            value=_format_date(s.year, s.month, s.day),
            rule=s.rule,
            source="",
            evidence=(Evidence(s.rule, ""),),
        )
        for s in survivors
    ]
    return decide(adapted)


def classify(
    candidates: list[_Candidate],
    survivors: list[_Survivor],
    drop_reasons: set[str],
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify survivors into a canonicalization outcome (see post_resolve)."""
    return post_resolve(candidates, survivors, drop_reasons, contract)
```

Also update the call site at `:788-794` so it forwards `drop_reasons` (already a `set[str]` from `resolve_and_validate`) to `classify` — the existing call already passes `drop_reasons`; no signature change needed there.

Add imports:
```python
from collections.abc import Callable
from paxman._core.classify import decide
from paxman._types.evidence import Evidence
```

- [ ] **Step 4: Run date tests + property**

Run: `uv run pytest tests/unit/test_date_capability.py tests/property -k date -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/paxman/_capabilities/date/canonicalizer.py tests/unit/test_date_capability.py
git commit -m "refactor(date): route enumeration tier through post_resolve + decide"
```

---

## Task 12: Wire `money` via `ParserRecognizer` (map `ContractError → INVALID`, preserve `canonical`)

**Files:** Create `src/paxman/_core/recognize.py`; Modify `src/paxman/_capabilities/money/canonicalizer.py` (the `canonicalize` try/except around `recognize_money`); Test `tests/unit/test_core_recognize.py`, `tests/unit/test_money_capability.py` (append)

- [ ] **Step 1: Add unit tests for `ParserRecognizer` + money ContractError mapping**

```python
# tests/unit/test_core_recognize.py
from paxman._core.recognize import ParserRecognizer
from paxman._capabilities.money.grammar import recognize_money, ContractError
from paxman import Money, canonicalize
from paxman._core.status import Status


def test_parser_recognizer_maps_contract_error_to_invalid() -> None:
    rec = ParserRecognizer(recognize_money)
    # currency mismatch raises ContractError inside recognize_money
    r = rec.parse("USD 5.00", Money(currency="MYR"))
    assert r.status is Status.INVALID
    assert any(e.rule == "unrecognized_format" for e in r.evidence)


def test_parser_recognizer_preserves_canonical_flag() -> None:
    rec = ParserRecognizer(recognize_money)
    r = rec.parse("MYR 5.00", Money(currency="MYR"))
    assert r.status is Status.CANONICALIZED
    assert r.value == "MYR:5.00"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_core_recognize.py -v`
Expected: FAIL (`ParserRecognizer` does not exist yet)

- [ ] **Step 3: Create `src/paxman/_core/recognize.py`**

```python
# src/paxman/_core/recognize.py
"""Engine-owned recognition strategies.

Wraps the three recognition styles (regex, grammar, parser) so the engine owns
the common dispatch while domains keep their own grammar/parser definitions.
"""

from __future__ import annotations

from collections.abc import Callable

from paxman._core.result import CapabilityResult
from paxman._core.status import Status
from paxman._types.evidence import Evidence


class ParserRecognizer:
    """Wraps a procedural parser that raises a domain `ContractError` on failure.

    Maps the raised `ContractError` to an INVALID CapabilityResult (with the
    explicit ``unrecognized_format`` rule) instead of letting it propagate, and
    preserves any idempotency flag the parser attached to the parsed parts.
    """

    def __init__(self, parse: Callable[..., object]) -> None:
        self._parse = parse

    def parse(self, raw: str, contract: object) -> CapabilityResult:
        try:
            parts = self._parse(raw, contract)
        except Exception:
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(Evidence("unrecognized_format", ""),),
            )
        canonical = bool(getattr(parts, "canonical", False))
        return CapabilityResult(
            status=Status.CANONICALIZED,
            value=getattr(parts, "value", raw),
            evidence=(Evidence("parsed_money", ""),),
            candidates=None,
            canonical=canonical,
        )
```

Note: the exact attribute names (`canonical`, the rendered `value`) on `MoneyParts` must match what `recognize_money` returns (verified: `MoneyParts` has `canonical: bool` and the caller composes the canonical string). Adjust the `value=` line to read the same field the money `canonicalize` currently uses; the behavior being preserved is "ContractError → INVALID with unrecognized_format, and the `canonical` idempotency flag survives".

- [ ] **Step 4: Wire money `canonicalize` to use `ParserRecognizer`**

In `src/paxman/_capabilities/money/canonicalizer.py`, replace the inline try/except that calls `recognize_money` with a call through `ParserRecognizer(recognize_money).parse(raw, contract)`, preserving the existing composition of the canonical string and the `canonical` flag on the returned `CapabilityResult`. Add:
```python
from paxman._core.recognize import ParserRecognizer
```

- [ ] **Step 5: Run money tests + property**

Run: `uv run pytest tests/unit/test_core_recognize.py tests/unit/test_money_capability.py tests/property -k money -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/paxman/_core/recognize.py src/paxman/_capabilities/money/canonicalizer.py tests/unit/test_core_recognize.py tests/unit/test_money_capability.py
git commit -m "feat(core): add ParserRecognizer; wire money through it"
```

---

## Task 13: Add the AST CI guard `scripts/check_single_classify_site.py`

**Files:** Create `scripts/check_single_classify_site.py`

- [ ] **Step 1: Write the guard**

```python
#!/usr/bin/env python
"""CI guard: the status skeleton must live only in `_core/classify.py`.

Forbids the 3-branch survivor->status skeleton (if not <x>: INVALID; elif
len(<x>)==1: CANONICALIZED; else: AMBIGUOUS) anywhere outside decide(), and
requires every post_resolve() to call decide(). Exits non-zero on violation.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

SRC = Path("src/paxman")


def _is_status_ambiguous(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Status"
        and node.attr == "AMBIGUOUS"
    )


def _has_skeleton(body: list[ast.stmt]) -> bool:
    saw_not = False
    saw_len_one = False
    saw_ambiguous = False
    for stmt in body:
        if not isinstance(stmt, ast.If):
            continue
        test = stmt.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            saw_not = True
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Call)
            and isinstance(test.left.func, ast.Name)
            and test.left.func.id == "len"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
        ):
            saw_len_one = True
        if _returns_status_ambiguous(stmt):
            saw_ambiguous = True
    return saw_not and saw_len_one and saw_ambiguous


def _returns_status_ambiguous(node: ast.If) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Return) and sub.value is not None and _is_status_ambiguous(sub.value):
            return True
    return False


def _calls_decide(body: list[ast.stmt]) -> bool:
    for sub in ast.walk(ast.Module(body=body)):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name) and f.id == "decide":
                return True
            if isinstance(f, ast.Attribute) and f.attr == "decide":
                return True
    return False


def main() -> int:
    errors: list[str] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            is_decide = fn.name == "decide" and path.name == "classify.py"
            is_post_resolve = fn.name == "post_resolve"
            if is_decide:
                continue
            if _has_skeleton(fn.body):
                errors.append(f"{path}:{fn.lineno} forbidden status skeleton")
            if is_post_resolve and not _calls_decide(fn.body):
                errors.append(f"{path}:{fn.lineno} post_resolve must call decide()")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    print("OK: single classify site enforced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the guard**

Run: `uv run python scripts/check_single_classify_site.py`
Expected: OK (after all migrations land; if run earlier it flags any not-yet-migrated domain — fix by completing that domain's task).

- [ ] **Step 3: Commit**

```bash
git add scripts/check_single_classify_site.py
git commit -m "feat(ci): add single-classify-site AST guard"
```

---

## Task 14: Update in-tree seam doc + run full gate

**Files:** Modify `src/paxman/_capabilities/_shared/CLASSIFY_SEAM.md` (in-tree only); run full verification.

- [ ] **Step 1: Update CLASSIFY_SEAM.md to name `decide` as the single site**

Edit `src/paxman/_capabilities/_shared/CLASSIFY_SEAM.md`: add a line stating the status skeleton now lives in `paxman._core.classify.decide`; domain-local `_Candidate`/`_Survivor` types remain local; non-uniform enumeration (email two-rule, geolocation hemisphere) stays in each domain's `post_resolve`. Do NOT add any reference to documents outside `src/`.

- [ ] **Step 2: Run the full local gate**

Run (each separately, all must pass):
```
uv run ruff check .
uv run ruff format --check .
uv run mypy src/paxman
uv run pytest tests/unit --no-header
uv run pytest -m property --no-header
uv run pytest tests/integration --no-header
uv run python scripts/check_single_classify_site.py
uv run python scripts/check_readme_quickstart.py
uv run python scripts/check_capability_section_isolation.py
uv run python scripts/check_paxman_normalize_substring.py
uv run python scripts/check_retired_vocabulary.py
```
Expected: all exit 0. (Note: `check_retired_vocabulary.py` scans `src/paxman/`; the new code uses only permitted vocabulary.)

- [ ] **Step 3: Commit**

```bash
git add src/paxman/_capabilities/_shared/CLASSIFY_SEAM.md
git commit -m "docs(shared): record decide as the single classify site"
```

---

## Self-Review Notes (plan author)

- **Spec coverage:** `decide` (Task 1), phone/url direct (3,8), ip/boolean/country/uuid/email/geolocation/date via `post_resolve` (4–11), recognizer strategies + money (12), CI guard (13), seam doc (14). All proposal sections addressed.
- **Correction vs proposal §5:** the proposal said "other 7 domains call decide directly"; verified code shows ip/boolean/country/uuid have `drop_reasons`-driven invalid rules, so they use `post_resolve` (Tasks 4–7). This plan is faithful to actual code, not the proposal's simplifying gloss.
- **No external-doc citations:** all task steps, docstrings, and inline comments reference only `src/` paths and code. The HARD RULE is stated at the top.
- **Type consistency:** `decide` signature `decide(survivors, *, none_rule, ambiguous_rule)` is used identically in every task; `_SurvivorProtocol` requires `value` + `evidence`; date/geolocation adapters supply both.

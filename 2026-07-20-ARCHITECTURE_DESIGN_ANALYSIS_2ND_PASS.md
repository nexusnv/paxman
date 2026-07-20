# Architecture Design Analysis — 2nd Pass

**Date:** 2026-07-20
**Branch:** improve/architecture
**Scope:** Architecture review of Paxman's capability model for (1) un-complicating
low-value design, (2) maintainability, (3) scaling to 50 new capabilities in 7 days
with "no capability is special", and (4) dependency arrow pointing inward.

---

## Section 1 — Findings & Analysis

### Methodology

- Read `MANDATE.md` (1,160 LOC), `ARCHITECTURE.md` (645 LOC), `CODING_GUIDELINES.md`
  (168 LOC).
- Fired 4 parallel explore agents mapping: capability shape variation, core pipeline
  complexity, shared infrastructure, and test suite / public API surface.
- Read `engine.py`, `validation.py`, `engine_env.py`, `__init__.py`,
  `_orchestrator_runtime.py`, `CapabilityBase`, `discovery.py`, `_core/provenance.py`,
  `_provenance/evidence.py` directly.
- Self-grilled each finding, then fired Oracle (read-only high-IQ consultant) for a
  brutal critique.
- Verified Oracle's corrections against source.

### Verdict Up Front

The **core pipeline is remarkably clean** — zero `if contract.kind ==` branches in
`engine.py`; `validation.py` delegates to `capability.validate()` (dependency arrow
points inward); `classification.py` is a pure 4-line function; `replay.py` treats the
artifact as opaque. The mandate's Principle 4 ("core should not own domain knowledge")
holds at the behavioral level.

**The real problem is capability authoring cost, not export-list friction.** Measuring
"edit points to add a capability" over-weighted the wrong thing; the actual blocker for
"50 in 7 days" is authoring cost (LOC a contributor must write per capability). Today:
~400 LOC of canonicalizer + ~200 LOC of tests, hand-written, with no shared scaffold.
At 1.4 capabilities/day that is not achievable without structural change.

### Findings Ranked by Actual Impact

#### 🔴 TIER 1 — The 50-in-7-days blockers

**Finding A — `can_handle` + dispatch INVALID returns duplicated 10×.**
Every canonicalizer opens with `isinstance(contract, Canonical<X>Contract) and
isinstance(value, str)` plus `not_a_<x>_contract` and `not_a_string_value` INVALID
`CapabilityResult` returns. 47 grep hits across 10 canonicalizers + 10 rules manifests.
*Oracle: "Highest-ROI mechanical fix in your entire list. Do it first."*

**Finding B — No shared test scaffold; each capability hand-writes 4-6 test files.**
Three divergent test shapes, no `CapabilityTestBase`, no parametrized harness. Only
`fresh_registry` fixture exists. 9/15 property tests are capability-specific (duplicating
idempotence/replay/immutability). *Oracle: "Under-weighted; tied with A for top priority."*

**Finding C — No capability template / authoring guide (author missed this initially).**
There is no cookiecutter or skeleton reflecting the minimum surface. A contributor
reverse-engineers the convention from 10 examples with 3 variants. `docs/how-to/
write-a-compliant-capability.md` exists but predates the `_shared` extraction helpers and
must be revised to reflect the simplified authoring path. *Oracle: "That's the gap."*

**Finding D — The `rules.py` / `_RULE_AUTHORITIES` manifest is a per-capability burden
(author missed this initially).**
`_provenance/evidence.py:59-86` — every capability must declare a `RuleAuthorities`
mapping (`Mapping[str, Authority | None]`); a missing entry raises `KeyError` at
evidence-build time. At 50 capabilities this becomes the dominant authoring cost.
*Oracle: "Will become the dominant authoring cost at 50 capabilities."* (Deferred to a
follow-up; documented here as a known scaling tax.)

#### 🟡 TIER 2 — Real friction, do after Tier 1

**Finding E — `_shared/grammar.py` only fits 8/10; date and money escape.**
`recognize_grammars` assumes anchored regex with a single `Grammar` shape returning raw
string captures. 8 domains use it. `date` escapes (bracket-notation compiler with
per-language recompilation, own `Grammar` with `field_roles`). `money` escapes (no
`Grammar`; structured `recognize_money` returning a typed `MoneyParts`). *Oracle: "Problem
is real and under-weighted; recommendation is half-right. Defer the strategy-protocol
until 3 more structured parsers are written."*

**Finding F — `_dsl/parser.py` 10-branch isinstance chain contradicts its own docstring.**
`parser.py:18-27` imports all 10 concrete contract classes; `:62-81` has `if
isinstance(spec, Canonical<X>Contract)` per domain. The docstring claims "registry-driven,
never names a concrete contract class" — contradicted by code. *Oracle: "Correct and safe.
Also fix the leaky docstring in `contract_registry.py`."* ⚠️ Watch out: audit `can_handle`
bodies — Protocol dispatch must not change which contracts a capability claims.

**Finding G — `__init__.py` + `discovery.py` + `test_load_builtins.py` list duplication.**
Adding one capability requires ~9 edit points all enumerating the same list.
`discovery.py` is the intended source of truth (keep explicit); `test_load_builtins.py`
hardcodes `len == 10`, name sets (twice), and full class enumerations (twice more) — 4
redundant edit points. *Oracle: "Sound, 30-minute cleanup, not an architecture fix."*

#### 🟢 TIER 3 — Documentation/hygiene, defer

**Finding H — `_provenance` package (1,473 LOC, 30 files) undocumented in ARCHITECTURE.md.**
*Self-correction:* I originally claimed Evidence was "split" between `_core/provenance.py`
and `_provenance/evidence.py`. **Wrong** — `_core/provenance.py` is a 14-line re-export
shim (verified). There is no parallel implementation. *Oracle: "Mostly a doc bug."* Plan:
document the subsystem; drop the "split" framing.

**Finding I — `_core/engine_env.py` hardcodes 4 authority names in 3 dicts.**
Rarely hit (new authorities grow slower than capabilities). Defer until a new authority
is actually needed.

**Finding J — date canonicalizer is 814 LOC (6.7× money).**
*Self-correction:* originally recommended decomposing date. **Wrong** — refactoring
theater. The leverage is extracting the 4-stage pattern into a shared base (covered by
A + C). Drop as an architecture problem.

**Finding K — Stale ARCHITECTURE.md directory tree.**
`_shared/base.py` (CapabilityBase) missing from the tree; `_StubContract` (28 LOC) lives
inside `engine.py` rather than near the Contract Protocol. Update tree + move stub.

### The Deeper Disease (Oracle's escalation trigger)

> The `Contract` Protocol vs concrete-class coupling is the deeper disease. `can_handle`
> checks `isinstance(contract, Canonical<X>Contract)` everywhere; `parse_contract` has the
> 10-branch chain (Finding F); `contract_registry.py` imports concrete contracts under
> `TYPE_CHECKING`; `validation.py` threads the capability through. The contract *concrete
> class* is the coupling point, not the capability. A capability should bind to a contract
> **Protocol** (structural), not a named class. Fixing that would collapse Findings A, F, G
> simultaneously.

**Do NOT do this preemptively.** Escalation trigger (from Oracle): *if, after Tier 1+2,
adding capability #11 still requires touching >3 files outside its own package, escalate
to Protocol-based contract dispatch across `validation.py`/`engine.py` — a 3+ day refactor.*

### Recommended Action Plan (carried into Section 2)

| Priority | Finding | Effort | Goal Served |
|---|---|---|---|
| 1 | A: Extract `can_handle` + INVALID dispatch into `CapabilityBase` | Short | Un-complicate, Scale |
| 2 | B: Build `CapabilityTestBase` + generic invariant test over all 10 | Medium | Maintain, Scale |
| 3 | C: Revise `docs/how-to/write-a-compliant-capability.md` to the new path | Medium | Scale (critical) |
| 4 | F: Replace parser isinstance chain with Protocol check; fix docstrings | Short | Un-complicate, Dep inward |
| 5 | G: Auto-derive `__init__.py` exports + make `test_load_builtins` derive from `discovery` | Short | Maintain, Scale |
| 6 | H/K: Document `_provenance/`; update ARCHITECTURE.md tree; move `_StubContract` | Short | Maintain |

**Estimated effort for items 1-6: 1-2 days.** Finding D (rule manifest) and Finding E
(grammar seam) are explicitly deferred to a follow-up pass (documented, not dropped).

---

## Section 2 — Implementation Plan (Full Pass, All 6 Priorities)

This plan fully implements priorities 1-6 with **no deferral and no partial
implementation** across all 10 built-in capabilities. Every change is behavior-preserving:
the sub-agents must run the full CI gate (ruff, mypy, the per-subpackage test suites, and
the property/integration suites) and confirm green before reporting done. No capability's
external behavior, `Status`, `evidence` rule names, or `replay_hash` may change.

File sets are partitioned so the six work packages touch **disjoint** files and may run
concurrently without conflict. Each sub-agent must:
- Touch ONLY its assigned files (do not run repo-wide `ruff format`; format only the
  files you edit).
- Preserve exact `evidence` rule names, `Status` values, and `CapabilityResult` shapes.
- Run `uv run pytest tests/unit tests/property tests/integration --no-header -q` (scoped
  to its files where possible) and confirm pass before reporting.

### Work Package 1 — Extract `can_handle` + dispatch-INVALID into `CapabilityBase` (Finding A)

**Files:** `src/paxman/_capabilities/_shared/base.py` + all 10 canonicalizers
(`email`, `uuid`, `date`, `phone`, `url`, `boolean`, `ip`, `money`, `geolocation`,
`country`).

**New API in `_shared/base.py`:**
- `make_can_handle(contract_cls: type, *, accept_none: bool = False) -> Callable` — returns
  a `can_handle(self, contract, value)` method. When `accept_none` is True, accepts
  `value is None or isinstance(value, str)`; otherwise `isinstance(value, str)` only.
- Module-level helpers (not methods, so they can close over each capability's own
  `_evidence` closure):
  - `reject_contract(contract, expected_cls, _evidence_fn, rule) -> CapabilityResult | None`
    — returns INVALID with `( _evidence_fn(rule), )` when `not isinstance(contract,
    expected_cls)`, else `None`.
  - `reject_non_string(value, _evidence_fn, rule="not_a_string_value") ->
    CapabilityResult | None` — returns INVALID when `not (value is None or
    isinstance(value, str))`, else `None`.
  - `reject_missing(value, _evidence_fn, rule="missing_value") -> CapabilityResult | None`
    — returns `Status.MISSING` when `value is None or value.strip(WS) == ""`, else `None`.
    (`WS = " \t\r\n\f\v"`.)

**Per-capability application (read each canonicalizer's CURRENT body first to preserve
exact behavior):**
- Replace the `def can_handle(...)` method body with `can_handle =
  make_can_handle(Canonical<X>Contract, accept_none=<current behavior>)` as a class
  attribute. Derive `accept_none` from the existing body: `ip`, `boolean`, `money` currently
  accept `None` → `accept_none=True`; `email`, `uuid`, `date`, `phone`, `url`, `geolocation`,
  `country` → `False` (verify each before changing).
- At the top of `canonicalize`, replace the two/three repeated guard blocks with:
  ```python
  r = reject_contract(contract, Canonical<X>Contract, _evidence, "not_a_<x>_contract")
  if r is not None:
      return r
  r = reject_non_string(value, _evidence)
  if r is not None:
      return r
  ```
  Use the EXACT existing rule name (`not_a_ip_contract`, `not_an_email_contract`,
  `not_a_money_contract`, `not_a_boolean_contract`, etc.). If the capability used
  `_evidence(rule, engine=engine)` (engine-aware, e.g. money), pass `engine=engine` through
  — i.e. call `reject_contract(contract, CanonicalMoneyContract, lambda rule: _evidence(rule, engine=engine), "not_a_money_contract")` OR keep the engine-aware closure form. Preserve exactly.
- If the capability also had a `missing_value` early-return, replace it with
  `r = reject_missing(value, _evidence, "missing_value"); if r is not None: return r`
  (only where it already existed — do not add MISSING handling where absent).
- Do NOT change recognition/resolution/classification logic.

**Verification:** `uv run pytest tests/unit tests/property tests/integration -q` all green;
spot-check that `date`, `email`, `money` canonicalization outputs and evidence are
byte-identical to before (idempotence + replay property tests are the guard).

### Work Package 2 — Build `CapabilityTestBase` + generic invariant test over all 10 (Finding B)

**Files:** new `tests/unit/_capability_test_base.py`; new
`tests/unit/test_capability_invariants_generic.py`; leave existing per-capability test
files intact (do not delete — preserves coverage).

**`tests/unit/_capability_test_base.py`:**
- A `CapabilityTestBase` (pytest base class) with class-level configuration hooks:
  `capability_cls`, `contract_factory()` (returns a default contract), `valid_cases`
  (list of `(input, expected_value_or_status)`), `invalid_cases` (list of `(input,
  expected_status)`), `non_string_inputs` (e.g. `123`, `b"x"` → expect `INVALID`).
- Provides reusable test methods asserting: (a) `can_handle` returns True for a string +
  its contract and False for a foreign contract / non-string; (b) each `valid_case`
  canonicalizes to the expected value with `Status.CANONICALIZED`; (c) each `valid_case`
  is idempotent (`canonicalize(canonicalize(x)) == canonicalize(x)`); (d) each
  `valid_case` replay is byte-equal (`replay(artifact, contract) == artifact`); (e) each
  `invalid_case` yields the expected `Status`; (f) `non_string_inputs` yield `INVALID`
  (`not_a_string_value`).
- These reuse the public `paxman.canonicalize` / `paxman.replay` surface and the
  `fresh_registry` fixture (import from `tests.conftest` or redefine a local one).

**`tests/unit/test_capability_invariants_generic.py`:**
- For all 10 capabilities, subclass `CapabilityTestBase` (or parametrize) with the
  capability's `capability_cls`, a default `contract_factory`, and a SMALL representative
  set of `valid_cases` / `invalid_cases` drawn from each capability's existing unit tests
  (read `test_<x>_capability.py` / `test_<x>_canonicalizer.py` to source 2-3 cases each).
  This proves the harness exercises all 10 without rewriting the originals.
- Do NOT weaken the dedicated property tests in `tests/property/`; this generic module is
  additive.

**Verification:** `uv run pytest tests/unit/test_capability_invariants_generic.py -q` green;
confirm it actually runs cases for all 10 capabilities (not silently skipped).

### Work Package 3 — Revise `docs/how-to/write-a-compliant-capability.md` (Finding C)

**Files:** `docs/how-to/write-a-compliant-capability.md` (existing — revise, do not
rewrite from scratch).

**Changes:**
- Add a "Minimum surface" skeleton showing the simplified authoring path using the new
  helpers from WP1: `can_handle = make_can_handle(CanonicalXContract)`; dispatch guards via
  `reject_contract` / `reject_non_string`; `_RULE_AUTHORITIES` manifest via
  `rule_authorities(...)`; `recognize` via `recognize_grammars` (or custom for date/money).
- State the contract: a new capability should touch ONLY its own
  `_capabilities/<domain>/` package plus (optionally) one line in `discovery.py` and one
  line in `__init__.py` (the latter two are auto-derived post-WP5, so the doc should say
  "register in `discovery.builtin_capabilities()`; exports are auto-derived").
- Note the deferred scaling tax (Finding D): the `_RULE_AUTHORITIES` manifest is required
  per capability; cite the Law 14 source for every rule.
- Keep all existing accurate content (SPI rules, provenance requirements, the three
  invariants).

**Verification:** doc is internally consistent with the post-WP1/WP5 code; no false
claims about manual edits that are now auto-derived.

### Work Package 4 — Replace parser isinstance chain with Protocol check; fix docstrings (Finding F)

**Files:** `src/paxman/_dsl/parser.py`; `src/paxman/_registry/contract_registry.py`
(docstring only).

**`parser.py`:**
- Confirm the structural `Contract` Protocol in `_core/contracts.py` is importable and
  satisfied by every `Canonical<X>Contract` (they expose `kind`, `version_field`,
  `authority_override`, `as_dict`). Read `_core/contracts.py` first.
- Replace the 10-branch `isinstance(spec, Canonical<X>Contract)` short-circuit with a
  single `if isinstance(spec, Contract): return spec` (already-parsed contracts are
  identity — no reconstruction). The dict-spec path continues to `get_builder`.
- Remove the now-unused top-level imports of the 10 concrete contract classes (keep only
  `Contract` Protocol + error types + `get_builder`).
- Fix the module docstring (lines 8-11) to reflect reality: it is still registry-driven for
  dict specs; for already-parsed contracts it returns identity via the structural Protocol
  check — it no longer enumerates concrete classes.
- **Behavioral guard:** `parse_contract` must return the SAME object/value it did before
  for both parsed-contract and dict inputs. The orchestrator relies on `parsed_contract`
  being the same instance for already-parsed specs.

**`contract_registry.py`:**
- Fix the misleading docstring claims ("never names a concrete contract class") — the
  `TYPE_CHECKING` block + `_BuilderResult` union still name concrete classes; rephrase to
  "runtime dispatch is registry-driven and domain-free; the type alias below is a static
  annotation convenience only."

**Verification:** `uv run pytest tests/unit tests/integration -q` green, especially
`test_orchestrator_autoload`, `test_readme_capability_section_isolation`, and any
`parse_contract` round-trip tests. Confirm `paxman.canonicalize("x", Email())` still works
(identity parse path).

### Work Package 5 — Auto-derive `__init__.py` exports + derive `test_load_builtins` from `discovery` (Finding G)

**Files:** `src/paxman/__init__.py`; `tests/unit/test_load_builtins.py`.

**`__init__.py`:**
- Keep the 10 explicit `from paxman._capabilities.<domain>.contract import <PublicName>,
  <CanonicalXContract>` import lines — these expose the user-facing API
  (`from paxman import Email`, `Date`, …) and must remain.
- Auto-derive the `Contract` type alias from the imported `Canonical*Contract` names: after
  the imports, collect them and build `Contract = typing.Union[tuple(<imported contract
  classes>)]` (dynamic `Union` of the concrete classes already imported). Remove the
  hand-written 10-type `Contract = (...)` literal.
- Auto-derive the `Canonical*` entries of `__all__`: after building the explicit `__all__`
  list, append the `Canonical*Contract` names discovered via `globals()` inspection of
  imported names (so adding a capability only requires the one `from ... import` line).
  Keep the explicitly-listed public value-object names (`Email`, `Date`, …) as-is.
- Confirm `from paxman import Email, Date, UUID, Country, Money, Phone, URL, IP, Boolean,
  Geolocation, CanonicalEmailContract, ...` and `paxman.canonicalize` all still resolve.

**`test_load_builtins.py`:**
- Replace `assert len(result) == 10` with `assert len(result) == len(builtin_capabilities())`.
- Replace the two hardcoded name-set assertions with
  `assert {c.name for c in result} == {c.name for c in builtin_capabilities()}` (and the
  ordered list assertion with `[c.name for c in builtin_capabilities()]`).
- Replace `test_preserves_user_capability_of_same_name` and
  `test_capabilities_hash_after_load_builtins_matches_register` hardcoded `register(XCap())`
  loops with `for c in builtin_capabilities(): registry.register(c)`.
- Keep the `MyEmailCap` user-override test logic; derive its expected hash from
  `builtin_capabilities()` rather than re-listing classes.
- Remove now-unused explicit capability-class imports where the test no longer references
  them directly (keep `builtin_capabilities` import + any still-used names).

**Verification:** `uv run pytest tests/unit/test_load_builtins.py -q` green; adding a
capability to `discovery.py` should now require NO test edit.

### Work Package 6 — Document `_provenance/`; update ARCHITECTURE.md tree; move `_StubContract` (Findings H, K)

**Files:** `src/paxman/_core/contracts.py` (move `_StubContract` here); `src/paxman/_core/engine.py`
(use the moved stub); `ARCHITECTURE.md` (document `_provenance/`, add `_shared/base.py` to
the tree, note `_StubContract` location).

**`_StubContract`:**
- Move the `_StubContract` class (engine.py:44-72) into `_core/contracts.py` (it satisfies
  the `_ContractLike` Protocol — confirm the Protocol shape matches). Update `engine.py` to
  import it from `_core.contracts` instead of defining it locally. Behavior unchanged.

**`ARCHITECTURE.md`:**
- In the directory tree under `_capabilities/_shared/`, add `base.py` (CapabilityBase) —
  currently missing.
- Add a `_provenance/` package entry (sibling of `_core/`, not under it) describing:
  `authority.py` (Authority), `selection.py` (Latest/Selector), `evidence.py` (Evidence +
  `_evidence`), `registries/` (iso_3166, iso_4217, cldr, itu_e164), `specs/` (per-RFC resolver
  modules, e.g. rfc_5321, rfc_5322, rfc_4122, rfc_3986, rfc_3339, …), `behaviour/`
  (documented platform behavior — Law 14 source #2), `policy/` (declared Paxman policy —
  Law 14 source #3). Clarify that `_core/provenance.py` is a 14-line re-export shim to
  `_provenance/evidence.py` (no parallel implementation).
- Note `_StubContract` lives in `_core/contracts.py`.
- Do NOT change any code-describing accuracy elsewhere; this is documentation only.

**Verification:** `uv run ruff check .` (doc prose unaffected); `uv run pytest tests/unit
-q` green (engine behavior identical). Manually confirm `ARCHITECTURE.md` tree matches the
actual file layout (run `find src/paxman/_capabilities/_shared src/paxman/_provenance -name
'*.py'` and reconcile).

### Cross-Cutting Final Gate (run once after all 6 packages land)

The orchestrator (me) runs the full CI gate from AGENTS.md and must be fully green before
committing:

```
uv run ruff check .
uv run ruff format --check .
uv run mypy src/paxman
uv run python scripts/check_readme_quickstart.py
uv run python scripts/check_capability_section_isolation.py
uv run python scripts/check_paxman_normalize_substring.py
uv run python scripts/check_retired_vocabulary.py
uv run pytest tests/unit --no-header
uv run pytest -m property --no-header
uv run pytest tests/integration --no-header
```

If any gate fails, the responsible sub-agent's continuation session is invoked to fix it
(evidence before assertion). No partial state is committed. On green: `git add -A` and
commit with a conventional message (`refactor(capabilities): ...`), then stop (no push).

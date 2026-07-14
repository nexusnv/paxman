# The 5-Minute Promise — Design Spec

**Status:** Design spec — 1 of 1.
**Authority:** [`MANDATE.md`](../../../MANDATE.md) is the constitutional boundary for every decision below. Questions not answerable by `MANDATE.md` are out of scope for this spec. Per maintainer directive, no ADR is produced this milestone — the choices recorded here are *tentative implementation decisions*, validated by working software, and will be recorded as an ADR only once the surface is stable.
**Date:** 2026-07-14.
**Branch:** `refactor/sharperning-user-first-5-minutes-experience`.
**Issue:** [#137 — Milestone: The 5-Minute Promise](https://github.com/nexusnv/paxman/issues/137).

---

## 0. Scope

Close the four "novice cliffs" in the v2.0.0 public surface so that a Python developer who has never seen Paxman can install it, copy a 15-line example from the README, run it on the first attempt, see both the result and the explanation of why, and understand replay — without reading any internal documentation, source code, or `src/paxman/_*` modules.

**In scope:**
1. A teaching `AttributeError` for the missing `normalize` name.
2. An `Email()` domain-type factory re-exported from `paxman`.
3. `parse_contract` accepts a `CanonicalEmailContract` instance, not only a dict.
4. Lazy, import-safe, freeze-ordered loading of built-in capabilities.
5. A repo-root `quickstart.py`, a README Quickstart that is the single source of truth, and an "Extending Paxman" section that contains the SPI surface and the freeze-on-first-`canonicalize` constraint.
6. CI-gated regression tests: README-exec, `normalize` teaching error, `Capability`-section grep, `Email()` defaults, 100-email regression with exactly 95 `CANONICALIZED` / 5 `INVALID`.

**Out of scope (explicitly):**
- ADR-0017 (deferred by maintainer directive; criterion 10's *proof* of north-star reachability is therefore deferred, not silently dropped).
- Multi-field contracts (`InvoiceContract(invoice_date=Date(), vendor_email=Email())`).
- Canonical types beyond `Email` (Date, Money, Phone, UUID, tax codes, IBAN, HSCode, Country, Language, Timezone).
- A `pip install paxman` path; install is still `git clone && uv sync`.
- Any change to the 13 laws, the `canonicalize`/`replay`/`register_capability` SPI, `VersionStamp.capabilities_hash`, `FrozenRegistryError`, or replay byte-equality.

---

## 1. The four cliffs, by mandate

The v2.0.0 surface has four cliffs a novice hits in the first 30 minutes. Each is a *symptom*; the mandate already implies the fix.

### 1.1 The `normalize` cliff

**Symptom.** `paxman.normalize(...)` raises a bare `AttributeError: module 'paxman' has no attribute 'normalize'`. No hint that the function is `canonicalize`.

**Mandate grounding.** §1.1 ("Paxman is not a normalizer") establishes the identity boundary: there is no `normalize` attribute, ever. §1.2 (the Identity invariant) reinforces this: "Paxman only canonicalizes." Law 8 (Fail Informatively) applies *to the surface too* — a bare `AttributeError` is informative to the Python interpreter but not to the human. The mandate commands informative failure; an uninformative attribute lookup is a surface violation of Law 8 in spirit.

**Fix.** Add a PEP 562 module-level `__getattr__` in `src/paxman/__init__.py`. For `name == "normalize"`, raise `AttributeError` whose message contains the word `canonicalize` and points the user at the right function. For any other missing name, raise the standard `AttributeError`. Do **not** define a `def normalize`. The §1.1 identity boundary holds — there is still no `normalize` attribute, only a teaching error raised on lookup.

### 1.2 The contract-instance cliff

**Symptom.** `paxman.canonicalize("a@b.com", CanonicalEmailContract())` returns `UNSUPPORTED(unparseable_contract)`. The class is in `paxman.__all__` but `parse_contract` only accepts a dict.

**Mandate grounding.** Law 5 — "The contract defines what canonical means." The contract value object IS the source of truth. A user who has constructed a valid `CanonicalEmailContract` has done everything Law 5 asks. Returning `UNSUPPORTED` for a valid contract is, in spirit, a Law 8 violation — the failure is not informative ("unparseable_contract" lies about a contract that parsed fine at construction time).

**Fix.** `parse_contract` short-circuits and returns the value unchanged when given a `CanonicalEmailContract` instance, before the existing `isinstance(spec, dict)` check. Use the exact type `isinstance(spec, CanonicalEmailContract)`, NOT the parent `Contract` alias — a broader check would silently absorb any future multi-field contract type (criterion 10: the architecture must not preclude the north star).

### 1.3 The built-in registration cliff

**Symptom.** `paxman.canonicalize("a@b.com", {"kind": "canonical_email"})` returns `UNSUPPORTED(no_capability_claims)`. `EmailCapability` exists at `paxman._capabilities.builtins.email.EmailCapability` but is not registered, not re-exported, and the user must import from a private underscore module to wire it up.

**Mandate grounding.** §4.3 ("Built-in capabilities stay in core. Like Carbon ships with all parsers in one package.") — the maintainer's position is that built-in canonical types are Paxman's own facts. Law 8a forbids import-time side effects ("anything that returns different bytes on a second call with the same inputs" — `import paxman` mutating the registry is hidden mutable state). Law 1 includes the capability set in the determinism invariant, so the capability set must be fixed before the first canonicalize call. The mandate therefore permits lazy seeding on first `canonicalize`, but forbids import-time registration.

**Fix.** Add `builtin_capabilities()` in `_capabilities/builtins/__init__.py` returning `[EmailCapability()]` today. Add `load_builtins()` to `CapabilityRegistry` with these ordering and idempotency invariants:
- runs BEFORE `registry.freeze()` on the first canonicalize,
- registers each built-in whose `name` is NOT already present (skip-if-present; never raise `ConfigurationError` for a duplicate),
- never overwrites a pre-existing capability of the same name (user capabilities registered via `paxman.register_capability(...)` before the first canonicalize stay intact),
- is a no-op when the registry is already frozen,
- the resulting `capabilities_hash` includes ALL registered capabilities (user + built-in), so `replay` (which calls `_orchestrator_runtime.default_registry.capabilities_hash()`) still matches.

The orchestrator calls `registry.load_builtins()` before `registry.freeze()` when the registry is not yet frozen — a single-line insertion at the existing freeze-on-first-use site in `_core/orchestrator.py:71-72`. No change to `replay.py`.

### 1.4 The vocabulary cliff

**Symptom.** The user has to know `EmailCapability` exists at all. There is no documented path from "I want to canonicalize an email" to "the thing I call is `EmailCapability()`." The capability name leaks the implementation; the user's intent is "Email", not "EmailCapability".

**Mandate grounding.** §4 — "The contract is the user's language; the capabilities are Paxman's language. They should never be the same vocabulary." §6.3 — adopted vocabulary (resolver, dispatcher, registry, matcher, capability resolution) is the surface vocabulary; retired vocabulary (heuristic, approximate, best effort, probably, confidence) is forbidden anywhere. Law 7 — Explicit Over Clever: user expresses intent, Paxman applies algorithm.

**Fix.** Add an `Email(*, strict=False, provider_aliases="none", lowercase=True, strip_whitespace=True) -> CanonicalEmailContract` factory in `_contracts/contract.py`. Re-export `Email` from `src/paxman/__init__.py` and add it to `__all__`. `EmailCapability` stays where it is as the private builtin path; do NOT add it to `__all__`. The factory returns a configured `CanonicalEmailContract` instance (not a subclass) so every existing `isinstance` check passes unchanged and Law 13 (contract immutability) is preserved by inheritance of the `@attrs.frozen` decorator, not by a new abstraction that would need a Law 11 defense.

---

## 2. The design, by law

Each change is run through Law 11 ("Can two independent implementations produce different results? Can it guess? Can score ordering change?"). For every change below, the answer to all three Law 11 questions is "no" — by construction, not by trust.

### 2.1 `paxman.normalize` teaching error

**Surface.** PEP 562 `__getattr__(name)` in `src/paxman/__init__.py`.

```python
def __getattr__(name: str) -> Any:
    if name == "normalize":
        raise AttributeError(
            "the 'normalize' name does not exist on this module; "
            "Paxman canonicalizes, not normalizes (MANDATE §1.1). "
            "Use canonicalize() instead."
        )
    raise AttributeError(f"module 'paxman' has no attribute {name!r}")
```

**Grep-zero gate.** The literal substring `paxman.normalize` must yield ZERO matches across `src/` and `tests/`. The error message string itself lives in `src/paxman/__init__.py` and IS a grep target; phrase the message so it never contains the substring `paxman.normalize` — refer only to "the 'normalize' name" and "`canonicalize()`".

**Laws preserved.** §1.1 (not a normalizer), §1.2 Identity (only canonicalize), Law 8 (informative failure).

**Laws not violated.** Law 11 (no abstraction introduced), Law 13 (no mutation of artifacts).

### 2.2 The `Email()` domain-type factory

**Surface.** A factory function in `_contracts/contract.py`, re-exported from `paxman.__init__`.

```python
def Email(
    *,
    strict: bool = False,
    provider_aliases: ProviderAliasesPolicy = "none",
    lowercase: bool = True,
    strip_whitespace: bool = True,
) -> CanonicalEmailContract:
    """Domain-type sugar: declare an email contract in user vocabulary.

    MANDATE §4: the contract is the user's language. This factory returns
    a configured CanonicalEmailContract value object; it does NOT subclass
    it (preserves all isinstance checks and @attrs.frozen immutability).
    Field defaults mirror CanonicalEmailContract's own defaults exactly.
    """
    return CanonicalEmailContract(
        lowercase=lowercase,
        strip_whitespace=strip_whitespace,
        provider_aliases=provider_aliases,
        strict=strict,
    )
```

**Defaults invariant.** The four factory kwargs (`strict=False`, `provider_aliases="none"`, `lowercase=True`, `strip_whitespace=True`) **exactly** match `CanonicalEmailContract`'s own field defaults. A unit test asserts `Email().strict == CanonicalEmailContract().strict` (and the other three) and that `isinstance(Email(), CanonicalEmailContract)` is `True`.

**Why a factory and not a subclass.** Subclassing a `@attrs.frozen` class creates a new abstraction that must satisfy Law 11. A factory is not an abstraction — it returns an existing value object whose Law 11 defense is already on record in the v1.0.0 design spec (2026-07-13-email-canonicalization-design.md §3.2). The factory pattern generalises cleanly to `Money()`, `Date()`, and the north-star multi-field form `InvoiceContract(vendor_email=Email(), ...)` — each future type is one factory, no new abstraction class.

**Why a factory and not the contract class directly.** `CanonicalEmailContract` is implementation vocabulary (the v1.0.0 spec name). `Email` is user vocabulary (the issue's criterion 6 — user expresses intent through contracts, not capabilities). The factory bridges the two vocabularies without duplicating the value object.

**`EmailCapability` stays put.** Do NOT add `EmailCapability` to `paxman.__all__`. It remains documented only in the README's "Extending Paxman" section. The grep-zero gate for the word `Capability` outside "Extending Paxman" in `README.md` is a hard CI test.

**Laws preserved.** Law 5 (contract is truth — `Email()` IS a `CanonicalEmailContract`), Law 7 (Explicit Over Clever — no `auto_detect` knob), Law 13 (returns an immutable `@attrs.frozen` instance).

### 2.3 `parse_contract` accepts a contract instance

**Surface.** One branch added at the top of `parse_contract` in `_contracts/contract.py`.

```python
def parse_contract(spec: Any) -> Contract:
    # New: short-circuit for an already-parsed contract value object.
    # Exact-type check (not `isinstance(spec, Contract)`) so future
    # multi-field contract types are NOT silently absorbed here.
    if isinstance(spec, CanonicalEmailContract):
        return spec

    if not isinstance(spec, dict):
        raise ContractError(f"contract must be a dict, got {type(spec).__name__}")
    # ... existing dict-DSL path unchanged ...
```

**Exact-type, not parent-type.** The check is `isinstance(spec, CanonicalEmailContract)`, NOT `isinstance(spec, Contract)`. `Contract` is currently aliased to `CanonicalEmailContract` (line 57 of the current file), but the parent-type form would falsely match a future `InvoiceContract` (the north star) and silently skip the multi-field contract path. Criterion 10 requires the architecture not preclude the north star; the exact-type check is how this design honours that.

**Why `Contract` is the alias and not a base class.** `Contract = CanonicalEmailContract` (line 57) is a type alias today, not a base class. There is no `class Contract` to `isinstance` against. The exact-type check is the only correct form.

**Automatically fixes `replay(..., Email())` too.** Both `canonicalize` and `replay` call `parse_contract`. With the short-circuit in place, `replay(artifact, Email())` works without touching `replay.py`.

**Dict-DSL path unchanged.** The existing `isinstance(spec, dict)` branch, the `kind` discriminator, the `_KIND_DISPATCH` lookup, the bool-field validation, the `provider_aliases` enum check — all unchanged. The dict DSL remains a first-class contract form. A user who prefers the dict form pays no cost.

**Laws preserved.** Law 5 (contract is truth — the value object is truth, the dict is one serialisation of it), Law 8 (fail informatively — invalid specs still raise `ContractError`), Law 11 (no new abstraction).

### 2.4 Lazy built-in capability loading

**Surface.** Three insertions.

(a) `_capabilities/builtins/__init__.py` gains a helper:

```python
from paxman._capabilities.builtins.email import EmailCapability


def builtin_capabilities() -> list[Capability]:
    """The list of built-in capability instances Paxman ships with.

    MANDATE §4.3: built-ins stay in core. This list is the single source
    of truth for "what built-ins does this version ship?" The orchestrator
    loads them lazily on the first canonicalize call (Law 8a: no import-time
    side effects).
    """
    return [EmailCapability()]
```

(b) `CapabilityRegistry` in `_capabilities/registry.py` gains a method:

```python
def load_builtins(self, builtins: list[Capability]) -> None:
    """Register built-in capabilities whose names are not already present.

    Idempotent, order-independent, and a no-op on a frozen registry.
    Pre-existing user capabilities of the same name are preserved
    (never overwritten) — the user's knowledge wins over Paxman's.

    Skipping a name that is already registered is NOT a ConfigurationError:
    the user *intentionally* registered an "email" capability before their
    first canonicalize and that registration is the one that wins.
    """
    if self._frozen:
        return
    existing = set(self._capabilities.keys())
    for cap in builtins:
        if cap.name not in existing:
            self._capabilities[cap.name] = cap
```

(c) `_core/orchestrator.py` inserts one line at the freeze site:

```python
registry = _orchestrator_runtime.default_registry
if not registry.is_frozen:
    from paxman._capabilities.builtins import builtin_capabilities
    registry.load_builtins(builtin_capabilities())
    registry.freeze()
```

**Ordering invariant (load → freeze → resolve).** `load_builtins()` runs BEFORE `freeze()`. After `freeze()`, any further load/register is a no-op or `FrozenRegistryError` — the capability set is now part of the determinism invariant (Law 1). Resolve executes against the now-frozen, fully-populated registry.

**Why `load_builtins` does NOT raise on duplicate name.** A user who registers a custom `email` capability before their first canonicalize is exercising Law 6 — they are teaching Paxman new deterministic knowledge. Their `register_capability(MyEmailCapability())` call lands before `load_builtins`, so `MyEmailCapability.name == "email"` is already in the registry. `load_builtins` sees the existing entry and skips. The user's knowledge wins; the built-in is silent. This is the §5.3 litmus ("users may teach Paxman new facts") made mechanical.

**Why `load_builtins` is a no-op on a frozen registry, not a raise.** The orchestrator only calls it when `not registry.is_frozen`, so the no-op branch is defense in depth, not the happy path. A raise would be a Law 8 violation (an exception, not a `Status`) for what is at worst a redundant call. The no-op is consistent with `freeze()`'s own idempotency.

**`capabilities_hash` includes both user and built-in.** The hash is `sha256("\n".join(sorted(self._capabilities.keys())))`. After `load_builtins`, both user-registered and built-in capability names are in `_capabilities`; `capabilities_hash` reflects both. `replay` recomputes the same hash from the same `default_registry` and matches. No change to `replay.py` is required.

**Laws preserved.** Law 1 (capability set frozen before first canonicalize, recorded on the artifact's `VersionStamp`), Law 8a (no import-time side effect — the `_capabilities/builtins/__init__.py` module does NOT call `register_capability` at import; the import is performed lazily inside the orchestrator's freeze step), Law 6 (Paxman owns the algorithm — built-in loading happens inside the orchestrator, not as user-visible API), §5.4 (resolution uniqueness holds — two claimants still produce `Status.AMBIGUOUS`).

**Why the import is inside the orchestrator, not at module top.** Importing `builtin_capabilities()` at the top of `orchestrator.py` would import `EmailCapability`, which imports `CanonicalEmailContract` from `_contracts/contract.py`. `_contracts/contract.py` is imported by `_core/orchestrator.py` already (line 26: `from paxman._contracts.contract import parse_contract`). The lazy import inside the `if not registry.is_frozen` branch avoids both an import cycle risk and a premature module evaluation at orchestrator-import time (Law 8a defense in depth).

---

## 3. The Quickstart and the README

### 3.1 The repo-root `quickstart.py`

A ~15-line file at the repo root using only `import paxman` and `from paxman import Email`. No private-module imports. No `register_capability` for the built-in. The example exercises:
- mixed-case input (e.g. `"  John.Doe@Gmail.COM  "`),
- the `Email(provider_aliases="gmail")` factory form,
- `print(result.status.name, "->", result.value)`,
- `print("evidence:", [(e.rule, e.detail) for e in result.evidence])`,
- `rehydrated = paxman.replay(result, Email(provider_aliases="gmail"))`,
- `assert rehydrated == result`,
- `print("replay ok")`.

The exact evidence rule names are *derived by running* against the real `EmailCapability`, not hardcoded in the spec — they are an output of the implementation, not an input to it.

### 3.2 The README Quickstart section

Replaces the current `## Public API` snippet in `README.md`. Contains the exact code from `quickstart.py` in a fenced ```python block, followed by the expected printed output:
```
CANONICALIZED -> <value>
evidence: [(...)]
replay ok
```

The README fenced code block and `quickstart.py` are **byte-for-byte equal** for the code region. A CI test (`test_five_minute_promise.py`) extracts the fenced block from README, extracts the code from `quickstart.py`, and asserts `code_a == code_b`. Drift between README and `quickstart.py` fails CI.

### 3.3 The README "Extending Paxman" section

New. Documents:
- The `Capability` Protocol (the SPI shape).
- `paxman.register_capability(...)` as the SPI entry point.
- Where `EmailCapability` lives (`paxman._capabilities.builtins.email`).
- The freeze constraint: "**Because the registry freezes on the first `paxman.canonicalize(...)` call, register custom capabilities BEFORE your first canonicalize in the process. Calling `register_capability` after the first canonicalize raises `FrozenRegistryError`.**"

The word `Capability` appears in README.md ONLY within this section. A CI test (`test_readme_capability_section_isolation.py`) reads README, splits at the `## Extending Paxman` heading, and asserts the substring `Capability` (case-sensitive) yields zero matches in everything before that heading. This makes the issue's criterion 6 a hard CI gate, not a manual review.

### 3.4 What the Quickstart does NOT contain

- The word `Capability` (criterion 6).
- Any `from paxman._...` import (criterion 4).
- Any `register_capability` call for the built-in (criterion 5).
- Any reference to "heuristic", "approximate", "best effort", "probably", "confidence" (MANDATE §6.3).
- Any `Engine` / bootstrap abstraction (§4.3, Law 6).

---

## 4. The test plan

All test files land under `tests/integration/` (gated by the existing `test-integration` CI job) or `tests/unit/` (gated by `test-unit`). There is no Makefile; CI gating is achieved via those jobs. No `tests/fixtures/` directory is created (repo convention; `.coderabbit.yaml` and `PROPOSED_STRUCTURE.md` both forbid it).

### 4.1 `tests/integration/test_five_minute_promise.py`

- Extracts the fenced ```python block from `README.md`'s Quickstart section.
- Extracts the code from `quickstart.py`.
- Asserts `code_from_readme == code_from_quickstart` byte-for-byte for the code region (hard gate; criterion 1's "single source of truth").
- `exec(...)`s the code, capturing stdout.
- Asserts stdout contains `CANONICALIZED ->`, `evidence:`, `replay ok`.
- Asserts `rehydrated == artifact` and byte-equality via `artifact.canonical_bytes() == rehydrated.canonical_bytes()`.

**Autouse fixture.** Replaces `paxman._orchestrator_runtime.default_registry` with a fresh `CapabilityRegistry()` per test via `monkeypatch.setattr(_orchestrator_runtime, "default_registry", CapabilityRegistry())` (yield-and-restore if `monkeypatch` is not the fixture in scope). This proves the "novice does nothing" path: each test starts with an empty, unfrozen registry, the orchestrator's `load_builtins()` is the only thing that wires `EmailCapability` in, and the test asserts the canonicalize succeeds. There is **no** `reset()`/`clear()`/`unregister()` method on `CapabilityRegistry`; the fixture uses `monkeypatch.setattr`, not a method that does not exist.

### 4.2 `tests/unit/test_normalize_teaching_error.py`

- `with pytest.raises(AttributeError): getattr(paxman, "normalize")` (never the literal `paxman.normalize`).
- Assert the raised message contains `canonicalize`.
- Assert the message does NOT contain the substring `paxman.normalize` (grep-zero gate includes the message string itself; §1.1 identity boundary).
- For any other missing name (`getattr(paxman, "definitely_not_a_function")`), assert a plain `AttributeError` is raised without a teaching message.

### 4.3 `tests/unit/test_email_factory.py`

- `Email().strict == CanonicalEmailContract().strict` (and the three other fields).
- `isinstance(Email(), CanonicalEmailContract)` is `True`.
- `Email(provider_aliases="gmail").provider_aliases == "gmail"`.
- `Email()` is `@attrs.frozen`-equivalent: assigning to `Email().strict` raises `attrs.exceptions.FrozenInstanceError`.
- The factory is callable with all four kwargs as keyword-only (e.g. `Email(strict=True)` works; `Email(True)` raises `TypeError`).

### 4.4 `tests/unit/test_parse_contract_short_circuit.py`

- `parse_contract(CanonicalEmailContract())` returns the same instance (identity equality is acceptable since the contract is frozen; equality is the stronger check and also holds).
- `parse_contract(Email())` returns a `CanonicalEmailContract` equal to `Email()`.
- `parse_contract(Email(provider_aliases="gmail"))` preserves the `provider_aliases` field.
- A non-Contract, non-dict input (e.g. `parse_contract("not a contract")`) still raises `ContractError`.
- A dict with an unknown `kind` still raises `ContractError` (dict-DSL path unchanged).
- A dict with a valid `kind` still parses into a `CanonicalEmailContract` (regression guard).

### 4.5 `tests/unit/test_load_builtins.py`

- `CapabilityRegistry().load_builtins([EmailCapability()])` registers `EmailCapability` under `"email_canonicalization"`.
- Calling `load_builtins` twice with the same list is a no-op (idempotent).
- A user-registered capability of the same name (e.g. `MyEmailCap` with `name="email_canonicalization"`) registered BEFORE `load_builtins` is preserved — `load_builtins` does NOT overwrite it.
- `load_builtins` on a frozen registry is a no-op (does not raise).
- After `load_builtins` + `freeze`, `capabilities_hash()` is the same as if the built-in had been registered via `register` — determinism is preserved.

### 4.6 `tests/integration/test_readme_capability_section_isolation.py`

- Reads `README.md`.
- Splits at the `## Extending Paxman` heading.
- Asserts the substring `Capability` (case-sensitive) appears ZERO times in the section BEFORE `## Extending Paxman`.
- Asserts the substring `Capability` appears at least once in the `## Extending Paxman` section (otherwise the section is missing the SPI documentation).

### 4.7 `tests/unit/test_grep_zero_normalize.py`

- Reads every `.py` file under `src/paxman/` and `tests/`.
- Asserts the literal substring `paxman.normalize` appears ZERO times.
- This is the §1.1 + Law 8a + criterion 7 grep-zero gate, made mechanical.

### 4.8 `tests/integration/test_five_minute_100_emails.py`

- A sibling data module `tests/integration/_five_minute_data.py` holds exactly 100 email strings, **deterministically constructed in-source** (no random; no `tests/fixtures/`; no external file reads; the categorization breakdown is fixed in the module):
  - 95 canonicalizable inputs: lowercase mixed-case variants, gmail.com↔googlemail.com alias mappings under `provider_aliases="gmail"`, ASCII whitespace-padded variants, plus-tag (`+`) variants under the gmail alias policy.
  - 5 invalid inputs: one missing `@` sign, one empty local part (`"@example.com"`), one empty domain part (`"user@"`), one non-ASCII character in the local part, one leading/trailing whitespace under `strict=True`.
- For each of the 100 inputs, runs `paxman.canonicalize(email, Email(provider_aliases="gmail"))` through the same autouse fresh-registry fixture as `test_five_minute_promise.py`.
- Asserts exactly 95 `Status.CANONICALIZED` and 5 `Status.INVALID` (count by status; resilient to input ordering).
- Asserts every `CANONICALIZED` artifact round-trips through `replay` byte-equal.

### 4.9 Regression: the existing public-API exact-set test

`tests/unit/test_public_api.py` asserts `paxman.__all__ == [<exact list>]`. The list grows by one symbol: `Email`. The test must be updated to include `Email`. No other public-surface change. `EmailCapability` is NOT added to `__all__`.

---

## 5. Invariants preserved (and tested)

| Invariant (mandate) | Mechanism | Test |
|---|---|---|
| §1.1 Not a normalizer — no `normalize` attribute | PEP 562 `__getattr__` raises `AttributeError` for `name == "normalize"`. No `def normalize`. | `test_grep_zero_normalize.py`, `test_normalize_teaching_error.py` |
| §1.2 Identity — only canonicalize | The only public callable that produces an artifact is `paxman.canonicalize`. | Existing `test_public_api.py` + new symbol `Email` |
| §1.2 Determinism — same inputs → same artifact | Registry freezes before first resolve; `load_builtins` runs before `freeze`; capability set is part of `VersionStamp`. | `test_load_builtins.py`, existing `test_orchestrator.py` |
| §1.2 Replay — byte-equal rehydration | `replay` recomputes `capabilities_hash` from the same `default_registry` (now including the built-in); no change to `replay.py`. | `test_five_minute_promise.py`, existing `test_replay.py`, `test_replay_invariant.py` |
| Law 2 — Idempotence | Neither `Email()` nor `parse_contract` short-circuit nor `load_builtins` are part of the canonicalize input; canonicalize is unchanged. | Existing `test_idempotence_invariant.py` |
| Law 5 — Contract is truth | `Email()` IS a `CanonicalEmailContract`; `parse_contract` accepts the value object directly. | `test_parse_contract_short_circuit.py`, `test_email_factory.py` |
| Law 7 — Explicit Over Clever | `Email(*, strict=False, provider_aliases="none", lowercase=True, strip_whitespace=True)` — no `auto_detect`, no `infer_provider`. | `test_email_factory.py` (kwarg shape) |
| Law 8 — Fail informatively | The teaching `AttributeError` is informative; `parse_contract` short-circuit accepts valid contracts, rejects invalid dicts with the same `ContractError` as before. | `test_normalize_teaching_error.py`, `test_parse_contract_short_circuit.py` |
| Law 8a — No import-time hidden state | `builtin_capabilities()` is import-time-evaluated but not import-time-applied. The orchestrator applies it on first canonicalize, never at `import paxman`. | `test_load_builtins.py` (call timing) |
| Law 9 — Evidence over confidence | Quickstart prints `evidence: [(rule, detail), ...]`, never a score. | `test_five_minute_promise.py` (asserts `evidence:` in stdout) |
| Law 11 — Every abstraction preserves determinism | No new abstraction is introduced. `Email()` is a factory (returns existing value object). `builtin_capabilities()` is a list-returning helper. `load_builtins()` is a method on an existing class. The PEP 562 `__getattr__` is module-level, not a new abstraction. | (No new abstraction to test for Law 11 specifically; the existing tests cover the underlying classes.) |
| Law 12 — Replay byte-equality | `test_five_minute_promise.py` asserts `rehydrated == artifact` and `canonical_bytes()` equality. | `test_five_minute_promise.py` |
| Law 13 — Artifact immutability | `Email()` returns an `@attrs.frozen` instance; no setter added. | `test_email_factory.py` (assign raises `FrozenInstanceError`) |
| §5.4 — Capability resolution uniqueness | `load_builtins` registers built-ins; if a userByEmail of the same name pre-exists, the user's wins; if two capabilities claim the same pair after `load_builtins`, the orchestrator still produces `Status.AMBIGUOUS`. | `test_load_builtins.py`, existing `test_uniqueness_invariant.py` |
| §6.3 — Adopted vocabulary, retired vocabulary absent | README Quickstart contains zero retired words; `test_grep_zero_normalize.py` extends the existing grep-zero gate. | `test_grep_zero_normalize.py`, existing grep tests |

---

## 6. The 22 → 23 public API delta

The current `paxman.__all__` has 22 symbols (per the 2026-07-13 email spec §4). This milestone adds **one** symbol: `Email`. The new `__all__` has 23 symbols.

| Symbol | Status | Notes |
|---|---|---|
| `Email` | **NEW** | Factory, top-level re-export. |
| `CanonicalEmailContract` | UNCHANGED | Still public; `Email()` returns one. |
| `Capability` | UNCHANGED | SPI; only documented under "Extending Paxman" in README. |
| `CapabilityRegistry` | UNCHANGED | Has `load_builtins()` method added (new method on existing public class — backward-compatible). |
| `parse_contract` | UNCHANGED signature, widened acceptance | Accepts `CanonicalEmailContract` instance AND dict. |
| `canonicalize` / `replay` / `register_capability` | UNCHANGED | |
| All other symbols | UNCHANGED | |

`EmailCapability` is **not** added to `__all__`. It remains importable from `paxman._capabilities.builtins.email` for the SPI path only.

---

## 7. Criterion 10 — north-star reachability, deferred

Issue criterion 10 requires that "ADR-0017 records an explicit decision about how the contract references the canonical type per field... The decision must be one that extends to multi-field contracts without a rewrite."

**Maintainer directive:** no ADR until v2 is stable and fulfils the promise. Criterion 10's *proof* in an ADR is therefore deferred.

The implementation makes three choices that do not preclude the north star:
1. `Email()` is a factory returning a single-field `CanonicalEmailContract`. A north-star `InvoiceContract` would be a frozen attrs class with `vendor_email: CanonicalEmailContract = Email()` as one field — the factory pattern composes.
2. `parse_contract` short-circuits on **exact type** `CanonicalEmailContract`, not the `Contract` alias. A north-star `InvoiceContract` would not be absorbed by the single-field short-circuit; it would require its own dispatch branch (or a multi-field orchestrator path — out of scope here, landable later).
3. `load_builtins` is generic over a list of capabilities — adding `DateCapability()` to the list is a one-line change in `builtin_capabilities()`. The loading mechanism scales north-star without rework.

The milestone close-out will record criterion 10 as "deferred per maintainer directive; tentative choices made do not preclude the north star; proof deferred to a future ADR." All 10 criteria are accounted for; criterion 10 is the only one whose full acceptance is explicitly deferred.

---

## 8. Exit verification

The milestone is delivered when ALL of the following are true.

1. `git clone && uv sync && uv run python quickstart.py` succeeds on first run.
2. `uv run pytest tests/integration/test_five_minute_promise.py` passes — the README snippet executes and round-trips byte-equal.
3. `uv run pytest tests/unit/test_normalize_teaching_error.py` passes — `normalize` raises an informative `AttributeError` containing `canonicalize`.
4. `uv run pytest tests/unit/test_email_factory.py` passes — `Email()` defaults match `CanonicalEmailContract` defaults; factory is `@as.frozen`-immutable.
5. `uv run pytest tests/unit/test_parse_contract_short_circuit.py` passes — `parse_contract` accepts `CanonicalEmailContract` and `Email()` instances.
6. `uv run pytest tests/unit/test_load_builtins.py` passes — `load_builtins` is idempotent, no-op on frozen, preserves user capabilities of the same name.
7. `uv run pytest tests/integration/test_readme_capability_section_isolation.py` passes — `Capability` appears in README only under `## Extending Paxman`.
8. `uv run pytest tests/unit/test_grep_zero_normalize.py` passes — `paxman.normalize` substring is absent from `src/` and `tests/`.
9. `uv run pytest tests/integration/test_five_minute_100_emails.py` passes — exactly 95 `CANONICALIZED` / 5 `INVALID` from the deterministic 100-email set.
10. The existing `tests/unit/test_public_api.py` passes with the one-symbol addition (`Email`).
11. The existing `tests/property/test_replay_invariant.py`, `test_idempotence_invariant.py`, `test_uniqueness_invariant.py`, `test_artifact_immutability_invariant.py`, `test_canonicalization_invariant.py` all pass — the 13 laws are not violated.
12. The existing grep-zero gate for the retired vocabulary (§6.3: `heuristic`, `approximate`, `best effort`, `probably`, `confidence`) across `src/paxman/` continues to pass.
13. The milestone close-out comment on issue #137 explicitly records that criterion 10 is deferred per maintainer directive.

If any item fails, the work is not complete.

---

## 9. Open decisions, by mandate section

| Decision | v2.0.x answer | Mandate section that fixes it |
|---|---|---|
| Is there an `Engine` abstraction? | No. `paxman.canonicalize(...)` is the one API. | §4.3, Law 6 |
| Are built-ins loaded at import? | No. Loaded on first canonicalize, before `freeze()`. | Law 8a, Law 1 |
| Is `Email` a class or a factory? | Factory returning `CanonicalEmailContract`. | Law 5, Law 13 |
| Does `parse_contract` accept contract instances? | Yes — exact-type `CanonicalEmailContract` short-circuit. | Law 5, Law 8 |
| What is the `normalize` error form? | `AttributeError` from PEP 562 `__getattr__`, message contains `canonicalize`. | §1.1, Law 8 |
| Is `EmailCapability` exported at top level? | No. SPI only, documented under "Extending Paxman". | §6.3, criterion 6 |
| Is the README Quickstart enforced against `quickstart.py`? | Yes — byte-for-byte equality gated by CI. | criterion 1 |

**Decisions NOT made in this spec (and why):**
- ADR-0017 — maintainer directive: no ADR until v2 is stable.
- Multi-field contract shape — issue non-goal #2.
- New canonical types beyond Email — issue non-goal #1.
- PyPI release — issue non-goal #6.
- The exact composition of the 100-email dataset's 95 canonicalizable + 5 invalid inputs — implementation detail, fixed by the data module's deterministic construction; categorization breakdown is recorded in §4.8 of this spec to constrain the implementation without overdetermining it.
# ADR-0012: V1 Capabilities Self-Register on Import

> **Status:** Accepted
> **Date:** 2026-07-01
> **Deciders:** Paxman core team
> **Supersedes:** — (clarifies the implicit asymmetry in [ADR-0007](./0007-contract-adapter-set-v1.md))
> **Superseded by:** —

## Context and Problem Statement

Paxman V1 ships exactly **5 built-in capabilities** (`text_extraction`,
`regex_extraction`, `lookup`, `inference`, `validation`) and **4 built-in
contract adapters** (`pydantic`, `json_schema`, `dict_dsl`, `openapi`).
The two registries are structurally parallel — both are
process-local `dict` tables keyed by `(id, version)` or
`format_id` — but V1.0.0/V1.0.1 ship them with **asymmetric
self-registration behaviour**:

- **Contract adapters** — all 4 (`pydantic.py:611`, `json_schema.py:775`,
  `dict_dsl.py:835`, `openapi.py:521`) end with
  `def _register_on_import(): registry.register(<Adapter>(), replace=True); _register_on_import()`.
  Importing `paxman.contract.adapters.*` populates the registry
  automatically.
- **Capabilities** — only **1 of 5** self-registers. `lookup.py:276-282`
  has the same hook; the other four (`text_extraction`, `regex_extraction`,
  `inference`, `validation`) do not. `v1/__init__.py` (post-#71) documents
  this asymmetry as intentional: "the rest (text_extraction,
  regex_extraction, inference, validation) are not part of the default
  registry; they must be registered explicitly by the user."

The asymmetry is **not deliberate** — it accumulated across the V1.0.0
sprints and was never resolved by an ADR. PR #71 (V1.1.0 format
extractors) corrected a misleading docstring that claimed all V1
capabilities self-registered, and explicitly punted the design question
to a follow-up issue (this ADR).

Concretely, the asymmetry forces callers and tests into a state that is
unique to capabilities but not to adapters:

```python
# Contract adapters — works without any registration call:
from paxman import normalize, CanonicalContract
normalize(b"…", MyPydanticModel)  # pydantic adapter is already registered

# Capabilities — would fail today without an explicit register() call:
from paxman import normalize
normalize(b"ACME Corp", {"type": "object", "properties": {"name": {"type": "string"}}})
# InvalidContractError(error_code="CAPABILITY_NOT_FOUND") for
# text_extraction, regex_extraction, validation, inference — and
# lookup works only because it self-registers.
```

The two **test fixtures** that exercise the global registry
(`tests/unit/test_planner_heuristics_planner.py:74-83` and
`tests/property/test_planner_determinism.py:109-118`) manually
re-register the 4 non-`lookup` capabilities between tests. If the
test author forgot one, the test would fail with
`CAPABILITY_NOT_FOUND` rather than the failure mode being tested.

The asymmetric shape also has a second-order cost: a reader of
`v1/__init__.py` is told the registry contains a *subset* of the
imported modules. That mental model is **false for adapters and true
for capabilities**, which makes the package harder to learn and the
V1 contract harder to teach.

## Decision Drivers

- **Approachability** (PRD §4.7) — `paxman.normalize()` should work
  out of the box for a caller who has done nothing more than `pip
  install paxman` and `import paxman`. Built-in capabilities should
  be available without manual registration.
- **Symmetry with the adapter side** — the contract adapter
  registry already self-registers uniformly. Splitting the two
  registries on this axis is an avoidable source of cognitive
  overhead.
- **Determinism** (PRD §4.5) — self-registration is deterministic
  given a fixed interpreter version, a fixed Python path, and a
  fixed set of `paxman.capabilities.v1.*` modules. Property tests
  at `tests/property/test_planner_determinism.py` already exercise
  this with `derandomize=True`.
- **Cold-start budget** (PRD §9) — the lazy import at
  `src/paxman/__init__.py:140-160` (PEP 562) defers all public
  symbols except `__version__`. The V1 capabilities only need to
  be loaded once `normalize()` is first called, which is exactly
  the point at which they are needed.
- **Public API stability** (AGENTS.md) — `paxman.register_capability`
  is a public SPI for **third-party** capability registration. The
  ADR must not remove it; the question is only whether it should
  remain required for first-party / built-in V1 capabilities.
- **Test simplicity** — every test fixture that touches the
  capability registry currently re-registers 4 capabilities
  manually. Removing the manual step makes the fixtures shorter
  and removes a class of "forgot to register X" test bugs.

## Considered Options

### Option A — Confirm the asymmetry as intentional (rejected)

Keep the current state: only `lookup` self-registers; the other four
require explicit `register_capability()` calls.

**Pros:**

- No behaviour change.
- Allows a future tier system where `LOCAL_DETERMINISTIC` capabilities
  remain opt-in (no inference, no I/O) and `STRUCTURED_LOOKUP` is
  always available.
- Preserves `register_capability` as a meaningful first-class call
  for **all** capabilities, not just third-party ones.

**Cons:**

- The first thing a new user does (`paxman.normalize(b"...", contract)`)
  fails with `CAPABILITY_NOT_FOUND` on 4 of 5 built-in capabilities.
  The error message does not say "you forgot to register the
  built-ins"; it says "no capability registered for id='text_extraction'",
  which looks like a bug.
- Asymmetric with the contract adapter side, which already
  self-registers uniformly. The two parallel registries should not
  diverge on this axis without an explicit reason.
- The test fixtures are required to know this asymmetry, which is
  institutional knowledge that does not appear in the public docs.
- The `v1/__init__.py` docstring (post-#71) is **technically correct**
  but actively misleading to a first-time reader.

### Option B — All V1 capabilities self-register on import (chosen)

Add the same `_register_on_import()` hook to
`text_extraction.py`, `regex_extraction.py`, `inference.py`, and
`validation.py`. Update `v1/__init__.py` to confirm the now-uniform
behaviour. Update `_bootstrap_v1_capabilities()` in
`capabilities/registry.py` to re-register **all 5** V1 capabilities
uniformly after a `reset()` call.

`paxman.register_capability()` **stays public** — it is the SPI for
third-party capability registration and remains necessary for any
capability outside the V1 built-in set.

**Pros:**

- One uniform rule for the entire package: **first-party V1
  capabilities self-register on import; third-party capabilities
  use `register_capability`**. This is a single coherent contract
  rather than a per-capability exception list.
- Symmetric with the contract adapter side, which already
  self-registers uniformly (4/4 vs the current 1/5 capability case).
- `paxman.normalize(b"...", contract)` works out of the box after
  `import paxman` — which is what every user expects.
- The test fixtures shrink to a single `reset()` call. Test
  brittleness from "forgot to register" disappears.
- The lazy import at `src/paxman/__init__.py:140` is preserved:
  importing `paxman` does not eagerly load the V1 capability
  modules. The V1 modules are loaded when `paxman.normalize()` is
  first called, which is exactly when they are needed.
- `_bootstrap_v1_capabilities` becomes uniform and trivially
  testable: re-import the V1 module and call all five
  `register(..., replace=True)` calls.

**Cons:**

- Slight risk of "implicit import side effects" in user code that
  imports `paxman.capabilities.v1` for typing/inspection purposes
  and accidentally populates the registry. This risk is the same
  one already accepted on the contract adapter side and is
  acceptable because the side effect is **idempotent** (the
  registry's `register(cap, replace=True)` is a no-op for the same
  instance and replays the same `(id, version)`).
- The `paxman.register_capability()` public function becomes a
  no-op for V1 built-ins (it still re-registers with `replace=False`
  if called explicitly, raising `CAPABILITY_ALREADY_REGISTERED` on
  conflict — which is the correct behaviour). This is the same
  status `paxman.register_adapter()` has for V1 built-in adapters
  today; the symmetry is a feature.
- Modules that import `paxman.capabilities.v1.lookup` for testing
  its singleton in isolation still trigger registration of **all
  five** capabilities once `v1/__init__.py` runs. This is a minor
  expansion of the import side effect, but it matches the existing
  contract adapter behaviour.

### Option C — Discovery via entry points (pluggy-style, rejected for V1)

Replace both registries with a `pluggy`-style entry-point system:
third-party packages declare `paxman_capabilities` entry points in
their `setup.py`/`pyproject.toml`, and Paxman discovers them at
runtime. First-party capabilities also declare entry points.

**Pros:**

- Industry-standard plugin discovery (used by pytest, tox, build,
  kedro, devpi).
- No import-time side effects.
- Plugins are decoupled from Paxman's import path.

**Cons:**

- Adds `pluggy` (or a hand-rolled equivalent) as a **core
  dependency** — directly violates `DEPENDENCIES.md` (core ≤ 3
  packages: `attrs`, `typing-extensions`; no pluggy).
- Changes the extension story for both adapters and capabilities
  in a way that is out of scope for V1.1.0.
- Entry-point discovery is **not lazy** in the same way as the
  current lazy import — `importlib.metadata.entry_points()` walks
  every installed distribution's metadata, which adds cold-start
  cost that the PEP 562 lazy import was specifically designed to
  avoid.
- Backward-incompatible for any caller that has already written
  `paxman.register_capability(MyCapability())` — they would have
  to migrate to entry points.

## Decision Outcome

**Chosen option: B — All V1 capabilities self-register on import.**

The change is:

1. Add the `_register_on_import()` hook to the four V1 capability
   modules that lack it (`text_extraction.py`, `regex_extraction.py`,
   `inference.py`, `validation.py`). The hook is the same shape as
   the existing one in `lookup.py:276-282`:
   ```python
   def _register_on_import() -> None:
       from paxman.capabilities import registry
       registry.register(<CapabilityClass>(), replace=True)
   _register_on_import()
   ```
2. Update `v1/__init__.py` to re-document the (now-true) uniform
   behaviour: "All V1 capabilities self-register on import. Third-party
   capabilities use `paxman.register_capability()`." Remove the
   post-#71 caveat that said the four non-`lookup` capabilities are
   not part of the default registry.
3. Update `_bootstrap_v1_capabilities()` in
   `src/paxman/capabilities/registry.py` to re-register **all five**
   V1 capabilities uniformly, replacing the special-case that only
   handled `lookup`.
4. Simplify the two test fixtures
   (`tests/unit/test_planner_heuristics_planner.py:74-83` and
   `tests/property/test_planner_determinism.py:109-118`) to call
   only `reset()` and remove the manual `register(...)` lines.
   The fixture still uses `reset()` to clear any third-party
   registrations from prior tests.
5. Update `docs/reference/extending.md` §2.3 step 4 to make the
   "first-party vs third-party" distinction explicit. The current
   wording implies `paxman.register_capability()` is required for
   all custom capabilities, which is correct for third-party but
   misleading for the V1 built-ins.
6. `paxman.register_capability()` **stays public** and is the
   documented SPI for third-party capability registration. The
   public API snapshot in
   `tests/public_api/test_public_api.py:50` continues to reference
   it; no public surface change is required.

## Consequences

### Positive

- `paxman.normalize(b"...", contract)` works out of the box after
  `import paxman`, with no manual `register_capability()` calls.
  This is the behaviour every first-time user will expect.
- The two parallel registries (capabilities, contract adapters)
  follow the same self-registration rule, eliminating an asymmetric
  mental model.
- Test fixtures shrink by 4 lines each and stop carrying implicit
  knowledge of the V1 capability set. New tests that exercise the
  registry no longer need to know which capabilities are built-in.
- The public API is unchanged: `paxman.register_capability()`
  remains public for third-party extensions. The function becomes
  a no-op for V1 built-ins, which is the same status
  `paxman.register_adapter()` has for V1 built-in adapters.
- The lazy import boundary at `src/paxman/__init__.py:140` is
  preserved: `import paxman` still does not load the V1 modules.
  They are loaded on first call to `normalize()`/`replay()`,
  which is exactly when they are needed.

### Negative

- Importing `paxman.capabilities.v1.lookup` (or any single V1
  module) for inspection or test isolation now also registers the
  other four V1 capabilities. This is a small expansion of the
  import side effect, symmetric with the existing contract
  adapter behaviour (`paxman.contract.adapters.pydantic` already
  triggers the registration of all four adapters).
- Users who want a minimal registry (e.g., a deployment that only
  uses `lookup` and wants to avoid loading `inference`'s
  provider SPI machinery) cannot selectively opt out of V1
  capabilities. This is acceptable for V1 because all 5 V1
  capabilities are required for the heuristic chain; opt-out
  remains possible by not importing `paxman.capabilities.v1` at
  all, which is the same escape hatch that exists today.
- `paxman.register_capability()` for a V1 built-in (e.g.,
  `register_capability(LookupCapability())`) raises
  `CAPABILITY_ALREADY_REGISTERED` because `_register_on_import`
  has already populated the registry. This is the correct
  idempotency behaviour and matches `register_adapter()`. The
  public docstring should be updated to clarify that
  `replace=True` is required to re-register a built-in.

### Neutral

- `paxman.__version__` continues to be the only eagerly-loaded
  symbol on `import paxman`. Cold-start time is unchanged.
- The `_register_on_import` hook fires at module-import time and
  not at function-call time. This is consistent with the contract
  adapter side and is acceptable because the side effect is
  idempotent and contains no I/O.

## Validation

- **Unit test** — `tests/unit/test_capability_spec_registry.py` already
  covers the registry's `register`/`get`/`unregister` behaviour. Add
  one new test that asserts the registry contains all 5 V1
  capabilities after a fresh `import paxman.capabilities.v1` (i.e.,
  after `reset()` followed by an explicit import of the V1 module).
- **Property test** — `tests/property/test_planner_determinism.py`
  continues to pass; the fixture shrinks to `reset()` only and the
  planner determinism guarantee is unaffected (the registry contents
  are part of the planner's input tuple, per ADR-0002).
- **Public API snapshot** — `tests/public_api/test_public_api.py`
  continues to pass; the surface is unchanged. The V1 capabilities
  are not in the public `__all__` (they are subsystem internals,
  per `PACKAGE_STRUCTURE.md` §5.3).
- **End-to-end smoke** — `paxman.normalize(b"ACME Corp", contract)`
  succeeds without any `register_capability()` call. A new
  smoke test in `tests/test_smoke.py` asserts this directly.
- **Documentation** — `docs/reference/extending.md` §2.3 step 4 is
  updated to read:
  > "If your capability is a **V1 built-in**
  > (`text_extraction`, `regex_extraction`, `lookup`, `inference`,
  > `validation`), it is already registered by the time you import
  > `paxman`. If your capability is **third-party**, register it
  > explicitly:
  > ```python
  > paxman.register_capability(MyCapability())
  > ```
  > Use `replace=True` to re-register a V1 built-in (e.g., to
  > subclass it)."

## References

- `src/paxman/capabilities/registry.py:1-278` — registry module
  with `_bootstrap_v1_capabilities` and `reset`.
- `src/paxman/capabilities/v1/lookup.py:276-282` — the only
  pre-existing `_register_on_import` hook.
- `src/paxman/contract/adapters/pydantic.py:611-617`,
  `json_schema.py:775-781`, `dict_dsl.py:835-841`,
  `openapi.py:521-527` — the four contract adapter self-registration
  hooks that already follow the pattern.
- `src/paxman/api/normalize.py:1-454` — the public entry point
  that depends on the registry being populated.
- `src/paxman/__init__.py:140-160` — PEP 562 lazy import that
  defers subsystem loading until `normalize()`/`replay()`.
- `tests/unit/test_planner_heuristics_planner.py:74-83` and
  `tests/property/test_planner_determinism.py:109-118` — the two
  fixtures that will shrink.
- `docs/reference/extending.md:140-260` — the public extension
  guide to be updated.
- ADR-0005 (confidence ownership) — orthogonal; this ADR does not
  change the capability SPI or the Reconciler's authority over
  confidence.
- ADR-0006 (sequential execution) — orthogonal.
- ADR-0007 (V1 contract adapter set) — the precedent for the
  uniform self-registration contract on the adapter side, which
  this ADR extends to the capability side.

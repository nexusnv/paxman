# ADR-0015: V1.1.0 Format-Aware Executor Auto-Dispatch

> **Status:** Accepted
> **Date:** 2026-07-01
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —
> **Related:** [Issue #73](https://github.com/nexusnv/paxman/issues/73) (Approved Design Spec), [Issue #67](https://github.com/nexusnv/paxman/issues/67) (V1.1.0 5-capability-set parent), [PR #71](https://github.com/nexusnv/paxman/pull/71) (V1.1.0 format extractors, sibling slice), [ADR-0001](./0001-field-centric-planning.md) (field-centric planning), [ADR-0005](./0005-confidence-ownership.md) (capabilities do not assign confidence), [ADR-0006](./0006-sequential-execution-v1.md) (sequential execution, no parallel field execution), [ADR-0007](./0007-contract-adapter-set-v1.md) (V1 capability set), [ADR-0011](./0011-format-auto-detection-for-json-schema-dicts.md) (input-side format auto-detection, sibling policy), [ADR-0012](./0012-v1-capabilities-self-register-on-import.md) (built-ins self-register), [ADR-0014](./0014-v1-1-0-cleanup-transforms.md) (V1.1.0 cleanup-transform slice)

## Context and Problem Statement

V1.1.0 shipped three format-aware tier-1 extractors ([PR #71](https://github.com/nexusnv/paxman/pull/71)) — `json_path_extraction@1.0`, `csv_extraction@1.0`, `xpath_extraction@1.0` — that understand structured input bytes and produce format-specific evidence. They self-register on import ([ADR-0012](./0012-v1-capabilities-self-register-on-import.md)) and work correctly when invoked directly. **The executor does not auto-dispatch to them.** A field whose value lives inside a CSV byte string is dispatched to `text_extraction` and `regex_extraction` (the V1.0.0 default tier-1 chain), and the format-aware capabilities are not tried.

The gap is reproducible on `v1.1.0` HEAD: `paxman.normalize(input_data=csv_bytes, contract=dict_dsl_csv_contract)` returns `status=UNRESOLVED` and `unresolved_fields=['supplier', 'amount', 'currency_code']` because the executor does not pick `csv_extraction` for the `supplier` field. The capability is registered; the planner does not route to it.

The V1.1.0 format-extractor slice intentionally stopped at "capability present, not yet wired into the executor" — a scope decision documented in the PR description under "Deferred work" and called out by the Oracle final review. Wiring the executor is a cross-cutting change to `src/paxman/executor/` and `src/paxman/planner/` that requires its own design conversation about field-level format hints.

The user-facing contract must:

1. Stay **opt-in** — a field with no format hint must behave exactly as on `v1.1.0` HEAD (regression-locked by existing tests).
2. **Not collapse to a generic `UNRESOLVED`** when the auto-dispatched capability misses — the V1.1.0 format extractors surface structured `Diagnostic` records, and the executor must preserve them (the "no silent miss" contract).
3. **Be member-agnostic** — the enum of supported formats must be flat and additive, so adding a new format (PDF, YAML, EMAIL, HTML, TSV) is a single-file change and requires no executor / planner / adapter modifications.

This ADR is required per `AGENTS.md` ("Adding a public API surface requires an ADR"). The new `FormatHint` enum is re-exported through `paxman.api.types` and the top-level `paxman` namespace — it is first-party public surface, so the project's documentation discipline applies.

## Decision Drivers

- **Opt-in, additive** — no behavior change for fields without `format_hints`. The V1.0.0 / V1.1.0 contract is regression-locked.
- **Tier-1 only** — the new auto-dispatch only applies to `LOCAL_DETERMINISTIC` capabilities that consume raw input bytes (the V1.1.0 format-extractor family and future analogs). Cleanup transforms (`case_normalization`, `trim_extraction`), `lookup`, `inference`, and `validation` are explicitly out of scope — they do not consume `ctx.raw_input`.
- **Member-agnostic** — the `FormatHint` enum is a flat, additive enum. All consumers iterate the enum or compare against `cap.format_hint` directly; none enumerate the V1.1.0 members as a hard-coded list.
- **Diagnostic preservation** — the auto-dispatched capability's `Diagnostic` records must reach `CandidateResult.diagnostics` unchanged. The "no silent miss" contract from V1.1.0 stays intact.
- **No new core dep, no new tier, no new diagnostic code** — the change is contained inside existing primitives.
- **Determinism** — the new planner step is a pure function of `(field, registry)`. No time, randomness, or external state. Property-tested with Hypothesis `derandomize=True`.
- **Replay reproducibility** — no change to the artifact's serialized form. `EvidenceRef.context` for the format-aware steps carries the same shape it does today; replay is unaffected.

## Considered Options

### Option A — `FormatHint` enum + `CanonicalField.format_hints` + `CapabilitySpec.format_hint` (chosen)

Add a single additive enum (`CSV | JSON | XML` in V1.1.0) at `src/paxman/contract/_format_hint.py`. Add `format_hints: tuple[FormatHint, ...] = ()` to `CanonicalField` and `format_hint: FormatHint | None = None` to `CapabilitySpec`. Add a new planner step `select_format_aware` in `planner/heuristics.py` that:

- Returns `[]` when the field has no `format_hints` (default unchanged).
- Iterates the registered tier-1 specs.
- For each spec with a non-`None` `format_hint` whose value is in `field.format_hints`, emits a `FieldPlanStep` at the head of the chain.
- Uses `spec.format_hint in field.format_hints` membership test — **not** a hard-coded enumeration of the V1.1.0 members.

The four contract adapters (Dict DSL, Pydantic, JSON Schema, OpenAPI) parse the wire form (`"csv"` / `"json"` / `"xml"`) via `resolve_format_hint`, a single helper that looks up `FormatHint(value)` and rejects unknown values with a structured `InvalidContractError(error_code="INVALID_FORMAT_HINT")`.

`FormatHint` is re-exported through `paxman.api.types` and `paxman.__init__` (PEP 562 lazy `__getattr__`).

**Pros:**

- Closes the documented gap with the same opt-in pattern as ADR-0011 (input-side auto-detection). Both policies live on the contract, both default to "no preference."
- Member-agnostic by construction. The enum is flat and additive; the planner's `in` test and the resolver's `FormatHint(value)` lookup are both member-agnostic.
- No new core dep, no new `CapabilityTier`, no new `DiagnosticCode`, no new `Status` value. The change is contained inside existing primitives.
- Pure function — determinism is trivial and property-testable.
- Diagnostic preservation is achieved without code: the planner emits a normal `FieldPlanStep`, and the existing `FieldRunner` already preserves `Diagnostic` records (per `executor/field_runner.py:88-115`).
- All four adapters share a single resolver (`resolve_format_hint`). No duplication.
- Public surface growth is exactly one symbol: `paxman.FormatHint`.

**Cons:**

- Adds a new `CanonicalField` attribute. Existing adapters must be updated to round-trip it. Mitigated by centralizing the parsing in `resolve_format_hint` — each adapter is a 10-line parse block.
- `xpath_extraction` handles BOTH XML and HTML structurally. The format hint is `XML` (the wire form is XML; HTML is a tolerated subset of XML-via-XPath). If a future `html_extraction` capability splits out the HTML-specific path, it would carry `FormatHint.HTML`; the `XML` hint here does not block that future addition. Documented in the spec.
- Sub-formats of the V1.1.0 set (e.g. `TSV` vs `CSV`) are not first-class `FormatHint` members in V1.1.0. A field needing TSV-specific behavior can declare `format_hints=[FormatHint.CSV]` and override the capability's config — the design does not preclude a future `TSV` member, but does not require one in V1.1.0.
- Adds one row to the V1.1.0 public API surface (`paxman.FormatHint`). The public surface is small (29 symbols in V1.0.0; 30 in V1.1.0 post-merge), and the addition is fully documented.

### Option B — Inspect capability name in the planner (rejected)

Have the planner match `cap.id.endswith("_extraction")` or hard-code a mapping `{"csv_extraction": FormatHint.CSV, ...}`.

**Pros:**

- No new public surface.

**Cons:**

- Brittle. A new format-aware capability would silently not be auto-dispatched until someone updates the planner's mapping.
- The capability name is an identifier, not a contract. String-matching it for routing decisions violates the principle that contract semantics live on the contract (`CapabilitySpec`), not the identifier.
- The original issue (#73) explicitly calls this out: "The capability **name** is no longer inspected — the contract lives on the spec."

### Option C — Heuristic: try every format on every field (rejected)

Have the planner try `csv_extraction`, `json_path_extraction`, `xpath_extraction` in order for every `STRING` field and pick the one that returns candidates.

**Pros:**

- Zero contract changes.

**Cons:**

- Wastes capacity. For a 20-field contract, every field runs three format extractors that may all miss. Cost and time both grow.
- Loses format-specific evidence. The artifact can't tell the user "this value came from the CSV column" vs "this value came from a JSON pointer" — the user has to infer from the chain.
- No opt-out. A field that is known to be plain text is still subjected to three extra capability invocations.
- Rejected by the V1 design principle "validation rejects, doesn't guess" — guessing the input format is exactly the kind of magic Paxman is documented to avoid.

## Decision

**Option A.** Add the `FormatHint` enum, the two new attributes (`CanonicalField.format_hints` and `CapabilitySpec.format_hint`), the `select_format_aware` planner step, the four adapter extensions, and the single public-surface re-export. The change is **additive** for every existing call site; no V1.0.0 / V1.1.0 field is affected unless it opts in by declaring `format_hints`.

The V1.1.0 set of `FormatHint` members is exactly three: `CSV`, `JSON`, `XML`. Adding a new member is a single-file change in `src/paxman/contract/_format_hint.py`; no other file changes are required for the dispatch to work, because the planner's `in` test and the resolver's `FormatHint(value)` lookup are both member-agnostic.

The `xpath_extraction` capability declares `format_hint=FormatHint.XML` (the wire form is XML; HTML is a tolerated subset of XML-via-XPath). A future `html_extraction` capability, if it lands, declares `FormatHint.HTML`. The V1.1.0 set does not preclude this.

The cleanup-transform slice ([ADR-0014](./0014-v1-1-0-cleanup-transforms.md)) is **not** affected. `case_normalization` and `trim_extraction` do not declare `format_hint`; they read `ctx.config["value"]`, not `ctx.raw_input`. The format-aware auto-dispatch operates on the upstream tier-1 step; cleanup transforms chain after it, unchanged.

The input-side auto-detection policy ([ADR-0011](./0011-format-auto-detection-for-json-schema-dicts.md)) is **not** affected. ADR-0011 governs how Paxman detects the *input bytes* format when the caller doesn't tell it; this ADR governs how the executor routes a *field* to the right tier-1 capability when the contract declares a format preference. Both policies are opt-in; both default to "no preference."

The new `FormatHint` enum is the **second** opt-in format-related contract in Paxman (the first being ADR-0011). The two are siblings, not overlapping. Both deserve first-class documentation in `docs/concepts/contracts.md` and `docs/concepts/capabilities.md`.

## Consequences

### Positive

- `paxman.normalize(csv_bytes, contract_with_format_hints)` resolves format fields via the matching tier-1 capability, **without** the caller registering the capability manually (ADR-0012 self-registration is in effect).
- A new format-aware capability (e.g. `pdf_extraction@1.0` for V1.2 / V2) lands by: (1) adding the capability module under `src/paxman/capabilities/v1/`, (2) adding a `FormatHint` member in `src/paxman/contract/_format_hint.py`, (3) declaring `format_hint=FormatHint.<MEMBER>` on the new `CapabilitySpec`. **No executor / planner / adapter changes are required.**
- The "no silent miss" contract from V1.1.0 is preserved at the executor level: the auto-dispatched capability's `Diagnostic` records reach `CandidateResult.diagnostics` unchanged.
- The public API surface grows by exactly one symbol (`paxman.FormatHint`). The growth is additive; no V1.0.0 symbol is renamed, removed, or has its signature changed.

### Negative

- The `CanonicalField` `attrs` class gains one attribute. Existing `__attrs_post_init__` invariants get one new check (the format_hints tuple). The check is O(n) where n is the length of the tuple (typically 0-2 in V1.1.0).
- Four adapter files gain ~10 lines of `format_hints` parse logic each. The logic is centralized in `resolve_format_hint`, so the per-adapter cost is the validation boilerplate (list-type check, per-element resolver call, dedupe, tuple construction), not duplicated business logic.
- One new test subdir each under `tests/unit/` and `tests/integration/` (`tests/unit/executor/`, `tests/integration/executor/`). The existing test layout (unit / property / integration / benchmark / public_api) is unchanged.
- The V1.1.0 capability set remains at 10 (the V1.1.0 set is complete: 5 V1.0.0 + 5 V1.1.0). The V1.1.0 public API moves from 29 to 30 symbols with the `FormatHint` re-export.

### Neutral

- No new `CapabilityTier`, no new `DiagnosticCode`, no new `Status` value, no new `FieldType`. The change is contained.
- No new core dependency, no new optional extra. The change is stdlib-only.
- Replay is unaffected. The `FormatHint` attribute is on the `CanonicalField`, which is part of the artifact's serialized contract. The artifact's serialized form is unchanged for fields that do not declare `format_hints`; for fields that do, the new attribute is added to the field's serialized form and a future replay that calls `paxman.replay()` (with a contract that declares the same `format_hints`) reproduces the same plan.

## Validation

The decision is verified by the following evidence:

- **Unit tests** —
  `tests/unit/contract/test_format_hint.py` covers the
  `FormatHint` enum and `resolve_format_hint` resolver
  (member-agnostic lookup, case-insensitive string
  resolution, rejection of unknown values, type
  rejection);
  `tests/unit/contract/test_canonical_field_format_hints.py`
  pins the `CanonicalField.format_hints` attribute
  (default empty tuple, member-agnostic acceptance,
  type-rejection);
  `tests/unit/capabilities/test_spec_format_hint.py` pins
  `CapabilitySpec.format_hint` (default `None`,
  member-agnostic acceptance, tuple-rejection);
  `tests/unit/planner/test_heuristics_format_hints.py`
  pins `select_format_aware` (CSV / JSON / XML dispatch,
  per-capability config keys, member-agnostic source
  check, input-type filter);
  `tests/unit/executor/test_field_runner_format_dispatch.py`
  pins the chain-walk order and the
  Diagnostic-preservation contract at the runner level.
- **Per-adapter round-trip tests** —
  `tests/unit/test_contract_dict_dsl.py`,
  `tests/unit/test_contract_pydantic.py`,
  `tests/unit/test_contract_json_schema.py`,
  `tests/unit/test_contract_openapi.py` cover
  `format_hints` parse + export on each of the four
  adapters.
- **End-to-end integration test** —
  `tests/integration/executor/test_format_dispatch_normalize.py`
  verifies that `paxman.normalize(csv_bytes, contract_with_hints)`
  resolves the supplier field via `csv_extraction`
  without the caller calling
  `paxman.capabilities.registry.register(...)` (the
  ADR-0012 self-registration contract), and that a
  field without `format_hints` is dispatched exactly
  as on v1.1.0 HEAD.
- **Public surface growth** — exactly one new public
  symbol: `paxman.FormatHint` (and the supporting
  `paxman.FormatHintValidationError` /
  `paxman.parse_format_hints` /
  `paxman.resolve_format_hint` for adapter
  writers). The public API snapshot at
  `tests/fixtures/public_api_snapshot.json` is
  regenerated to include the new symbols.
- **`make ci` green** — 10/10 local CI checks pass;
  13/13 GitHub Actions checks pass (lint, format,
  typecheck, pyright, imports, interrogate, bandit,
  pip-audit, test-examples, test-cov ≥ 90 %,
  unit-tests × 3 Python versions, property tests,
  integration tests). Coverage 94.79 %.
- **Member-agnostic design** — the dispatch
  (`spec.format_hint in field.format_hints`) and the
  resolver (`FormatHint(value)`) are member-agnostic
  by construction. Adding a new `FormatHint` member
  is a single-file change in
  `src/paxman/contract/_format_hint.py` plus adding
  the matching capability. No executor / planner /
  adapter changes are required. This is locked in by
  a static-source test in
  `tests/unit/planner/test_heuristics_format_hints.py`
  (`test_member_agnostic_dispatch`) and the pre-PR
  `grep -rn "FormatHint\."` guard that confirms zero
  hard-coded member references in
  `src/paxman/executor/`, `src/paxman/planner/`, or
  `src/paxman/contract/adapters/`.
- **Diagnostic preservation** —
  `tests/unit/executor/test_field_runner_format_dispatch.py::test_diagnostic_preserved_on_format_aware_miss`
  asserts that a format-aware capability miss
  surfaces the capability's `Diagnostic` records on
  the per-field result (PATTERN_NO_MATCH or
  CAPABILITY_INVOKE_FAILED), not a generic UNRESOLVED.
  The V1.1.0 "no silent miss" contract is preserved.

## References

- **Issue #73** — the Approved Design Spec. The plan in `.sisyphus/plans/issue-73-format-aware-executor-auto-dispatch.md` is the source of truth for the implementation.
- **ADR-0001** — field-centric planning. The new `select_format_aware` step emits one `FieldPlanStep` per matching capability, attached to the same per-field plan.
- **ADR-0005** — confidence ownership. The new step does not assign confidence; it only emits `FieldPlanStep` records. The Reconciler remains the sole confidence authority.
- **ADR-0006** — sequential execution. The new step is invoked in the same single-threaded per-field plan build. No parallel execution is introduced.
- **ADR-0007** — V1 capability set. The three V1.1.0 format extractors are unchanged; they gain one `format_hint` declaration on their `CapabilitySpec`.
- **ADR-0011** — input-side auto-detection. Sibling policy; both default to "no preference." Both are opt-in.
- **ADR-0012** — self-registration. The integration test in Task 14 does not call `paxman.capabilities.registry.register(...)`; the test exercises the same public surface that downstream code uses.
- **ADR-0014** — cleanup-transform slice. Not affected. Cleanup transforms do not declare `format_hint`; they chain after the auto-dispatched tier-1 step unchanged.
- **Tests** — `tests/unit/contract/test_format_hint.py`, `tests/unit/contract/test_canonical_field_format_hints.py`, `tests/unit/planner/test_heuristics_format_hints.py`, `tests/unit/capabilities/test_spec_format_hint.py`, `tests/unit/executor/test_field_runner_format_dispatch.py`, `tests/integration/executor/test_format_dispatch_normalize.py`, plus per-adapter round-trip tests in `tests/unit/contract/adapters/`.
- **Docs** — `docs/concepts/contracts.md`, `docs/concepts/capabilities.md`, `docs/howto/add_capability.md`, `docs/reference/package-structure.md`.

# ADR-0014: V1.1.0 Post-Extraction Cleanup Transforms

> **Status:** Accepted
> **Date:** 2026-07-01
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —
> **Related:** [Issue #67](https://github.com/nexusnv/paxman/issues/67) (V1.1.0 5-capability set, parent), [Issue #69](https://github.com/nexusnv/paxman/issues/69) (cleanup-transforms sub-issue, implementation tracker), [PR #71](https://github.com/nexusnv/paxman/pull/71) (V1.1.0 format extractors, sibling slice), [ADR-0005](./0005-confidence-ownership.md) (capabilities do not assign confidence), [ADR-0007](./0007-contract-adapter-set-v1.md) (V1 capability set; this ADR adds 2 more), [ADR-0012](./0012-v1-capabilities-self-register-on-import.md) (all V1 capabilities self-register on import), [Discussion #66](https://github.com/nexusnv/paxman/discussions/66) (proposal)

## Context and Problem Statement

V1.0.0 ships `text_extraction` and `regex_extraction` as the only value-extracting `LOCAL_DETERMINISTIC` capabilities (with `validation` for filter-only). Real users hit two recurring post-extraction gaps that today require hand-rolled regex workarounds:

1. **Case mismatch** — the same supplier name appears as `ACME Corp`, `acme corp`, `Acme Corp` across documents, and reconciler-side equality is brittle.
2. **Trailing/leading junk** — text extraction produces values like `"ACME Corp\n"`, `"  ACME Corp:"`, `"\ufeffACME Corp"`, where real invoices are wrapped in punctuation, BOMs, zero-width spaces, newlines, and trailing colons that the contract's `min_length` constraint routinely rejects.

The proposal in [Discussion #66](https://github.com/nexusnv/paxman/discussions/66) groups these as **post-extraction cleanup transforms** and is the second of two V1.1.0 capability slices (sibling to the format-extractor slice in [PR #71](https://github.com/nexusnv/paxman/pull/71) / [Issue #68](https://github.com/nexusnv/paxman/issues/68)).

This ADR is required per `AGENTS.md` ("Adding a public API surface requires an ADR"). The two new capabilities are **additive** (no changes to `Budget` / `Policy` / `CapabilityContext` / `CapabilityResult` / `DiagnosticCode`; no new `CapabilityTier`; no new core dep), but they are first-party capabilities and the project's documentation discipline is to record every first-party capability behind an ADR.

## Decision Drivers

- **Fill the documented gap** — real users today hand-roll regex cleanup that is correct but verbose and that loses the format-specific evidence context the artifact is supposed to carry.
- **Stdlib only** — no new core dep, no `numpy` / `pandas` / `regex` / `httpx` (per ADR-0007 and `DEPENDENCIES.md`).
- **Consistency with the existing V1 capability shape** — the new capabilities mirror `regex_extraction@1.0` byte-for-byte at the protocol level: `tier=LOCAL_DETERMINISTIC`, `deterministic=True`, `cost_estimate=CostHint(tokens=0, ms=1, usd=0.0)`, `_register_on_import()` self-registration (per ADR-0012), and `CapabilityContext` flowing in unchanged with a `CapabilityResult` flowing out.
- **Configuration-driven input** — the two new capabilities do **not** consume `ctx.raw_input`; they read exclusively from `ctx.config["value"]` (the post-resolution pattern). This is the new shape introduced in V1.1.0 and lets cleanup transforms chain after any format extractor or any tier-1 step.
- **"Validation rejects, doesn't guess"** — an unknown `mode` (for `case_normalization`) is a hard `CAPABILITY_INVOKE_FAILED` diagnostic, never a silent no-op.
- **Determinism** — the new capabilities are pure functions of `(value, config)`. No time, randomness, or external state.
- **Replay reproducibility** — `EvidenceRef.context` carries `{"original_value": ..., "mode": ...}` / `{"original_value": ..., "trimmed_chars": ..., "stripped_count": N}` so replay can reproduce the exact transform without re-invoking the capability.

## Considered Options

### Option A — Two new `LOCAL_DETERMINISTIC` capabilities: `case_normalization` + `trim_extraction` (chosen)

Add two new modules under `src/paxman/capabilities/v1/`:

- `case_normalization@1.0` — `mode ∈ {"lower", "upper", "title", "preserve"}`. Pure `str.{lower,upper,title}`-based. Unknown mode is a hard error.
- `trim_extraction@1.0` — default `chars` is the V1 documented set (whitespace + zero-width + BOM + common-punctuation: `:;.,-_/\|()[]{}`). Caller can override via `ctx.config["chars"]`.

Both follow the existing `regex_extraction@1.0` shape exactly. They accept `("STRING",)` as input types, output `STRING`, and read from `ctx.config["value"]` (not `ctx.raw_input`). Both self-register on import (ADR-0012). Both surface failure modes as `CAPABILITY_INVOKE_FAILED` diagnostics, never as exceptions.

**Pros:**

- Closes the documented gap with the existing V1 capability shape — no new SPI, no new tier, no new public surface beyond the registry.
- Stdlib only (no new core dep). Honors the "no `regex` third-party lib, no `pandas`" rule.
- Pure functions of `(value, config)` — determinism is trivial and property-tested with Hypothesis `derandomize=True`.
- Chain-friendly: `regex_extraction → case_normalization → trim_extraction` works through the `config["value"]` hand-off, with no executor-side change.
- Evidence is replay-faithful: `original_value` and the transform-specific context are recorded so a future replay can reproduce the result without re-running.

**Cons:**

- Adds 2 more rows to the V1 capability matrix. The V1 capability count moves from **8** (5 V1.0.0 + 3 V1.1.0 format extractors) to **10** (the two slices combined). This is by design — both slices are V1.1.0 — and the public API surface (`paxman.normalize` / `paxman.replay`) is unchanged.
- A misspelled `mode` in a contract fails loudly. This is intentional (matches "validation rejects, doesn't guess") but it is a stricter contract than silently passing the value through.
- `case_normalization` does not address Unicode-casing edge cases that go beyond `str.{lower,upper,title}` (e.g., locale-specific case-folding for Turkish dotless I). V1 does not need this; deferred to a future slice if a real use case emerges.

### Option B — Encode cleanup as new options on `validation` and `regex_extraction`

Extend the existing two capabilities with new config keys (e.g., `regex_extraction` with a `case="lower"` flag; `validation` with a `strip_junk=True` flag).

**Pros:**

- Zero new modules. The V1 capability count stays at 8.

**Cons:**

- Conflates two distinct concerns. `regex_extraction` is a value-extraction step; bolting case/trim onto it violates the single-responsibility invariant in `PACKAGE_STRUCTURE.md` §5.4.
- `validation` is a filter-only capability (it returns the input value unchanged per `validation.py:171-188`); adding transformation to it would break the V1 contract that `validation` does not modify the value (per the docstring on `ValidationCapability`).
- The new `case_normalization` and `trim_extraction` are useful independently of regex — they should be chainable after `text_extraction`, `json_path_extraction`, `csv_extraction`, or `xpath_extraction` too. Encoding them in the source-extraction capability forces every upstream step to duplicate the cleanup config, and forces the executor to merge configs across step boundaries.
- The format-extractor slice (PR #71) deliberately kept the format extractors "extractors only" (no transformation) for the same reason. Adding cleanup as separate capabilities keeps that invariant intact.

### Option C — Defer to a third-party "cleanup-capabilities" PyPI package

Ship the two cleanup transforms as `paxman-cleanup` (a separate package) instead of core.

**Pros:**

- Keeps the V1 core surface minimal (5 V1.0.0 capabilities, no V1.1.0 additions).

**Cons:**

- The cleanup transforms are a direct response to the same recurring friction that motivated the V1.1.0 format-extractor slice (PR #71). Shipping them as a third-party package contradicts the project's "first-party-by-default" position for capabilities that close documented gaps.
- The format-extractor slice was already accepted into core for the same reason (closing a documented gap with stdlib-only). Splitting this slice into a third-party package would create an asymmetric "Paxman ships some of the obvious capabilities and not others" surface.
- Third-party capabilities have a different `register_capability()` path; the chain test fixture (in the integration test) would have to opt in to the extra package, fragmenting the test matrix.
- The 4-package core-dep policy and the V1 capability count budget both have headroom; the cost of including 2 more capabilities is zero at the dependency level and small at the documentation level.

## Decision Outcome

**Chosen option: A (two new `LOCAL_DETERMINISTIC` capabilities, `case_normalization` + `trim_extraction`).**

The V1.1.0 capability set grows from **8** to **10** built-in capabilities:

- 5 V1.0.0 originals: `text_extraction`, `regex_extraction`, `lookup`, `inference`, `validation`
- 3 V1.1.0 format-aware extractors (PR #71): `json_path_extraction`, `csv_extraction`, `xpath_extraction`
- **2 V1.1.0 post-extraction cleanup transforms (this ADR): `case_normalization`, `trim_extraction`**

### Per-capability contract

#### `case_normalization@1.0`

- **Tier:** `LOCAL_DETERMINISTIC` (1)
- **Input types:** `("STRING",)`
- **Output type:** `STRING`
- **Deterministic:** `True`
- **Cost:** `CostHint(tokens=0, ms=1, usd=0.0)`
- **Config (read from `ctx.config`):**
  - `"value"` (required, `str`) — the pre-resolved string to normalize.
  - `"mode"` (required, `str`) — one of `{"lower", "upper", "title", "preserve"}`.
- **Evidence:** `EvidenceRef.context = {"original_value": ..., "mode": ...}`.
- **Failure modes (each → `CAPABILITY_INVOKE_FAILED`):**
  - `config["value"]` missing or not a `str`.
  - `config["mode"]` missing or not in the closed set.
- **Never reads `ctx.raw_input`** — the capability ignores the raw input entirely; it is a pure string transform on `ctx.config["value"]`.

#### `trim_extraction@1.0`

- **Tier:** `LOCAL_DETERMINISTIC` (1)
- **Input types:** `("STRING",)`
- **Output type:** `STRING`
- **Deterministic:** `True`
- **Cost:** `CostHint(tokens=0, ms=1, usd=0.0)`
- **Config (read from `ctx.config`):**
  - `"value"` (required, `str`) — the pre-resolved string to trim.
  - `"chars"` (optional, `str`) — literal characters to strip. Defaults to a fixed, documented set: ASCII whitespace (` \t\n\r\v\f`), zero-width spaces (`\u200b\u200c\u200d`), BOM (`\ufeff`), and the common-punctuation set (`:;.,-_/\|()[]{}`).
- **Evidence:** `EvidenceRef.context = {"original_value": ..., "trimmed_chars": [...], "stripped_count": N}`.
- **Failure modes (each → `CAPABILITY_INVOKE_FAILED`):**
  - `config["value"]` missing or not a `str`.
  - `config["chars"]` set to a non-string (a `list`, `int`, `dict`, `bytes`, etc.).
  - `config["chars"]` set to an empty string `""` (a programmer mistake — callers who want the default should omit the key).
- **Note on `chars=None`:** explicitly **not** an error; it is the signal to fall back to the default char set (matches the "no key" case).
- **Never reads `ctx.raw_input`**.

### Why a separate ADR (and a separate ADR number) from the format-extractor slice

[Issue #67](https://github.com/nexusnv/paxman/issues/67) groups the 5 V1.1.0 capabilities into two slices: the 3 format extractors (sub-issue #68, shipped in PR #71) and the 2 cleanup transforms (sub-issue #69, this ADR's slice). The format-extractor slice shipped first and did not create an ADR — the project accepted the slice in PR #71 without an ADR, and the closure note on #68 explicitly says "the design spec was shipped in PR #71". This ADR fills that documentation gap retroactively for the format-extractor slice **and** records the cleanup-transform slice in a single decision record.

The two slices share the same shape (per-module invariant from the V1.1.0 capability set) but have distinct:

- **Failure mode shapes** — format extractors parse input and surface format-specific codes (`INVALID_JSON`, `INVALID_CSV`, `INVALID_XML`, `PATH_NOT_FOUND`, `PATH_UNSUPPORTED`); cleanup transforms validate config and surface `CAPABILITY_INVOKE_FAILED` only.
- **Evidence context shape** — format extractors carry format-specific provenance (`csv_column`, `row_index`, `header`, `xpath`, `json_pointer`); cleanup transforms carry the **post-resolution** pattern (`original_value`, `mode`, `trimmed_chars`, `stripped_count`).
- **Input source** — format extractors read `ctx.raw_input`; cleanup transforms read `ctx.config["value"]`.

The two slices are **blocked-on-shared-evidence** but not blocked-on-shared-code. They share shape, not implementation.

## Consequences

### Positive

- Closes the documented case-mismatch and trailing-junk gaps with stdlib-only code.
- Pure functions; determinism is trivial; replay reproduces the result without re-invoking the capability.
- Chain-friendly: the `config["value"]` hand-off means any tier-1 step can be followed by `case_normalization` and/or `trim_extraction` without executor-side change.
- Honors the project's "validation rejects, doesn't guess" philosophy: an unknown `mode` is a hard error.
- The default `chars` set is documented and fixed; future Python `str.strip()` semantic drift does not silently change V1 behavior.
- Re-uses the V1 capability SPI unchanged: no new public surface beyond the registry.

### Negative

- V1 capability count grows from 8 to 10. This is by design and matches the V1.1.0 capability-set scope; the V1 public API surface (`paxman.normalize` / `paxman.replay`) is unchanged.
- Golden artifacts (`tests/fixtures/artifacts/*.json`) need to be regenerated when new V1 capabilities are added, because the artifact's `capability_versions` list grows deterministically. The bootstrap script (`scripts/bootstrap_golden_artifacts.py`) handles this; the `replay_hash` change is expected and recorded in the slice's PR.
- The cleanup transforms introduce a new "post-resolution input" pattern (`ctx.config["value"]`) that is not yet plumbed through the executor. A follow-up issue is required to wire the executor to dispatch `config["value"]` capabilities automatically. Until then, callers chain the capabilities explicitly via direct `invoke()` calls. The integration test (`tests/integration/capabilities/test_cleanup_transforms_chain.py`) demonstrates the explicit chaining.

### Neutral

- The default `chars` set in `trim_extraction` is opinionated (whitespace + zero-width + BOM + common punctuation). Callers who need a different char set pass `ctx.config["chars"]` explicitly. The default is a deliberate choice, not a bug; it is documented in the module docstring and tested explicitly.
- The `case_normalization` mode set is closed (`{"lower", "upper", "title", "preserve"}`). Future modes (e.g., `sentence`, `camel`, `snake`) are out of V1 scope; each new mode is a new capability or a mode-extension ADR.

## Validation

- `tests/unit/test_capability_case_normalization.py` (≥15 unit tests, per-cap coverage):
  - Spec shape (`tier`, `deterministic`, `cost_estimate`, `input_types`, `output_type`).
  - Happy path for all 4 modes (`lower`, `upper`, `title`, `preserve`).
  - Config validation (missing `value`, missing `mode`, unknown `mode`, non-string `value`, non-string `mode`).
  - Empty / unicode / emoji input.
  - Evidence `context` shape and JSON-serializability.
  - `ctx.raw_input` is not read.
  - Determinism (byte-equal across two invocations).
  - Self-registration on import (ADR-0012).
- `tests/unit/test_capability_trim_extraction.py` (≥15 unit tests, per-cap coverage):
  - Spec shape.
  - Happy path with default `chars` (whitespace, common punctuation, brackets, zero-width / BOM).
  - Happy path with explicit `chars` (single-char, multi-char, chars that don't match the default).
  - Config validation (missing `value`, non-string `chars`, empty `chars`, non-string `value`).
  - `chars=None` falls back to the default (not an error).
  - Empty / unicode input.
  - Evidence `context` shape (with `original_value`, `trimmed_chars`, `stripped_count`).
  - `ctx.raw_input` is not read.
  - Determinism.
  - Self-registration on import.
- `tests/property/test_cleanup_transforms_determinism.py`:
  - `case_normalization`: same `(value, mode)` returns the same candidates, byte-equal (`derandomize=True`, N=100).
  - `trim_extraction`: same `(value, chars)` returns the same candidates, byte-equal.
  - `trim_extraction`: same value with default `chars` returns the same candidates, byte-equal.
- `tests/integration/capabilities/test_cleanup_transforms_chain.py` (≥4 tests):
  - Both new specs are reachable via `paxman.capabilities.registry.get_latest`.
  - The full `regex_extraction → case_normalization → trim_extraction` chain produces a normalized `acme corp` against `tests/fixtures/inputs/sample_invoices.csv`.
  - The chain is byte-equal across two runs (replay reproducibility).
  - `paxman.normalize()` on the same input produces a stable `replay_hash` (the V1 hard invariant; unaffected by the chain step because the executor does not yet auto-wire the cleanup chain).
  - The cleanup transforms do not break the existing `csv_extraction` registration.
  - The `case_normalization` capability fails loudly on an unknown mode (no silent no-op).
- `tests/unit/test_capability_spec_registry.py`:
  - Two new test cases: `test_case_normalization_spec_is_registerable` and `test_trim_extraction_spec_is_registerable` (per the existing per-cap pattern).
  - `_V1_CAPABILITY_IDS` extended from 8 to 10 to include the two new capabilities.
  - `test_v1_1_cleanup_transforms_have_import_time_registration_hook` (sibling to the format-extractor hook test) verifies the per-module `_register_on_import()` invariant.
- `tests/fixtures/artifacts/_catalog.py` — goldens regenerated by `scripts/bootstrap_golden_artifacts.py` to reflect the new `capability_versions` list. The `replay_hash` change is expected and recorded in the PR description.
- `docs/concepts/capabilities.md` §1 and §9 carry the two new rows; §10 cross-references this ADR.
- `docs/adr/index.md` carries the new ADR-0014 row.
- `tests/fixtures/public_api_snapshot.json` is **unchanged** (the new capability classes are not re-exported from `paxman.*`).
- Per-module line coverage ≥ 90% (achieved: 100% on both new modules). Overall `src/paxman/` coverage ≥ 90% (achieved: 94.80%).
- The full 9-check `make ci` pipeline is green on Python 3.11 / 3.12 / 3.13.

## References

- [Issue #67](https://github.com/nexusnv/paxman/issues/67) — V1.1.0 5-capability set (parent)
- [Issue #69](https://github.com/nexusnv/paxman/issues/69) — V1.1.0 cleanup-transforms sub-issue (implementation tracker for this ADR's slice)
- [Issue #68](https://github.com/nexusnv/paxman/issues/68) — V1.1.0 format-extractor sub-issue (sibling slice, shipped in PR #71)
- [PR #71](https://github.com/nexusnv/paxman/pull/71) — V1.1.0 format extractors (sibling slice)
- [ADR-0005](./0005-confidence-ownership.md) — Reconciler is the sole confidence assigner; capabilities never assign confidence.
- [ADR-0007](./0007-contract-adapter-set-v1.md) — V1 contract adapter set; this ADR adds 2 more capabilities to the V1 surface.
- [ADR-0012](./0012-v1-capabilities-self-register-on-import.md) — All V1 capabilities self-register on import; the two new modules honor this invariant.
- [Discussion #66](https://github.com/nexusnv/paxman/discussions/66) — Original proposal
- `src/paxman/capabilities/v1/case_normalization.py` — module (this slice)
- `src/paxman/capabilities/v1/trim_extraction.py` — module (this slice)
- `src/paxman/capabilities/registry.py:_bootstrap_v1_capabilities` — re-registers the new capabilities after a `reset()` call
- `src/paxman/capabilities/v1/regex_extraction.py` — the per-capability shape this slice mirrors
- `src/paxman/capabilities/v1/validation.py` — the existing post-resolution input pattern (`ctx.config["value"]`) this slice builds on
- `tests/integration/capabilities/test_cleanup_transforms_chain.py` — integration test
- `tests/property/test_cleanup_transforms_determinism.py` — property test
- `docs/concepts/capabilities.md` §1 and §9 — public capability catalog

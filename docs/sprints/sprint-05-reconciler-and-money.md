# Sprint 5 — Reconciler + MONEY + Vendoring

> **Duration:** 2 weeks
> **Goal:** Implement the **Reconciler** (the sole confidence authority per ADR-0005), finalize **MONEY arithmetic** (first-class per ADR-0004), and complete the **`scripts/fetch_test_data.py`** implementation so the V1 corpus can be vendored.
> **Status:** This is the sprint where **honest confidence** enters the pipeline. End of sprint: `paxman.normalize()` returns a confidence-scored artifact with explicit `UNRESOLVED` for unresolvable fields.

## Scope (in)

### Reconciler subsystem (`src/paxman/reconciler/`)
- `truth.py` — `TruthLayer` data models (Contract / Candidate / Resolved)
- `confidence.py` — confidence assignment (float 0.0–1.0) and band mapping (`CERTAIN`/`HIGH`/`MEDIUM`/`LOW`/`UNTRUSTED`)
- `merge.py` — candidate merging strategies (union, intersection, prefer-by-evidence)
- `conflict.py` — conflict detection between candidates
- `evidence_compare.py` — evidence quality comparison
- `unresolved.py` — explicit `UNRESOLVED` state handling
- `validation.py` — apply `Validation` capability to inference candidates
- `money.py` — `MONEY` arithmetic, `CurrencyPolicy` (STRICT_MATCH/ALLOW_FX/REJECT_WITHOUT_RATE), Decimal precision
- `reconciler.py` — top-level `reconcile(candidates, contract) -> ResolvedResult[]`

### Test data
- `scripts/fetch_test_data.py` — fully implemented (`vendor_one()` for all 10 V1 datasets)
- `tests/fixtures/DATASET_LICENSES.md` — verified against vendored files
- `tests/fixtures/inputs/adversarial/` — ≥6 edge cases (currently 4; add: large input, truncated, etc.)
- `tests/fixtures/inputs/{invoices,receipts,quotations}/synthetic/` — ≥3 smoke inputs each

### Tests
- Unit tests for all Reconciler modules
- Property tests for MONEY arithmetic (Hypothesis, `Decimal` precision)
- Property tests for Reconciler monotonicity (strictly better evidence never lowers confidence)
- `tests/fixtures/inputs/adversarial/prompt_injection.txt` end-to-end through Reconciler
- Reconciler never assigns confidence in any module outside `reconciler/` (static check via `import-linter` or `ast` walk)

### Tooling
- `import-linter` contract: `reconciler/` may NOT import from `artifact/` or `api/`
- `reconciler/money.py` is the only module that may import `Decimal` (restrict via `import-linter` if needed)

## Scope (out)

- **Artifact** (Sprint 6) — Sprint 5 produces `ResolvedResult[]`, not `ExecutionArtifact`.
- **`paxman.normalize()` API** (Sprint 6).
- **MONEY FX rate sources** (V2) — `ALLOW_FX` requires an explicit `fx_rate` field on the candidate, not a live FX feed.
- **Multi-currency aggregation beyond pairwise** (V2) — V1 supports `MONEY` per field; aggregated MONEY across fields is V2.

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D5.1 | `reconciler/truth.py` | 1.0 |
| D5.2 | `reconciler/confidence.py` — band mapping + assignment | 2.0 |
| D5.3 | `reconciler/merge.py` — 3 strategies | 2.0 |
| D5.4 | `reconciler/conflict.py` | 2.0 |
| D5.5 | `reconciler/evidence_compare.py` | 2.0 |
| D5.6 | `reconciler/unresolved.py` | 1.0 |
| D5.7 | `reconciler/validation.py` (apply Validation capability) | 1.0 |
| D5.8 | `reconciler/money.py` — `MONEY` arithmetic, `CurrencyPolicy`, Decimal precision | 3.0 |
| D5.9 | `reconciler/reconciler.py` — top-level `reconcile()` | 2.0 |
| D5.10 | `scripts/fetch_test_data.py` — `vendor_one()` implemented for all 10 V1 datasets | 3.0 |
| D5.11 | `tests/fixtures/DATASET_LICENSES.md` — verified | 0.5 |
| D5.12 | ≥6 adversarial input fixtures (add `extremely_large.txt`, `truncated_pdf.bin`, `mismatched_currency.txt` already exists) | 1.0 |
| D5.13 | ≥3 synthetic input fixtures per use case (invoices, receipts, quotations) | 1.0 |
| D5.14 | Unit tests for all Reconciler modules | 3.0 |
| D5.15 | Property tests: MONEY arithmetic (Decimal precision, cross-currency) | 1.5 |
| D5.16 | Property tests: Reconciler monotonicity (better evidence → higher confidence) | 1.0 |
| D5.17 | Adversarial test: prompt-injection candidate rejected by Reconciler | 0.5 |
| D5.18 | Static check: only `reconciler/` imports `ConfidenceBand` constructor | 0.5 |
| D5.19 | `import-linter` contract for `reconciler/` | 0.5 |
| D5.20 | `make test-data-verify` works (CI gate) | 0.3 |

**Total: ~25.8 id-ed.** Sized for **3 engineers × 2 weeks** (1 on reconciler, 1 on MONEY, 1 on test data + property tests).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 3 engineers (1 senior with MONEY/Decimal experience, 2 mid-level) | MONEY arithmetic needs care |
| **Tools** | All Sprint 1-4 deps; HuggingFace `datasets` library (dev-only); Git CLI | Standard Python + git |
| **Tests** | Sprint 4 Executor + `lookup` + `inference` capabilities (to feed Reconciler) | Done |
| **Decisions** | `MONEY` rounding mode (`ROUND_HALF_EVEN` aka banker's rounding recommended); Decimal precision default (28 digits, Python's `Decimal` default) | Document in `money.py` module docstring |
| **External** | Disk space: ~50 MB for the V1 corpus + ~200 MB for HuggingFace cache during vendoring | Plan ahead |
| **Docs** | `ADR-0004` (MONEY), `ADR-0005` (confidence), `docs/TEST_DATA.md` (vendoring policy) | Read carefully — MONEY is high-risk |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **datasets** (HuggingFace) | latest | Vendoring CORD, InvoiceBenchmark, alamgirqazi, wildreceipt, OQO, TED | dev-only; never in production deps |
| **GitHub CLI (`gh`)** | latest | Vendoring petstore, JSON-Schema-Test-Suite, Polish Tenders | dev-only |
| **hypothesis** | ≥ 6.0 | Property tests (already dev dep) | Critical for MONEY |
| **pytest-benchmark** | latest | Performance tests (used in Sprint 9) | Dev dep, installed this sprint |

## API keys / secrets

None. All vendored datasets are publicly available under allowed licenses (MIT, Apache-2.0, BSD, CC0, CC-BY-4.0). No HuggingFace API key required for public datasets.

## Exit criteria

1. `reconciler.reconcile(candidates, contract) -> ResolvedResult[]` works end-to-end.
2. The Reconciler is the **only** module that assigns confidence (static test).
3. The Reconciler produces `ConfidenceBand.CERTAIN`/`HIGH`/`MEDIUM`/`LOW`/`UNTRUSTED` based on the float confidence.
4. The Reconciler marks a field `UNRESOLVED` when no candidate meets the field's `confidence_threshold`.
5. The Reconciler detects conflicts between candidates (two candidates with different values for the same field).
6. `reconciler/money.py` arithmetic:
   - `STRICT_MATCH` rejects cross-currency candidates.
   - `ALLOW_FX` requires an explicit `fx_rate` field; arithmetic uses `Decimal` precision (no float).
   - `REJECT_WITHOUT_RATE` rejects when no `fx_rate` is provided.
7. Property test: Reconciler monotonicity — for any two candidate sets where B is strictly better-evidenced than A, every field's confidence in B ≥ A's confidence.
8. Property test: MONEY arithmetic preserves Decimal precision across 100 random MONEY operations.
9. Adversarial test: a prompt-injection candidate (from `prompt_injection.txt`) is rejected by the Validation capability and marked `UNRESOLVED` by the Reconciler.
10. `python scripts/fetch_test_data.py --validate-licenses` is green (no disallowed licenses in the corpus).
11. `make test-data-verify` is green (every vendored file has a `DATASET_LICENSES.md` entry).
12. Test coverage on `reconciler/` ≥ 90%.
13. `mypy --strict src/paxman/reconciler` is clean.
14. `import-linter` is clean.
15. `make ci` is green.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| MONEY arithmetic has subtle rounding errors that only show up in production | High | High | Use Python's `Decimal` with explicit context (precision=28, rounding=`ROUND_HALF_EVEN`). Property test 1000 random MONEY operations. Document rounding mode. |
| The Reconciler's confidence calibration is subjective (PRD R-3) | High | Medium | Document the mapping from evidence characteristics to confidence bands explicitly. Provide a `confidence_calibration.md` doc. Test that the same evidence always produces the same band. |
| The `reconciler/confidence.py` is too aggressive (always returns `UNTRUSTED` for inference candidates) | Medium | Medium | Have explicit per-capability confidence baselines. Document the rubric. |
| The fetch script downloads the wrong file or stale URL | Medium | High | Pin dataset commit SHAs. Verify SHA-256 checksums after download. CI uses `--verify` only. |
| The vendored corpus is too large for some developers' machines | Low | Low | Document the corpus size (~50 MB) in `DEVELOPMENT.md`. Provide a `--minimal` flag for `fetch_test_data.py` to download a 10 MB subset for fast smoke tests. |
| License gating fails for one dataset | Low | High | List allowed licenses in `scripts/fetch_test_data.py`; reject any dataset whose license is not in the allowed list. Use `--dev-only` to bypass (developer only). |
| Reconciler monotonicity test is vacuous (always true) | Low | High | Construct a test that constructs candidate sets A and B where B has a strictly higher-evidenced candidate than A for the same field. The test must fail if monotonicity is broken. |
| `reconciler/money.py` is the bottleneck for Decimal performance | Low | Low | Profile in Sprint 9. For now, correctness > performance. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §1.5, §1.6 (MONEY).
- `../PACKAGE_STRUCTURE.md` §7 — `reconciler/` module spec.
- `../docs/adr/0003-separate-reconciler.md`.
- `../docs/adr/0004-money-first-class-type.md`.
- `../docs/adr/0005-confidence-ownership.md`.
- `../ARCHITECTURE.md` §4.5 — Reconciler responsibilities.
- `../docs/TEST_DATA.md` — 5-layer model, dataset catalog, licensing.
- `../tests/fixtures/DATASET_LICENSES.md` — attribution.
- `../SECURITY.md` §2 — PII handling in test data.

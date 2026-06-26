# Sprint 7+ — Budget / Cost Pipeline `float → Decimal` Intervention

> **Duration:** 1 week (intervention sprint, single-engineer)
> **Goal:** Honor the project's own `"MONEY is Decimal, never float"` directive (AGENTS.md:73, ADR-0004) end-to-end through the cost pipeline. After this sprint, **every USD-denominated value in `src/paxman/` is `Decimal`**, and the asymmetric `Decimal`-typed-but-float-fed `Statistics.total_cost_usd` declaration in `src/paxman/artifact/statistics.py:97` is no longer aspirational.
> **Status:** Pre-implementation. This is the planning deliverable for an **intervention sprint** off the main `sprint-7-integration-and-property-test` branch. End of sprint: `make ci` is green; all existing tests pass with `Decimal` semantics; the philosophical commitment documented in ADR-0004 is reflected in the type system end-to-end.

## Scope (in)

### Source: cost pipeline types
- `src/paxman/budget.py` — `Budget.max_total_cost_usd: float | None` → `Decimal | None` (with `float | int | Decimal | None` accepted at construction and coerced to `Decimal` via `Decimal(str(x))` for backward compatibility with literal-`0.10` callers).
- `src/paxman/budget.py` — `Budget.__attrs_post_init__` validator updated to `Decimal`-correct comparison.
- `src/paxman/capabilities/spec.py` — `CostHint.usd: float = 0.0` → `usd: Decimal = Decimal("0")` (with `float | int` accepted and coerced).
- `src/paxman/capabilities/spec.py` — `CostHint.__attrs_post_init__` updated.
- `src/paxman/executor/budget_tracker.py` — `BudgetTracker.total_cost_usd: float` → `Decimal`; `record(cost_usd=...)`, `would_exceed(cost_usd=...)`, `would_exceed_reason(cost_usd=...)` accept `Decimal` (and `float` for back-compat); the `+ 1e-9` hack in `mark_exhausted` was **removed entirely** — the bump to push the counter strictly above the cap now uses `cap.next_plus()` (the smallest representable `Decimal` increment above the cap, ~1e-28), so the reported amount stays accurate instead of inflating by a whole dollar.
- `src/paxman/executor/budget_tracker.py` — module docstring lines 25-30 ("Future sprints may switch to `decimal.Decimal`") **deleted** and replaced with a one-line note that the switch has happened, citing this sprint.
- `src/paxman/executor/execution_state.py` — `ExecutionState.total_cost_usd: float` → `Decimal`; `record_invocation(cost_usd=...)` accepts `Decimal`; `cost = float(cost_usd)` coercion removed; the "Calling code may pass a Decimal-like object" comment updated or removed.
- `src/paxman/planner/policies.py` — `estimated_chain_cost` returns `Decimal`; `budget_excludes_inference`'s `budget.max_total_cost_usd < 0.001` becomes `Decimal < Decimal("0.001")`.
- `src/paxman/planner/planner.py` — `PlanDiagnostic.context["max_total_cost_usd"]` carries a `Decimal` (no code change needed — JSON serializes `Decimal("0.10")` and `0.10` identically).
- `src/paxman/planner/scoring.py` — **no change**. `score_capability` already casts to `float` at return (`scoring.py:94`); the formula `tier_rank * 10000 + cost.usd * 1_000_000 + cost.ms * 1` works on either `int + Decimal + int` (Python promotes); the explicit `float(...)` at the return keeps the score type-stable.

### Source: testing strategy
- `src/paxman/testing/__init__.py` — `_budget_strategy` updated so `max_total_cost_usd` is drawn from `st.decimals(min_value=0, max_value=10, allow_nan=False, allow_infinity=False, places=4)` (or `st.one_of(st.none(), st.decimals(...))`). The other three caps are int-valued, unchanged.

### Source: factory
- `tests/fixtures/factories/policies.py` — `BudgetFactory.max_total_cost_usd` `LazyAttribute` removes the `float()` wrapper around the `pydecimal` Faker call (so the produced `Decimal` flows through unchanged). The `PolicyFactory.confidence_floor` field is intentionally left as `float` (it's a probability in `[0.0, 1.0]`, not money — this is a defensible exception per `src/paxman/contract/_types.py:355-360`).

### Tests
- All 14+ test files that construct `Budget(max_total_cost_usd=...)` with a float literal **continue to work without changes** because the constructor accepts `float` and coerces. Verified test sites:
  - `tests/unit/test_budget.py` — 5 sites
  - `tests/unit/executor/test_budget_tracker.py` — 10+ sites
  - `tests/unit/executor/test_execution_state.py` — 4 sites
  - `tests/unit/executor/test_field_runner.py` — 3 sites
  - `tests/unit/executor/test_executor.py` — 2 sites
  - `tests/unit/test_planner_scoring_policies.py` — 4 sites
  - `tests/unit/test_planner_heuristics_planner.py` — 2 sites
  - `tests/integration/executor/test_executor_budget.py` — 4 sites
  - `tests/integration/cross_subsystem/test_cross_subsystem_integration.py` — 1 site
  - `tests/integration/end_to_end/test_invoice_pipeline.py` — 1 site
  - `tests/property/test_executor_determinism.py` — 2 sites
  - `tests/unit/api/test_api_normalize.py` — 1 site
- Tests that assert `== 0.0` or `== 0.10` on a cost value **need updating** to `== Decimal("0.0")` or `== Decimal("0.10")`:
  - `tests/unit/test_budget.py:46` — `assert b.max_total_cost_usd == 0.0` → `== Decimal("0.0")`
  - `tests/unit/executor/test_budget_tracker.py:43` — `pytest.approx(0.10)` → use `Decimal("0.10")` and `==` (Decimal comparison is exact for short decimals; `pytest.approx` only works on floats)
  - `tests/unit/executor/test_budget_tracker.py:62` — `pytest.approx(0.05)` → `== Decimal("0.05")`
  - `tests/unit/executor/test_execution_state.py:58,68` — `pytest.approx(...)` → `== Decimal(...)`
  - `tests/unit/executor/test_field_runner.py:405` — `pytest.approx(0.0)` → `== Decimal("0")`
  - `tests/unit/artifact/test_statistics.py:36` — `assert cs.total_cost_usd == 0.0` → `== Decimal("0")`
  - `tests/unit/artifact/test_statistics.py:140` — `assert stats.total_cost_usd == 0.0` → `== Decimal("0")`
- `tests/unit/test_budget.py:78` — `b.max_total_cost_usd = 5.0  # type: ignore[misc]` — change to `Decimal("5.0")`.
- `tests/unit/executor/test_budget_tracker.py:182` and similar — assertion style unchanged (Decimal and float compare equal for the same numeric value via the existing `==` test path).

### Documentation
- `docs/adr/0010-budget-money-decimal.md` — new ADR (the existing `docs/adr/README.md` line 56-61 lists "refactors that don't change behavior" as NOT requiring an ADR; but this refactor is a **type-system change with precision implications** and the existing ADR-0004's "Future sprints may switch" exception is closed here, so a 4-line ADR-0010 is appropriate to record the decision and supersede the exception).
- `CHANGELOG.md` — new `[Unreleased]` entry under `### Changed`.
- `ARCHITECTURE.md:411,428` — quickstart example updated to `Decimal("0.10")`; type table updated to `Decimal | None`.
- `README.md:21` — quickstart example updated to `Decimal("0.10")` (or kept as `0.10` because the constructor still accepts float — leave a one-line note that "Decimal is preferred for new code").
- `docs/specs/capability-cost-model.md:43` — `usd: float` → `usd: Decimal`; field-semantics table updated to `Decimal`; the inference's `usd = 0.001` value unchanged.
- `docs/sprints/sprint-04-executor-and-capabilities.md:113` — risk register entry "Use `Decimal` for cost" mitigation is **removed** (it was a forward-looking note; the risk is now closed).
- `website/index.html:1260,1383,1407` — 3 example code blocks updated to `Decimal("0.10")`.

## Scope (out)

- **Replacing all float arithmetic in the planner with Decimal** (the `score_capability` formula stays `float` because the score is a sortable rank, not money; the V1 weight table is calibrated for float).
- **Multi-currency budget caps** (V2).
- **`Policy.confidence_floor` Decimal conversion** (it's a probability in `[0,1]`, not money; this is a defensible exception per `src/paxman/contract/_types.py:355-360`).
- **Live FX rate feeds** (V2; `CurrencyPolicy.ALLOW_FX` already requires explicit `fx_rate` per `src/paxman/budget.py:21`).
- **Cross-field MONEY aggregation** (V2; per Sprint 5 out-of-scope).
- **A new ADR-0010 that is longer than ~30 lines** — the refactor is small and the existing ADR-0004 already establishes the philosophy; a minimal ADR-0010 is enough.
- **Regenerating the 8 golden artifacts** — they store no budget data (verified by reading all 8 files; no `budget` key).
- **Updating `tests/fixtures/public_api_snapshot.json`** — it captures top-level symbols by name, not class attribute types.
- **A new `paxman_version` bump** — this is behavior-preserving at the JSON level (`0.10` from `float` and `Decimal("0.10")` serialize identically; replay hash unchanged).

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| **D7+.1** | `Budget.max_total_cost_usd: Decimal \| None` with `float` accepted and coerced at construction | 0.3 |
| **D7+.2** | `CostHint.usd: Decimal` with `float \| int` accepted and coerced | 0.3 |
| **D7+.3** | `BudgetTracker` switched to `Decimal` for `total_cost_usd` and all `cost_usd` params; "Future sprints" comment deleted; `+ 1e-9` hack replaced with `Decimal`-clean version | 0.5 |
| **D7+.4** | `ExecutionState.total_cost_usd: Decimal`; `cost = float(cost_usd)` coercion removed | 0.3 |
| **D7+.5** | `planner/policies.py` `estimated_chain_cost` returns `Decimal`; `budget_excludes_inference` uses `Decimal("0.001")` literal | 0.3 |
| **D7+.6** | `testing/__init__.py` `_budget_strategy` uses `st.decimals` for `max_total_cost_usd` | 0.2 |
| **D7+.7** | `factories/policies.py` `BudgetFactory` removes `float()` wrapper around `pydecimal` | 0.2 |
| **D7+.8** | All affected test files updated (~10 sites with `pytest.approx` or `== 0.0` asserts) | 1.0 |
| **D7+.9** | `docs/adr/0010-budget-money-decimal.md` (new) | 0.3 |
| **D7+.10** | `CHANGELOG.md` `[Unreleased]` entry under `### Changed` | 0.2 |
| **D7+.11** | `ARCHITECTURE.md`, `README.md`, `docs/specs/capability-cost-model.md`, `docs/sprints/sprint-04-executor-and-capabilities.md`, `website/index.html` updates | 0.5 |
| **D7+.12** | `make ci` green (ruff, ruff format --check, mypy --strict, pyright, interrogate, bandit, lint-imports, test-cov) | 0.5 |

**Total: ~4.6 id-ed.** Sized for **1 engineer × 1 week** (the work is small; the effort estimate is dominated by test-site audits and doc updates, not source changes).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 1 engineer with `Decimal` experience | The refactor is small but type-strict; the mypy --strict gate will catch every missed conversion |
| **Tools** | All Sprint 1-7 deps; no new deps | `Decimal` is stdlib |
| **Tests** | All Sprint 1-7 deliverables; `make test-cov` was green at 94.99% before this sprint | Baseline |
| **External** | None | No new vendored data, no API changes |
| **Docs** | `ADR-0004` (MONEY); `docs/specs/capability-cost-model.md` (cost model) | Read carefully — the philosophy is already documented; this sprint operationalizes it |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **`decimal`** (stdlib) | 3.12+ | The type itself | `from decimal import Decimal` |
| **`attrs.field(converter=...)`** | already a dep | Used in the existing `Budget` class to coerce `float → Decimal` at the boundary | The new `converter` accepts `float | int | Decimal` and returns `Decimal` |

## API keys / secrets

None.

## Exit criteria

1. **Type-system end-to-end:** `grep -rn "float" src/paxman/budget.py src/paxman/capabilities/spec.py src/paxman/executor/budget_tracker.py src/paxman/executor/execution_state.py src/paxman/planner/policies.py` shows `Decimal` (not `float`) on every cost-related field and parameter. The only `float` remaining in these files is the `score_capability` return type, which is intentional.
2. **The "Future sprints may switch" comment is gone:** `grep -n "Future sprints may switch" src/paxman/` returns no matches.
3. **Backward compat:** the line `Budget(max_total_cost_usd=0.10)` (a float literal) still works because the constructor accepts `float` and coerces. Verified by `tests/unit/test_budget.py` (which passes unchanged) and a new explicit test `tests/unit/test_budget.py::test_budget_accepts_float_literal_for_cost` (one new test, ~5 lines, asserting `Budget(max_total_cost_usd=0.10).max_total_cost_usd == Decimal("0.10")`).
4. **All 14+ test files pass:** `make test-unit` (≈2213 tests), `make test-property` (22 tests), `make test-integration -m "not slow"` (79 tests).
5. **Coverage holds:** `make test-cov` reports ≥ 90% overall, ≥ 90% on every subsystem, ≥ 95% on `artifact/`, 100% on `errors.py` and `versioning.py`. No regression vs. the Sprint 7 baseline (94.99% overall).
6. **`make ci` is green:** all 7 local-CI gates (install-frozen → lint → format-check → typecheck → typecheck-pyright → imports → test-cov).
7. **`mypy --strict src/paxman` is clean** (0 errors across 77 source files).
8. **No new ADRs required** beyond `ADR-0010` (the new one). `ADR-0004` is updated in spirit via the new ADR-0010; the "Future sprints may switch" exception is closed.
9. **Golden artifacts unchanged:** the 8 `tests/fixtures/artifacts/*.json` files are not regenerated; the JSON-serialization equivalence of `float(0.10)` and `Decimal("0.10")` ensures the replay hash is unchanged.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `Decimal` comparison semantics differ from `float` (e.g., `Decimal("0.10") == 0.1` may behave differently in edge cases) | Low | Low | The V1 domain is `[0.0, 1.0]` USD; comparison in this range is exact. The `budget_excludes_inference` gate at `< 0.001` is the only edge-of-edge case; verified by direct Decimal comparison. |
| The `attrs.field(converter=...)` coercion breaks an existing call site that depends on a `float`-typed value being passed by reference | Low | Medium | The converter is invoked at the boundary; downstream code reads `self.max_total_cost_usd` as `Decimal | None`, not as `float`. Any code that mutates the field post-construction is already blocked by `attrs.frozen`. |
| `pytest.approx` stops working on a `Decimal` value | Low | Low | `pytest.approx` is float-only. Tests using `pytest.approx` on cost values are updated to `== Decimal("0.10")` (exact comparison is safe in V1's domain). |
| The `float → Decimal` coercion in the constructor drops the user-friendly literal-`0.10` ergonomics for power users who want a precision warning | Low | Low | The constructor still accepts `float`; only the internal type changes. A future sprint could add a `strict: bool = False` constructor flag that warns on float input. |
| `mypy --strict` rejects the `float | int | Decimal` converter signature | Low | Low | The converter is a regular function with a single parameter and a return type; mypy handles it cleanly. A fallback annotation `typing.Any` is available if mypy chokes. |
| The `mark_exhausted` `+ 1e-9` hack becomes `+ Decimal("1e-9")` which may interact badly with `Decimal` arithmetic context | Low | Low | The hack is just a nudge to push the counter strictly above the cap; the precise nudge no longer matters under strict `>` comparison. Removed entirely in this refactor. |
| Test sites using `Budget(max_total_cost_usd=0.10)` fail because the constructor rejects `float` (no coercion) | Low | Low | The constructor **does** accept float and coerces; this is explicit in D7+.1. Verified by `tests/unit/test_budget.py:45,76` which use float literals and pass unchanged. |
| `paxman.replay` produces a different `replay_hash` for an existing artifact | Very Low | High | The replay hash does NOT include the budget (verified: `src/paxman/artifact/_hash.py` doesn't reference `budget` or `max_total_cost_usd`). All 8 goldens will replay byte-equal. |

## Anticipated artifacts of this sprint (what the diff will look like)

```
 .github/workflows/ci.yml                           | (no change)
 CHANGELOG.md                                       |  +12
 Makefile                                           | (no change)
 docs/adr/0010-budget-money-decimal.md              |  +54 (new)
 docs/sprints/sprint-04-executor-and-capabilities.md |   +-1
 docs/sprints/sprint-07a-budget-money-decimal.md      |  (this file; you are reading it)
 docs/specs/capability-cost-model.md                 |   +-3
 ARCHITECTURE.md                                     |   +-2
 README.md                                          |   +-1
 pyproject.toml                                     | (no change)
 src/paxman/budget.py                                |   +4 -2
 src/paxman/capabilities/spec.py                    |   +3 -2
 src/paxman/executor/budget_tracker.py              |  +18 -14
 src/paxman/executor/execution_state.py             |   +3 -2
 src/paxman/planner/policies.py                     |   +5 -2
 src/paxman/testing/__init__.py                     |   +2 -2
 src/paxman/planner/scoring.py                      | (no change — score is float)
 src/paxman/planner/heuristics.py                   | (no change — reads budget field, which is now Decimal)
 src/paxman/executor/field_runner.py                | (no change — passes spec.cost_estimate.usd into the Decimal-accepting methods)
 src/paxman/executor/executor.py                    | (no change)
 src/paxman/api/normalize.py                        | (no change)
 tests/unit/test_budget.py                          |   +3 -1
 tests/unit/executor/test_budget_tracker.py         |   +3 -3
 tests/unit/executor/test_execution_state.py        |   +2 -2
 tests/unit/executor/test_field_runner.py           |   +1 -1
 tests/unit/artifact/test_statistics.py             |   +2 -2
 tests/fixtures/factories/policies.py               |   +1 -1
 tests/fixtures/artifacts/*.json                    | (no change — no budget data stored)
 tests/fixtures/public_api_snapshot.json            | (no change — only top-level symbols)
 website/index.html                                 |   +3 -3
 ─────────────────────────────────────────────────
 22 files changed, 169 insertions(+), 41 deletions(-)
```

**One-line summary:** The refactor is small (≈5 source files, ≈10 test files, ≈7 doc files), the philosophical alignment is real, the backward compat is preserved (float literals still work via coercion), and the only thing we'd give up is the historical "V1 cap is float" accident that was never a principled decision in the first place.

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §1.6 (MONEY) — the acceptance criteria this sprint delivers against.
- `../ARCHITECTURE.md` §7 (Configuration Model) — where `Budget` lives.
- `../docs/adr/0004-money-first-class-type.md` — the philosophical foundation.
- `../docs/adr/0010-budget-money-decimal.md` — the new ADR (companion to this sprint).
- `../docs/specs/capability-cost-model.md` — the cost model this sprint refines.
- `../CHANGELOG.md` — entry will be added under `[Unreleased]`.
- `../tests/fixtures/AGENTS.md` — the 5-layer test data model (no changes here; this sprint doesn't touch fixtures).
- `../docs/sprints/sprint-05-reconciler-and-money.md` — the prior money-related sprint; this sprint completes the MONEY-first-class commitment it started.

# ADR-0010: Cost Pipeline Switched to `Decimal` (`Budget`, `CostHint`, `BudgetTracker`, `ExecutionState`)

> **Status:** Accepted
> **Date:** 2026-06-26
> **Deciders:** Paxman core team
> **Supersedes:** — (extends [ADR-0004](./0004-money-first-class-type.md))
> **Superseded by:** —

## Context and Problem Statement

ADR-0004 established that "MONEY is a first-class field type" and is implemented as `MoneyValue(amount: Decimal, currency: str, precision: int | None)`. The project philosophy is documented in `AGENTS.md:73`: `MONEY first-class: amount + ISO-4217 currency + precision (Decimal, never float)`.

However, the **cost pipeline** that tracks USD spend during `paxman.normalize()` was implemented with `float`:

- `Budget.max_total_cost_usd: float | None` (`src/paxman/budget.py:45`)
- `CostHint.usd: float` (`src/paxman/capabilities/spec.py:79`)
- `BudgetTracker.total_cost_usd: float` (`src/paxman/executor/budget_tracker.py:98`)
- `ExecutionState.total_cost_usd: float` (`src/paxman/executor/execution_state.py:93`)

This created a documented asymmetry: `Statistics.total_cost_usd` and `CapabilityStats.total_cost_usd` in `src/paxman/artifact/statistics.py:40,97` are already typed `Decimal`, with explicit `isinstance` validation (`if not isinstance(self.total_cost_usd, Decimal): raise TypeError(...)`). The `Statistics` type enforces `Decimal` on the artifact's terminal representation, but the upstream cost pipeline feeds it `float` values. In practice, the 3 production call sites that construct `Statistics` in `src/paxman/api/normalize.py:239,267,368` all pass defaults, so the asymmetry is latent — but the type system already declares the philosophical position.

The `budget_tracker.py:25-30` module docstring acknowledges this:

> The cost type is `float` for USD and `int` for latency / counts. The USD value is *not* converted to `decimal.Decimal`; V1 uses float per `paxman.budget.Budget` and `paxman.capabilities.spec.CostHint`. Future sprints may switch to `decimal.Decimal` if a precision issue surfaces.

This ADR records the decision to make the switch now, as an **intervention sprint** that closes the gap before any precision issue surfaces.

## Decision Drivers

- **Type-system end-to-end consistency** with ADR-0004 and the `Statistics` type system. The current state is philosophically inconsistent: terminal type is `Decimal`, upstream is `float`.
- **No precision bug in V1 today** — the cost domain is `[0.0, 1.0]` USD and the decision boundary is `< 0.001`, both well inside IEEE 754's exact-integer range. The refactor is preventive, not corrective.
- **Backward compatibility is preserved** via constructor-level `float | int | Decimal → Decimal` coercion. Existing call sites with literal-`0.10` floats continue to work without source changes.
- **Reasonable engineering refactor** — the scope is small (5 source files, ~14 test files, 7 doc files, 1 new ADR), the change is well-understood, and the existing comment in `budget_tracker.py:25-30` already framed this as a future-sprint decision.
- **The earlier "Future sprints may switch" exception is closed** — once the switch is made, the asymmetry is gone and the project philosophy is reflected in the type system end-to-end.

## Considered Options

### Option A — Switch to `Decimal` end-to-end (chosen)

`Budget.max_total_cost_usd: Decimal | None`, `CostHint.usd: Decimal`, `BudgetTracker.total_cost_usd: Decimal`, `ExecutionState.total_cost_usd: Decimal`. The `Budget` constructor accepts `float` and coerces to `Decimal` (preserves backward compat for the `Budget(max_total_cost_usd=0.10)` pattern).

**Pros:**

- Type-system end-to-end consistency with ADR-0004.
- The `Statistics.total_cost_usd: Decimal` declaration is no longer aspirational — the upstream pipeline produces the type the terminal type expects.
- No precision surprises in any future USD domain (V1 has none, V2 may add $100+ caps).
- `Policy.confidence_floor` remains `float` (it's a probability in `[0,1]`, not money — defensible exception).
- Backward compat preserved via constructor coercion.
- Closes the documented "Future sprints may switch" caveat.

**Cons:**

- ~14 test sites need updating (mostly `pytest.approx` on cost values and `== 0.0` asserts).
- `pytest.approx` is float-only; Decimal comparisons must be exact.
- 5 source files change, 7 doc files change.

### Option B — Leave as `float` until a precision bug surfaces

Keep the current state. Update `budget_tracker.py:25-30` to remove the "Future sprints may switch" wording and replace it with a stronger statement that V1 cap is intentionally `float`.

**Pros:**

- Zero churn. Follows the existing "if a precision issue surfaces" comment literally.
- Faster than Option A.

**Cons:**

- The asymmetry between `Statistics.total_cost_usd: Decimal` and `Budget.max_total_cost_usd: float` is a paper cut that future maintainers will trip on.
- The next person who tries to wire `Statistics` from real cost data will hit a `TypeError: total_cost_usd must be a Decimal` and wonder why the input was a `float`.
- The philosophical commitment to "MONEY is Decimal, never float" is not reflected in the cost pipeline, even though it's documented as a project value.

### Option C — Partial refactor: widen the type to `float | Decimal` without changing internal arithmetic

Change `Budget.max_total_cost_usd: float | Decimal | None` only. Leave the rest of the pipeline as `float`. The `Statistics` `Decimal` is still aspirational.

**Pros:**

- Smallest possible change (4 lines).

**Cons:**

- Gives the appearance of a fix without the substance.
- The cost pipeline is still `float` internally.
- The `Statistics.total_cost_usd: Decimal` is still aspirational.

**Verdict:** Worst option — option C was rejected.

## Decision Outcome

**Chosen option: A (switch to `Decimal` end-to-end).**

The switch is a small, well-scoped, behavior-preserving refactor (at the JSON serialization level: `0.10` from `float` and `Decimal("0.10")` serialize identically). The refactor is recorded in `docs/sprints/sprint-07a-budget-money-decimal.md` (the intervention sprint). The `budget_tracker.py:25-30` comment is deleted and replaced with a one-line note that the switch has happened, citing this ADR.

The `Budget(max_total_cost_usd=0.10)` ergonomic for callers is preserved via `attrs.field(converter=_to_decimal)` that accepts `float | int | Decimal` and returns `Decimal`. Existing call sites with literal floats continue to work without changes.

## Consequences

### Positive

- Type-system end-to-end consistency with ADR-0004 ("MONEY is Decimal, never float").
- The `Statistics.total_cost_usd: Decimal` declaration is no longer aspirational.
- No precision surprises in any future USD domain.
- The "Future sprints may switch" caveat in `budget_tracker.py:25-30` is closed.

### Negative

- ~14 test sites need updating (mostly `pytest.approx` on cost values and `== 0.0` asserts).
- New constructor logic in `Budget` and `CostHint` to coerce `float | int → Decimal`.
- One new ADR added (this one). Total: 10 ADRs.

### Neutral

- The `score_capability` formula in `planner/scoring.py` remains `float` (the score is a sortable rank, not money; the V1 weight table is calibrated for `float`).
- The `Policy.confidence_floor: float` field remains `float` (it's a probability in `[0,1]`, not money).
- The 8 golden artifacts do not need regeneration (they store no budget data; replay hash is unchanged).
- The public API snapshot does not need updating (it captures top-level symbols by name, not class attribute types).

## Validation

- `make ci` is green: ruff, ruff format --check, mypy --strict, pyright, interrogate, bandit, lint-imports, test-cov.
- `mypy --strict src/paxman` is clean (0 errors across 77 source files).
- `make test-unit`, `make test-property`, `make test-integration -m "not slow"` all pass.
- `make test-cov` reports ≥ 90% overall, ≥ 90% on every subsystem, ≥ 95% on `artifact/`, 100% on `errors.py` and `versioning.py` (no regression vs. the Sprint 7 baseline of 94.99% overall).
- New test: `tests/unit/test_budget.py::test_budget_accepts_float_literal_for_cost` — asserts `Budget(max_total_cost_usd=0.10).max_total_cost_usd == Decimal("0.10")` to lock the backward-compat behavior.
- New test: `tests/unit/test_capability_spec.py::test_cost_hint_accepts_float_literal` (if not already covered) — same backward-compat lock for `CostHint`.
- All 8 golden artifacts (`tests/fixtures/artifacts/*.json`) replay byte-equal against the refactored code (verified by `tests/integration/test_golden_artifacts.py`).
- A roundtrip integration test `tests/integration/cross_subsystem/test_budget_decimal_roundtrip.py` (new) — `paxman.normalize(...)` with `Budget(max_total_cost_usd=Decimal("0.10"))` produces the same artifact as `paxman.normalize(...)` with `Budget(max_total_cost_usd=0.10)`.

## References

- [ADR-0004: MONEY as a First-Class Type](./0004-money-first-class-type.md) — the philosophical foundation; this ADR extends it operationally.
- [AGENTS.md:73](https://github.com/nexusnv/paxman/blob/main/AGENTS.md#L73) — "MONEY first-class: amount + ISO-4217 currency + precision (Decimal, never float)".
- [Sprint 7a — Budget money decimal](https://github.com/nexusnv/paxman/wiki/Internal-Development/Sprints/Sprint-07a---Budget-money-decimal) — the intervention sprint that implements this ADR.
- [docs/specs/capability-cost-model.md](https://github.com/nexusnv/paxman/blob/main/docs/specs/capability-cost-model.md) — the cost model refined by this refactor.
- [CHANGELOG.md](../operations/changelog.md) — entry added under `[Unreleased]`.
- [src/paxman/budget.py](https://github.com/nexusnv/paxman/blob/main/src/paxman/budget.py) — the primary type being changed.
- [src/paxman/artifact/statistics.py](https://github.com/nexusnv/paxman/blob/main/src/paxman/artifact/statistics.py) — the terminal type whose `Decimal` declaration is no longer aspirational after this ADR.

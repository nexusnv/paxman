# Engineering Standards

> **Status:** Draft v1.
> **Audience:** Paxman contributors and maintainers.
> **Related docs:** [Contributing](./index.md), [Development](./development.md), [Architecture](../reference/architecture.md), [Package Structure](../reference/package-structure.md)

This document captures Paxman's **engineering process standards** — the
policies that govern how we use tooling, how we enforce quality gates, and
how we document decisions that are engineering process (not architecture).

For **architectural decisions** (plugin architecture, provider abstraction,
canonical schema, dependency inversion), see the [ADR index](../adr/).

---

## 1. Canonical vs Additional Checkers

Paxman uses multiple static analysis tools. Each has a defined role:

| Tool | Role | Gate? | Config |
|---|---|---|---|
| **mypy** | Canonical type checker | **Yes** | `pyproject.toml` `[tool.mypy]` `strict = true` |
| **pyright** | Additional validation (basic) | No (advisory) | `pyrightconfig.json` `typeCheckingMode: "basic"` |
| **pyright strict** | Additional validation (strict) | No (advisory) | `pyrightconfig-strict.json` `typeCheckingMode: "strict"` |
| **ruff** | Linting + formatting | **Yes** | `pyproject.toml` `[tool.ruff]` |
| **bandit** | Security linting | No (advisory) | CLI flags in Makefile |
| **interrogate** | Docstring coverage | **Yes** | `pyproject.toml` `[tool.interrogate]` |
| **import-linter** | Import layer contracts | **Yes** | `pyproject.toml` `[tool.importlinter]` |

**Policy:** mypy defines correctness. Pyright provides additional validation.
Two independent type systems should not both be capable of blocking every PR.

**Design decision:** D8.19 (pyright is advisory; mypy --strict is the gate).

---

## 2. Suppression-Free Policy

Paxman enforces a **suppression-free policy** on `src/paxman/`:

- **No `# type: ignore`** in `src/paxman/`. CI rejects.
- **No `# pyright: ignore`** in `src/paxman/`. CI rejects.
- **No `# noqa`** in `src/paxman/`. CI rejects. (`S101` for asserts in tests is already permitted via the `tests/**/*.py` per-file-ignore in `pyproject.toml`, not via inline `# noqa`.)
- **No `as any`** or equivalent type-erasure in `src/paxman/`. CI rejects.

**Rationale:** Suppressions hide type-system weaknesses. If a type is `Any`,
the type system cannot verify correctness. Suppressions make the weakness
invisible to reviewers.

**Exception process:** If a suppression is truly necessary (e.g. a third-party
library without type stubs), the suppression must live in the tool's config
file (`pyproject.toml` or `pyrightconfig.json`), not inline. This makes the
suppression visible and auditable at the rule level, not the call site.

**Example:** `defusedxml` does not ship type stubs. The suppression is in
`pyproject.toml` `[tool.mypy.overrides]` with `ignore_missing_imports = true`,
not inline at the import site.

---

## 3. Pyright Silenced Rules Log

The following pyright rules are intentionally silenced in
`pyrightconfig-strict.json`. Each rule has a one-line justification.

| Rule | Count | Justification | Audit Status |
|---|---:|---|---|
| `reportUnnecessaryIsInstance` | 239 | Deliberate runtime safety nets (constructor validation, parameter validation, type dispatch). 9 dead guards removed in PR-1.5; 230 kept as deliberate safety nets. | Audited in PR-1.5 of [#26](https://github.com/nexusnv/paxman/issues/26) — re-silenced to avoid ~239 false positives in CI |
| `reportUnknownParameterType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | V2 deferred (real adapter-layer Any-leakage) |
| `reportUnknownArgumentType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | V2 deferred (real adapter-layer Any-leakage) |
| `reportUnknownLambdaType` | — | Carried forward from basic config. | V2 deferred (real adapter-layer Any-leakage) |
| `reportUnknownVariableType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | V2 deferred (real adapter-layer Any-leakage) |
| `reportUnknownMemberType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | V2 deferred (real adapter-layer Any-leakage) |
| `reportMissingTypeStubs` | — | Third-party libraries (e.g. `openapi-spec-validator`, `jsonschema`) don't ship type stubs. Adapter layer relies on these. | Not audited |
| `reportUnusedImport` | — | Carried forward from basic config. Pyright false-positives on attrs `@define` re-exports. | Not audited |
| `reportUnusedVariable` | — | Carried forward from basic config. Pyright false-positives on Protocol-bound locals. | Not audited |
| `reportUnusedFunction` | — | Carried forward from basic config. Pyright false-positives on `__all__` exports. | Not audited |
| `reportUnusedClass` | — | Carried forward from basic config. Pyright false-positives on `attrs` validators. | Not audited |
| `reportUnusedExpression` | — | Carried forward from basic config. Pyright false-positives on result-less calls in capability specs. | Not audited |
| `reportPrivateImportUsage` | — | Carried forward from basic config. Internal modules cross-reference private helpers by design. | Not audited |
| `reportConstantRedefinition` | — | Carried forward from basic config. Pyright false-positives on conditional constants. | Not audited |

**Policy:** When adding a new silenced rule, document it here with:
1. The rule name
2. The diagnostic count (run `pyright --strict` and count)
3. A one-line justification
4. The audit status (To be audited / Audited and justified / Audited and removed / V2 deferred)

**Audit process:** The `reportUnnecessaryIsInstance` audit was completed in
PR-1.5 of [#26](https://github.com/nexusnv/paxman/issues/26). Each guard was
classified as:
- **Deliberate runtime safety net** — kept, documented in §4 below
- **Dead code** — removed (9 sites in reconciler modules)
- **Type-system workaround** — none identified; 2 Protocols tightened instead

---

## 4. PR-1.5 Audit Results (Pyright Strict Mode Initiative #26)

PR-1.5 performed a full audit of the `isinstance()` call sites in `src/paxman/` to classify them as:
- **Deliberate runtime safety net** — keep, document
- **Dead code** — remove
- **Type-system workaround** — tighten the Protocol to eliminate the need

### Summary

| Category | Count | Action |
|---|---:|---|
| Deliberate runtime safety nets | 230 | Kept (documented in this table) |
| Dead code (homogeneous tuple comprehension filters) | 9 | Removed |
| Type-system workarounds | 0 | None identified |

The 9 dead guards were in `reconciler/evidence_compare.py` (4), `reconciler/reconciler.py` (2), `reconciler/merge.py` (2), and `reconciler/conflict.py` (1). They were `isinstance(c, Candidate)` and `isinstance(r, EvidenceRef)` filters inside comprehensions over `tuple[Candidate, ...]` or `tuple[EvidenceRef, ...]` — the type system already guarantees homogeneity.

The 230 deliberate runtime safety nets remain. They are concentrated in:
- `__attrs_post_init__` constructor validation guards (~133 instances)
- Function/method parameter validation guards (~28 instances)
- Type dispatch/branching for serialization, JSON tree walking, adapter input routing (~55 instances)
- `_validate_default` type-vs-fieldtype dispatch (~11 instances)
- `bytes` input guards (~5 instances)

### Protocol Tightening

| Protocol | Before | After | ADR Required? |
|---|---|---|---|
| `CanonicalField.default` | `typing.Any` | `str \| int \| bool \| float \| decimal.Decimal \| MoneyValue \| dict[str, object] \| list[object] \| tuple[object, ...] \| None` | No (annotation accuracy) |
| `EvidenceRef.context` | `dict[str, typing.Any]` | `dict[str, str \| bool \| int \| list[str] \| dict[str, str \| int]]` | No (annotation accuracy) |
| `CanonicalContract` | (no Any) | (no change needed) | N/A |
| `MoneyValue` | (no Any) | (no change needed) | N/A |
| `CapabilitySpec` | (no Any) | (no change needed) | N/A |

---

## 5. Adapter-Layer Protocol Investment

The adapter layer (`contract/adapters/*`, `contract/canonical.py`,
`artifact/artifact.py`, `planner/field_plan.py`) carries the bulk of the
pyright strict diagnostics. This is not random — it tracks the boundaries
where external formats (`dict[str, Any]`, JSON Schema, OpenAPI, Pydantic)
meet the internal canonical model.

**Target Protocols for PR-1:**

- `CanonicalField` — the canonical representation of a contract field
- `CanonicalContract` — the canonical representation of a contract
- `MoneyValue` — first-class money representation (amount + currency + precision)
- `CapabilitySpec` — the specification of a capability (input/output, cost, determinism)
- `EvidenceRef` — a reference to evidence (provenance, confidence)

**Goal:** Tighten these Protocols so that the `dict[str, Any]` leakage at
the adapter boundary is narrowed to `object` or to a Protocol with explicit
members. This reduces risk for V2 features (inference providers, recursive
contracts) that will extend these Protocols.

**Success criterion:** Diagnostics drop from 490 to < 50 (non-`isinstance`),
with the residual diagnostics concentrated in documented silenced rules.

---

## 6. Adding a New Checker

When adding a new static analysis tool to the Paxman CI pipeline:

1. **Define the role.** Is the tool a gate (blocks PRs) or additional validation (advisory)?
2. **Choose the config location.** Tool-specific config file (e.g. `pyrightconfig.json`) or `[tool.*]` section in `pyproject.toml`.
3. **Add the Makefile target.** Follow the existing pattern: `.PHONY` + target with `##` doc + `$(UV) run` command.
4. **Add the CI job.** Follow the existing pattern: comment block + job key + steps (Checkout → Install uv → Python → Install deps → Run tool). If advisory, add `continue-on-error: true` with a D8.XX design decision reference.
5. **Document in this file.** Add the tool to the table in §1. If the tool has silenced rules, add them to §3 (or create a new section for the tool).

**Example:** Adding a new linter `newlinter`:

1. Role: Gate (blocks PRs on errors).
2. Config: `pyproject.toml` `[tool.newlinter]`.
3. Makefile: `.PHONY: newlinter` + `newlinter: ## Run newlinter` + `$(UV) run newlinter src/paxman`.
4. CI job: `newlinter:` job with 5-step pattern, no `continue-on-error`.
5. Doc: Add `newlinter` to §1 table.

---

## 7. References

- [Contributing](./index.md) — contribution workflow
- [Development](./development.md) — development setup
- [Architecture](../reference/architecture.md) — subsystem design
- [Package Structure](../reference/package-structure.md) — module layout
- [ADR Index](../adr/) — architectural decisions
- [Issue #26](https://github.com/nexusnv/paxman/issues/26) — Pyright Strict Mode Initiative

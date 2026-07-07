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
| **import-linter** | Import layer contracts | **Yes** | `.importlinter` |

**Policy:** mypy defines correctness. Pyright provides additional validation.
Two independent type systems should not both be capable of blocking every PR.

**Design decision:** D8.19 (pyright is advisory; mypy --strict is the gate).

---

## 2. Suppression-Free Policy

Paxman enforces a **suppression-free policy** on `src/paxman/`:

- **No `# type: ignore`** in `src/paxman/`. CI rejects.
- **No `# pyright: ignore`** in `src/paxman/`. CI rejects.
- **No `# noqa`** in `src/paxman/`. CI rejects. (Test code may use `# noqa: S101` for asserts.)
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
| `reportUnnecessaryIsInstance` | 251 | Deliberate runtime safety nets over `Any`-typed adapter inputs. Runtime correctness beats static elegance. | Audited in PR-1 of [#26](https://github.com/nexusnv/paxman/issues/26) — confirmed as deliberate runtime safety nets; no removals |
| `reportUnknownParameterType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | Not audited |
| `reportUnknownArgumentType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | Not audited |
| `reportUnknownLambdaType` | — | Carried forward from basic config. | Not audited |
| `reportUnknownVariableType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | Not audited |
| `reportUnknownMemberType` | — | Carried forward from basic config. Adapter layer uses `dict[str, Any]`-shaped inputs. | Not audited |
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
4. The audit status (To be audited / Audited and justified / Audited and removed)

**Audit process:** PR-1 of [#26](https://github.com/nexusnv/paxman/issues/26)
will audit the `reportUnnecessaryIsInstance` cluster. Each guard will be
classified as:
- **Deliberate runtime safety net** — keep, document in this table
- **Dead code** — remove
- **Type-system workaround** — tighten the Protocol to eliminate the need

---

## 4. Adapter-Layer Protocol Investment

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

## 5. Adding a New Checker

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

## 6. References

- [Contributing](./index.md) — contribution workflow
- [Development](./development.md) — development setup
- [Architecture](../reference/architecture.md) — subsystem design
- [Package Structure](../reference/package-structure.md) — module layout
- [ADR Index](../adr/) — architectural decisions
- [Issue #26](https://github.com/nexusnv/paxman/issues/26) — Pyright Strict Mode Initiative

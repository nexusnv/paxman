# Dependencies

> **Status:** Draft v1.
> **Audience:** Paxman users (especially those concerned about install footprint) and Paxman maintainers.
> **Related docs:** [PACKAGE_STRUCTURE.md §17 Build and Packaging Strategy](./PACKAGE_STRUCTURE.md), [SECURITY.md](./SECURITY.md), [PRD.md §11 Dependencies and Assumptions](./PRD.md)

This document describes Paxman's **dependency policy**: what is core, what is optional, and how the packaging is organized.

---

## 1. Policy

Paxman follows a **minimal core** policy:

- **Core dependencies** (always installed with `pip install paxman`) must be **≤ 3 packages** and must not pull in heavyweight transitive dependencies.
- **Adapter extras** are scoped to the format the user actually uses.
- **Inference provider extras** are V2; V1 ships a stub provider with no extra dependencies.
- **Dev dependencies** are scoped to PEP 735 dependency groups, not `[project.optional-dependencies]`.

This policy keeps `pip install paxman` cheap, fast, and safe for downstream users.

---

## 2. Core Dependencies

These are installed by default with `pip install paxman`:

| Package | Version | Purpose | Why core |
|---|---|---|---|
| `attrs` | `>=23.0` | Lightweight data classes for internal types | Internal data model; no `pydantic`-in-core dependency. |
| `typing-extensions` | `>=4.0` | Backport of `typing` features for older Pythons | Cross-version type-hint support. |

**Total core deps: 2 packages.** Both are tiny, pure-Python, and have no transitive dependencies of consequence.

The V1 core **does not** require `pydantic`. Pydantic is an optional extra used only by the Pydantic adapter.

---

## 3. Optional Dependencies (Extras)

Extras are declared in `[project.optional-dependencies]` and installed with `pip install paxman[<extra>]`.

### 3.1 Adapter extras

| Extra | Dependencies | Required by |
|---|---|---|
| `pydantic` | `pydantic>=2.5` | `PaxmanPydanticAdapter` |
| `json-schema` | `jsonschema>=4.20` | `PaxmanJsonSchemaAdapter` |
| `openapi` | `openapi-spec-validator>=0.6` | `PaxmanOpenAPIAdapter` (best-effort) |
| `all-adapters` | All of the above | Convenience meta-extra |

### 3.2 Inference provider extras (V2+)

V1 ships a stub provider; V2 will ship reference providers:

| Extra | Dependencies | Required by | V1? |
|---|---|---|---|
| `inference-openai` | `openai>=1.0` | `OpenAIProvider` | No (V2) |
| `inference-anthropic` | `anthropic>=0.20` | `AnthropicProvider` | No (V2) |
| `inference-cohere` | `cohere>=4.0` | `CohereProvider` | No (V2) |
| `all-providers` | All of the above | Convenience | No (V2) |

### 3.3 Convenience extras

| Extra | Dependencies | Purpose |
|---|---|---|
| `all` | All adapter extras | Every adapter |
| `dev` | (use PEP 735 instead) | Deprecated; use `uv sync --dev` |

### 3.4 Examples

```bash
# Just the core
pip install paxman

# Core + Pydantic
pip install paxman[pydantic]

# Core + all adapters
pip install paxman[all]

# V2: core + OpenAI provider
pip install paxman[inference-openai]

# V2: everything
pip install paxman[all,inference-openai]
```

---

## 4. Dev Dependencies (PEP 735)

Dev dependencies are **not** `[project.optional-dependencies]` (those are for end users). They are declared as PEP 735 dependency groups in `pyproject.toml` and installed with `uv sync --dev` or `pip install --group dev` (with a PEP 735-compatible tool).

| Package | Purpose |
|---|---|
| `pytest>=7.4` | Test runner |
| `pytest-cov>=4.1` | Coverage |
| `pytest-xdist>=3.3` | Parallel test execution |
| `hypothesis>=6.0` | Property-based testing |
| `pytest-benchmark` (V2) | Performance benchmarks |
| `pytest-mock` | Mocking |
| `ruff>=0.4` | Lint + format |
| `mypy>=1.10` | Static type checking |
| `pyright>=1.1` | Cross-validation type checking |
| `import-linter>=2.0` | Module DAG enforcement |
| `interrogate>=1.7` | Docstring coverage |
| `structlog>=24.1` | Structured logging (testing helpers) |
| `bandit` | Security lint |
| `pip-audit` | Dependency vulnerability scanning |
| `hatchling` | Build backend |
| `hatch` | Build orchestration |
| `twine` (legacy) | PyPI upload (use trusted publishing instead) |

Dev dependencies do not affect end users. `pip install paxman` never installs them.

---

## 5. Adding a New Dependency

### 5.1 Core dependency

Adding a new core dependency is a **breaking change** in spirit (it increases the install footprint for every user) and requires:

1. An ADR documenting the rationale.
2. A team review.
3. A clear justification: "the dependency is needed by the core engine, not by an adapter or provider."

If the dependency is only needed by an optional feature, put it in an extra instead.

### 5.2 Optional extra

Adding a new optional extra is a **non-breaking change** and requires:

1. A team review.
2. Documentation in this file (§3).
3. A test that exercises the extra.

### 5.3 Dev dependency

Adding a new dev dependency is a **non-breaking change** and requires:

1. A team review.
2. Documentation in this file (§4).

### 5.4 Pinning

- Use **lower bounds** to declare minimum supported versions: `pydantic>=2.5`.
- Do **not** use upper bounds unless there's a known incompatibility.
- Use `~=` for patch-level pinning only when the dependency has a known issue.
- Avoid `==` pinning except in dev/CI lockfiles.

---

## 6. Dependency Conflicts

Paxman may be installed in environments with conflicting dependencies (e.g., a caller using Pydantic v1). The policy:

- **Core deps are minimal** — `attrs` and `typing-extensions` rarely conflict.
- **Adapter extras are isolated** — installing `paxman[pydantic]` does not affect `paxman[json-schema]`.
- **Inference provider extras are isolated** (V2) — installing `paxman[inference-openai]` does not affect `paxman[inference-anthropic]`.
- **No `pip check` failures** are tolerated. CI runs `pip check` on every wheel build.

If a conflict is reported, open an issue. The conflict is a bug in either Paxman or the other package.

---

## 7. Security Scanning

CI runs `pip-audit` and `bandit` on every PR.

- **Critical / High vulnerabilities** block the PR.
- **Medium / Low vulnerabilities** are reported but do not block.
- A weekly GitHub Action runs `pip-audit` against the latest dependency tree and opens issues for new vulnerabilities.

See [SECURITY.md](./SECURITY.md) for the vulnerability reporting process.

---

## 8. Supply Chain

- **Trusted publishing** is used for PyPI uploads. No API keys in the repo or environment.
- **All dependencies are pinned** with lower bounds in `pyproject.toml` and resolved to exact versions in `uv.lock` (or `requirements.lock` if using pip).
- **Reproducible builds** are a goal: `uv sync --frozen` should produce a byte-identical `uv.lock` and install set on every machine.
- **Sigstore** signing of wheels is a V2 goal.

---

## 9. Dependency Graph

```text
paxman (core)
├── attrs
└── typing-extensions

paxman[pydantic]
└── pydantic

paxman[json-schema]
└── jsonschema

paxman[openapi]
└── openapi-spec-validator

paxman[inference-openai]  (V2)
└── openai

paxman[inference-anthropic]  (V2)
└── anthropic
```

The core is intentionally **disconnected** from any schema library. Adapters are the only place that depends on Pydantic, `jsonschema`, etc.

---

## 10. See also

- [PACKAGE_STRUCTURE.md §17 Build and Packaging Strategy](./PACKAGE_STRUCTURE.md)
- [PRD.md §11 Dependencies and Assumptions](./PRD.md)
- [SECURITY.md §7 Vulnerability Reporting](./SECURITY.md)
- [DEVELOPMENT.md §9 Building the Package](./DEVELOPMENT.md)

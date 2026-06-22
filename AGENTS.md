# PROJECT KNOWLEDGE BASE — Paxman

**Generated:** 2026-06-22T09:44:36Z
**Commit:** 174d8dd
**Branch:** main

## OVERVIEW

Paxman is a **contract-driven deterministic normalization engine for Python** (in design stage — no source code yet). Takes arbitrary input (PDFs, scans, emails, spreadsheets, free text) and a caller-owned contract (Pydantic / JSON Schema / OpenAPI / Dict DSL), produces an evidence-backed, replayable normalized artifact. Public API: `paxman.normalize()` and `paxman.replay()`.

**Status: design-only.** `src/` does not exist. Zero implementation. 13 top-level files are Markdown specs + 4 design specs in `docs/specs/`; the 9 ADRs are the architectural source of truth.

## STRUCTURE

```
paxman/
├── README.md, PRD.md, ARCHITECTURE.md, PACKAGE_STRUCTURE.md
├── GLOSSARY.md, V1_ACCEPTANCE_CRITERIA.md, REPLAY_AND_DETERMINISM.md
├── SECURITY.md, TESTING_STRATEGY.md, EXTENDING.md
├── DEPENDENCIES.md, DEVELOPMENT.md
├── docs/{TEST_DATA.md, adr/, specs/}        # 9 ADRs → docs/adr/AGENTS.md; 4 design specs → docs/specs/
├── scripts/fetch_test_data.py               # 50MB vendor (download is stubbed)
├── tests/fixtures/                          # 5-layer data → tests/fixtures/AGENTS.md
└── .agents/skills/                          # 17 OpenCode project skills
```

**Planned (NOT YET IMPLEMENTED) layout:** `src/paxman/` with 7 subsystems (`contract/`, `planner/`, `capabilities/`, `executor/`, `reconciler/`, `artifact/`, `api/`) + 9 cross-cutting modules.

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Product vision | `README.md` → `PRD.md` (v1 scope source of truth) |
| Module layout | `PACKAGE_STRUCTURE.md` ("Stable v1" — code structure source of truth) |
| v1 acceptance | `V1_ACCEPTANCE_CRITERIA.md` |
| Replay model | `REPLAY_AND_DETERMINISM.md` (SHA-256, no recompute) |
| Security | `SECURITY.md` (threat model, PII, secrets-by-reference) |
| Test strategy | `TESTING_STRATEGY.md` (5-layer data, property tests) |
| Add adapter/capability/provider | `EXTENDING.md` |
| Dev setup | `DEVELOPMENT.md` (uv, Makefile, release) |
| Dependency policy | `DEPENDENCIES.md` (core ≤ 3 pkgs, no numpy/torch/requests) |
| Architecture change | `docs/adr/` (MADR template; ADRs immutable once Accepted) |
| Test data + licensing | `docs/TEST_DATA.md` |
| Vocabulary | `GLOSSARY.md` |
| Dict DSL / InputProfile / cost model / license decision | `docs/specs/` (4 design specs) |

## PLANNED CODE MAP (7 subsystems)

None implemented yet. Per `PACKAGE_STRUCTURE.md` §2-§10.

| Subsystem | Responsibility | Boundary rule |
|-----------|----------------|---------------|
| `contract/` | Adapter + validation (4 formats → CanonicalContract) | **Only layer that knows about external schemas** |
| `planner/` | Field-centric plan synthesis (deterministic, rule-based) | **Never executes. Emits FieldPlans only.** |
| `capabilities/` | 5 atomic ops: text_extraction, regex_extraction, lookup, inference, validation | **Never assign confidence. Never read canonical contract directly.** |
| `executor/` | Runs plan, collects evidence, stops early | **Never replans. Never assigns confidence. Never reads raw input directly.** |
| `reconciler/` | Merges candidates, assigns final confidence, resolves truth | **Sole confidence authority. Never executes. Never reads raw input. Never sees external schemas.** |
| `artifact/` | ExecutionArtifact + replay hash + diagnostics | **Replay rehydrates captured truth — never recomputes.** |
| `api/` | Public surface — `normalize()`, `replay()`, public types/errors | **No internal concepts leak (no FieldPlan, no CapabilitySpec, no TruthLayer by name).** |

## CONVENTIONS (PROJECT-SPECIFIC)

- **Python ≥ 3.11**, src-layout, `hatchling` build backend, `uv` package manager
- **Core deps ≤ 3 packages:** `attrs>=23.0`, `typing-extensions>=4.0` (no numpy/torch/requests)
- **Data classes:** `attrs` for core, NOT pydantic (pydantic is adapter-only)
- **Naming:** `snake_case` modules/functions, `PascalCase` classes, `SCREAMING_SNAKE_CASE` enums/statuses/bands/error codes
- **Type hints mandatory** on every public symbol; `py.typed` shipped (PEP 561)
- **Mypy `--strict`** on public surface; **pyright** cross-validates
- **Ruff:** `E,F,W,I,B,UP,ANN,ASYNC,S,RUF`; line-length 100; `S101` (asserts) OK in tests
- **Docstrings:** Google style; `interrogate` enforces 100% on public surface
- **Test markers:** `deterministic`, `replay`, `property`, `slow`
- **Confidence bands (fixed):** `CERTAIN`, `HIGH`, `MEDIUM`, `LOW`, `UNTRUSTED`
- **MONEY first-class:** amount + ISO-4217 currency + precision (Decimal, never float)
- **9 V1 field types:** `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`
- **Status enum:** `SUCCESS`, `PARTIAL_SUCCESS`, `UNRESOLVED`, `INVALID_CONTRACT`, `EXECUTION_FAILED`
- **JSON serialization:** sorted keys, no whitespace, RFC 8785-style (never mock the encoder)
- **Confidence is sole-owned by Reconciler** (ADR-0005); capabilities never assign; planner may emit `target_confidence` only

## ANTI-PATTERNS (ZERO TOLERANCE)

- `# type: ignore`, `# pyright: ignore`, `as any`, `# noqa` in `src/paxman/` — **CI rejects**
- `paxman.normalize()` is **synchronous and not thread-safe** (V1). No async API. (V2.)
- **Sequential execution only** (ADR-0006). No parallel field execution in V1.
- **Replay is pure deserialization.** Never invoke capability/planner/executor/reconciler during replay.
- **Secrets by reference only.** Never embed API keys in artifacts.
- **Raw input never in logs by default** (`Policy.log_raw_input: bool = False`)
- **Inference output is untrusted until validated**
- **Adding a public API surface requires an ADR** (caught by `tests/test_public_api.py` snapshot)
- **Adding a core dependency requires an ADR** (`DEPENDENCIES.md`)
- **No persistence in core.** No storage imports anywhere.
- **No real PII in test data.** License gating enforced by `scripts/fetch_test_data.py --validate-licenses`.
- **Determinism violation = test failure.** Property-tested with Hypothesis `derandomize=True`.

## UNIQUE STYLES

- **Contract = caller-owned.** Paxman never owns schemas, ontologies, or business standards.
- **Field-centric, not document-centric.** One FieldPlan per required field. (ADR-0001)
- **Planner is a pure function** — no LLM, no agent, no AI-generated planning logic in V1. (ADR-0002)
- **Reconciler is a first-class subsystem** owning final truth + final confidence. (ADR-0003)
- **Three truth layers are explicit:** Contract Truth, Candidate Truth, Resolved Truth.
- **Errors are structured:** every exception carries `error_code` (string) + `context` dict.
- **Status vs Exception:** Status = expected failure in artifact (`UNRESOLVED`); Exception = unrecoverable.
- **V1 ships exactly 5 capabilities** + 3 required adapters + 1 optional adapter. Everything else is V2.
- **Cross-cutting modules never import from subsystem layers** (`errors.py`, `types.py`, `protocols.py`, `versioning.py`, `logging.py`, `budget.py`, `clock.py`, `ids.py`, `serialization.py`).

## COMMANDS (PLANNED — NOT YET WIRED)

```bash
# Dev setup
uv venv && uv sync --all-extras --dev
uv run pre-commit install

# Test data
make test-data-vendor         # vendor V1 corpus (~50MB)
make test-data-list           # list vendored datasets + licenses
make test-data-verify         # verify vendored data (CI use)

# Test
make test                     # all
make test-unit                # unit only
make test-property            # property only
make test-cov                 # with coverage
make test-public-api          # public surface stability

# Lint / type / imports
make lint                     # ruff check
make format                   # ruff format
make typecheck                # mypy --strict
make typecheck-pyright        # pyright
make imports                  # import-linter (DAG)

# Build / publish
make build                    # hatchling build → dist/
make publish-test             # TestPyPI
make publish                  # PyPI (trusted publishing)
make ci                       # full local CI
```

## NOTES

- **No source code yet.** First implementation step: `pyproject.toml`, `src/paxman/` skeleton, `Makefile`, `.pre-commit-config.yaml`, CI config.
- **Public API target: ≤ 5 functions in V1** (`normalize`, `replay`, `register_adapter`, `register_capability`, `__version__`).
- **Coverage targets:** mypy 100% on public surface; pytest ≥ 90% lines on `contract/`, `planner/`, `executor/`, `reconciler/`.
- **Cold-start target: ≤ 100 ms.** Aspirational perf: p50 ≤ 200 ms, p99 ≤ 2 s for 20-field contract on 100 KB input.
- **License TBD:** MIT or Apache-2.0 — pending team decision.
- **`tests/fixtures/artifacts/` is empty** — goldens are bootstrapped from real implementations, never predicted.
- **Research-only datasets** (SROIE, INV-CDIP, FATURA) are NOT vendored. CI never exercises those code paths.

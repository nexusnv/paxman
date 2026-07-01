# PROJECT KNOWLEDGE BASE — Paxman

**Generated:** 2026-07-01
**Commit:** b410fbe
**Branch:** main
**Version:** 1.0.1 (Production/Stable)

## OVERVIEW

Paxman is a **contract-driven deterministic normalization engine for Python** — **shipped, in production**. Takes arbitrary input (PDFs, scans, emails, spreadsheets, APIs, free text) and a caller-owned contract (Pydantic / JSON Schema / OpenAPI / Dict DSL), produces an evidence-backed, replayable normalized artifact. Public API: `paxman.normalize()` and `paxman.replay()`.

**Status: v1.0.1 implemented and shipped.** `src/paxman/` is live with 7 subsystems + 9 cross-cutting modules. 4 contract adapters, 5 V1 capabilities, 11 ADRs, 3 reference examples, a 10-check CI pipeline. All V1 acceptance criteria are met. Per [README.md](./README.md), v1.0.0 is the current stable release and v1.0.1 is the current `main`-HEAD patch.

## STRUCTURE

```
paxman/
├── README.md                       # Quickstart, examples, perf table, RTD links
├── LICENSE                         # MIT (Copyright 2026 Paxman core team, per ADR-0008)
├── CHANGELOG.md                    # stub → docs/operations/changelog.md
├── CONTRIBUTING.md                 # stub → docs/contributing/
├── CODE_OF_CONDUCT.md              # full text (Contributor Covenant v2.1, 137 lines)
├── SECURITY.md                     # stub → docs/security/
├── pyproject.toml                  # PEP 621 metadata, v1.0.1, hatchling, PEP 735 dep groups
├── uv.lock                         # committed lockfile
├── Makefile                        # 32 targets, 10-check `make ci` pipeline
├── mkdocs.yml                      # MkDocs Material config (RTD site)
├── .readthedocs.yaml               # RTD build config (Python 3.12, uv)
├── .pre-commit-config.yaml         # ruff + mypy + hygiene hooks
├── pyrightconfig.json              # pyright basic mode
├── .coderabbit.yaml                # CodeRabbit AI review config (auto-review on PR)
├── .gitignore / .github/           # GitHub workflows + issue/PR templates + CODEOWNERS
│
├── src/paxman/                     # the package (src-layout) — see "CODE MAP" below
├── tests/                          # pytest suite (unit / property / integration / benchmark / public_api)
│   ├── unit/                       # per-subsystem unit tests (~50 files)
│   ├── property/                   # Hypothesis determinism + property tests (5 files)
│   ├── integration/                # end-to-end, cross-subsystem, golden replay (10+ files)
│   ├── benchmark/                  # pytest-benchmark suite
│   ├── public_api/                 # snapshot test guarding public surface
│   └── fixtures/                   # 5-layer fixtures (artifacts, contracts, inputs, factories)
│
├── docs/                           # user + contributor docs (Diátaxis-style, served by RTD)
│   ├── index.md                    # RTD landing
│   ├── adr/                        # 11 ADRs (0001-0011) + index.md + agents-knowledge.md
│   ├── concepts/                   # contracts, capabilities, planning, reconciliation, replay, migration, v1.0.0/v1.0.1 release notes
│   ├── howto/                      # add_adapter, add_capability, add_inference_provider, replay_artifact
│   ├── reference/                  # architecture, package-structure, glossary, replay-and-determinism, extending, dependencies
│   ├── specs/                      # dict-dsl-spec, input-profile-spec, capability-cost-model (+ README)
│   ├── contributing/               # development, testing-strategy, test-data, code-of-conduct, maintainers
│   ├── security/                   # index.md
│   ├── operations/                 # changelog.md
│   ├── guides/                     # forward-growth slot
│   └── superpowers/                # plans/, specs/ (gitignored)
│
├── examples/                       # 3 reference mini-packages (each its own pyproject + src + tests)
│   ├── backend_service/            # Persona A — FastAPI POST /normalize
│   ├── ai_agent_ingest/            # Persona B — agent tool-calling loop
│   └── saas_procurement/           # Persona C — CSV-batch normalization
│
├── scripts/                        # 4 ops scripts
│   ├── fetch_test_data.py          # V1 test-data vendor (download stubbed)
│   ├── bootstrap_golden_artifacts.py
│   ├── check_subsystem_coverage.py # per-subsystem coverage thresholds (D7.15)
│   └── benchmark_import_time.py    # cold-import timing
│
├── .agents/                        # OpenCode project skills (gitignored)
├── .sisyphus/                      # Sisyphus loop files (gitignored)
├── skills-lock.json                # 14 locked agent skills (gitignored)
├── site/                           # MkDocs build output
└── .worktrees/, .venv/, .benchmarks/, .coverage*, .hypothesis/, .mypy_cache/, .ruff_cache/, .import_linter_cache/, .codegraph/, .playwright-cli/  # build/CI artifacts (gitignored)
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Product vision | `README.md` → `docs/concepts/RELEASE_NOTES_v1.0.0.md` |
| Architecture | `docs/reference/architecture.md` (and 11 ADRs in `docs/adr/`) |
| Module layout | `docs/reference/package-structure.md` ("Stable v1" — code structure source of truth) |
| Replay model | `docs/reference/replay-and-determinism.md` (SHA-256, no recompute) |
| Security | `docs/security/index.md` (threat model, PII, secrets-by-reference) |
| Test strategy | `docs/contributing/testing-strategy.md` (5-layer data, property tests) |
| Add adapter/capability/provider | `docs/howto/add_adapter.md`, `docs/howto/add_capability.md`, `docs/howto/add_inference_provider.md` |
| Dev setup | `docs/contributing/development.md` (uv, Makefile, release) |
| Dependency policy | `docs/reference/dependencies.md` (core ≤ 4 pkgs, no numpy/torch/requests) |
| Architecture change | `docs/adr/` (MADR template; ADRs immutable once Accepted) |
| Test data + licensing | `docs/contributing/test-data.md` + `tests/fixtures/DATASET_LICENSES.md` |
| Vocabulary | `docs/reference/glossary.md` |
| Dict DSL / InputProfile / cost model | `docs/specs/` (3 design specs + README) |
| Public API contract | `src/paxman/__init__.py` (PEP 562 lazy `__getattr__`, `__all__` = 29 symbols) |
| Public types/errors | `src/paxman/api/types.py`, `src/paxman/api/errors.py` |
| Public `normalize()` / `replay()` | `src/paxman/api/normalize.py`, `src/paxman/api/replay.py` |
| Golden artifacts | `tests/fixtures/artifacts/` (8 goldens + `_catalog.py` + `GENERATION.md`) |

## CODE MAP (7 subsystems + 9 cross-cutting modules)

All seven planned subsystems are implemented under `src/paxman/`. Each has a single responsibility and a hard boundary rule.

| Subsystem | Path | Responsibility | Boundary rule |
|-----------|------|----------------|---------------|
| `contract/` | `src/paxman/contract/` | Adapter + validation (4 formats → `CanonicalContract`) | **Only layer that knows about external schemas.** Holds `CanonicalContract`, `CanonicalField`, `MoneyValue`, validator, semantics, and the 4 adapters (`pydantic`, `json_schema`, `openapi`, `dict_dsl`). |
| `planner/` | `src/paxman/planner/` | Field-centric plan synthesis (deterministic, rule-based) | **Never executes. Emits `FieldPlan`s only.** Holds `ExecutionPlan`, `FieldPlan`, `FieldPlanStep`, heuristics, `input_profile`, policies, scoring. |
| `capabilities/` | `src/paxman/capabilities/` | 5 atomic ops: `text_extraction`, `regex_extraction`, `lookup`, `inference`, `validation` | **Never assign confidence. Never read canonical contract directly.** Holds `Capability` base, `CapabilitySpec`, `Candidate`/`CapabilityResult`/`EvidenceRef`, and `v1/` with the 5 ship capabilities. |
| `executor/` | `src/paxman/executor/` | Runs plan, collects evidence, stops early | **Never replans. Never assigns confidence. Never reads raw input directly.** Holds the executor loop, `field_runner`, `budget_tracker`, `context`, `early_stop`, `evidence`, `execution_state`. |
| `reconciler/` | `src/paxman/reconciler/` | Merges candidates, assigns final confidence, resolves truth | **Sole confidence authority. Never executes. Never reads raw input. Never sees external schemas.** Holds reconciler, `confidence`, `merge`, `conflict`, `money` (only module allowed `import decimal`), `validation`, `unresolved`, `truth`, `evidence_compare`. |
| `artifact/` | `src/paxman/artifact/` | `ExecutionArtifact` + replay hash + diagnostics | **Replay rehydrates captured truth — never recomputes.** Holds artifact, `_hash` (SHA-256), replay, serializer, diagnostics, evidence, confidence aggregator, statistics. |
| `api/` | `src/paxman/api/` | Public surface — `normalize()`, `replay()`, `register_adapter`, `register_capability`, public types/errors, `__version__` | **No internal concepts leak (no `FieldPlan`, no `CapabilitySpec`, no `TruthLayer` by name).** Holds `normalize`, `replay`, `registry`, `types`, `errors`, `protocols`, `version`. |

**Cross-cutting modules** (at `src/paxman/` root, never import from subsystem layers):

| Module | Purpose |
|--------|---------|
| `__init__.py` | Public API, PEP 562 lazy `__getattr__`, `__all__` = 29 symbols. Eager-loads only `__version__`; defers everything else until first attribute access. |
| `py.typed` | PEP 561 marker |
| `budget.py` | `Budget`, `Policy`, `CurrencyPolicy` |
| `clock.py` | Injectable `Clock` + `FakeClock` (no `time.time()` in core) |
| `errors.py` | 17 exception classes (11 public, 6 internal) |
| `ids.py` | Prefixed ID helpers |
| `logging.py` | `structlog` factory (no timestamps in replay) |
| `protocols.py` | Internal `Protocol` definitions |
| `serialization.py` | Stable JSON encoder (RFC 8785-style) |
| `types.py` | `Status` (5), `ConfidenceBand` (5), `FieldType` (9) enums |
| `versioning.py` | `__version__`, format-version constants, semver utilities |

**Public testing sub-package** (`paxman.testing`, shipped `py.typed`): 7 Hypothesis strategies (`contracts`, `inputs`, `budgets`, `policies`, `registries`, `candidate_sets`, `artifacts`), an `install_registry()` context manager, and re-exports of internal types for test fixtures only.

## CONVENTIONS (PROJECT-SPECIFIC)

- **Python ≥ 3.11** (CI matrix: 3.11 / 3.12 / 3.13), src-layout, `hatchling` build backend, `uv` package manager
- **Core deps (4 packages):** `attrs>=23.0`, `typing-extensions>=4.0`, `structlog>=24.1`, `packaging>=24.0` (no numpy/torch/requests)
- **Optional adapter extras:** `pydantic` (≥2.5), `json-schema` (`jsonschema>=4.20`), `openapi` (`openapi-spec-validator>=0.6`), `all` (all three), `test` (`hypothesis>=6.0`)
- **Data classes:** `attrs` for core, NOT pydantic (pydantic is adapter-only)
- **Naming:** `snake_case` modules/functions, `PascalCase` classes, `SCREAMING_SNAKE_CASE` enums/statuses/bands/error codes
- **Type hints mandatory** on every public symbol; `py.typed` shipped (PEP 561)
- **Mypy `--strict`** on `src/paxman`; **pyright** cross-validates
- **Ruff:** `E,F,W,I,B,UP,ANN,ASYNC,S,RUF`; line-length 100; `S101` (asserts) OK in tests
- **Docstrings:** Google style; `interrogate` enforces 100% on public surface (`make docs-check`)
- **Test markers:** `deterministic`, `replay`, `property`, `slow`, `integration`, `unit`
- **Coverage:** `coverage` `fail_under=90`; per-subsystem thresholds enforced by `scripts/check_subsystem_coverage.py` (D7.15)
- **Confidence bands (fixed):** `CERTAIN`, `HIGH`, `MEDIUM`, `LOW`, `UNTRUSTED`
- **MONEY first-class:** `amount` + ISO-4217 currency + precision (`Decimal`, never `float`); only `reconciler/money.py` may `import decimal`
- **9 V1 field types:** `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`
- **Status enum:** `SUCCESS`, `PARTIAL_SUCCESS`, `UNRESOLVED`, `INVALID_CONTRACT`, `EXECUTION_FAILED`
- **JSON serialization:** sorted keys, no whitespace, RFC 8785-style (never mock the encoder)
- **Confidence is sole-owned by Reconciler** (ADR-0005); capabilities never assign; planner may emit `target_confidence` only
- **Import-linter** enforces 6 layer contracts that the subsystem boundaries must not violate

## ANTI-PATTERNS (ZERO TOLERANCE)

- `# type: ignore`, `# pyright: ignore`, `as any`, `# noqa` in `src/paxman/` — **CI rejects**
- `paxman.normalize()` is **synchronous and not thread-safe** (V1). No async API. (V2.)
- **Sequential execution only** (ADR-0006). No parallel field execution in V1.
- **Replay is pure deserialization.** Never invoke capability/planner/executor/reconciler during replay.
- **Secrets by reference only.** Never embed API keys in artifacts.
- **Raw input never in logs by default** (`Policy.log_raw_input: bool = False`)
- **Inference output is untrusted until validated** (the `inference` capability is a stub in V1; real remote LLM calls are out of scope)
- **Adding a public API surface requires an ADR** (caught by `tests/public_api/test_public_api.py` snapshot)
- **Adding a core dependency requires an ADR** (`docs/reference/dependencies.md`)
- **No persistence in core.** No storage imports anywhere.
- **No real PII in test data.** License gating enforced by `scripts/fetch_test_data.py --validate-licenses`.
- **Determinism violation = test failure.** Property-tested with Hypothesis `derandomize=True`.
- **Mocking the JSON encoder is forbidden** — use the real `serialization` module.
- **Internal concept leakage** in `api/` (e.g. `FieldPlan`, `CapabilitySpec`, `TruthLayer` by name) is a public-API contract violation.

## UNIQUE STYLES

- **Contract = caller-owned.** Paxman never owns schemas, ontologies, or business standards.
- **Field-centric, not document-centric.** One `FieldPlan` per required field. (ADR-0001)
- **Planner is a pure function** — no LLM, no agent, no AI-generated planning logic in V1. (ADR-0002)
- **Reconciler is a first-class subsystem** owning final truth + final confidence. (ADR-0003)
- **Three truth layers are explicit:** Contract Truth, Candidate Truth, Resolved Truth.
- **Errors are structured:** every exception carries `error_code` (string) + `context` dict.
- **Status vs Exception:** Status = expected failure in artifact (`UNRESOLVED`); Exception = unrecoverable.
- **V1 ships exactly 5 capabilities** (`text_extraction`, `regex_extraction`, `lookup`, `inference`, `validation`) + 4 adapters (`pydantic`, `json_schema`, `openapi`, `dict_dsl`) per ADR-0007. Everything else is V2.
- **Cross-cutting modules never import from subsystem layers** (`errors.py`, `types.py`, `protocols.py`, `versioning.py`, `logging.py`, `budget.py`, `clock.py`, `ids.py`, `serialization.py`).
- **Money is Decimal-only.** `reconciler/money.py` is the sole module that may `import decimal`.
- **Public API is lazy.** `import paxman` only loads `__version__`; all other public symbols resolve on first attribute access via PEP 562 `__getattr__` (D9.5 cold-start optimization).
- **Documented alternatives:** the `paxman.testing` sub-package re-exports internal types for test fixtures only — those are not part of the stable public API.

## COMMANDS (WIRED — Makefile, 32 targets)

```bash
# Dev setup
make install                # uv sync --all-extras --dev
make install-frozen         # uv sync --frozen --all-extras --dev  (CI)

# Test
make test                   # all
make test-unit              # tests/unit
make test-integration       # tests/integration
make test-property          # tests/property (Hypothesis)
make test-public-api        # tests/public_api (snapshot)
make test-cov               # with coverage report
make check-coverage         # per-subsystem thresholds (D7.15)
make test-examples          # run all 3 example smoke test suites

# Lint / format / type / imports / docs / security
make lint                   # ruff check
make lint-fix               # ruff check --fix
make format                 # ruff format
make format-check           # ruff format --check
make typecheck              # mypy --strict src/paxman
make typecheck-pyright      # pyright src/paxman
make imports                # import-linter (6 layer contracts)
make docs-check             # interrogate (100% docstring coverage on public surface)
make security               # bandit -r src/paxman
make security-audit         # bandit + pip-audit

# Benchmarks
make benchmark              # pytest-benchmark (10 rounds, 3 warmup)
make benchmark-quick        # pytest-benchmark (3 rounds)
make profile                # cold-import benchmark (20 iterations)

# Test data
make test-data-vendor       # vendor V1 corpus
make test-data-list         # list vendored datasets
make test-data-verify       # verify vendored data

# Docs
make docs                   # build RTD site (MkDocs)

# Build / publish
make build                  # hatchling build → dist/
make build-verify           # build + verify wheel contents
make clean                  # remove build artifacts
make clean-all              # clean + remove venv
make publish-test           # TODO (TestPyPI)
make publish                # TODO (PyPI)

# Full local CI (10 checks — same as GitHub Actions)
make ci                     # install-frozen → lint → format-check → typecheck → typecheck-pyright → imports → docs-check → security → test-examples → test-cov
```

## NOTES

- **Current version: 1.0.1** (`pyproject.toml` `version = "1.0.1"`). v1.0.0 shipped the full V1; v1.0.1 is a critical bugfix release for contract-detection and adapter bugs (see PR #65).
- **CI has 11 jobs** in `.github/workflows/ci.yml`: lint, pyright, interrogate, bandit, pip-audit, test-unit (3.11/3.12/3.13 matrix), test-property, test-integration, test-examples, test-coverage + build. Plus `release.yml` (OIDC trusted publishing to PyPI on `v*` tag push), `deploy.yaml` (Cloudflared SSH deploy to main), and `opencode.yml` (slash-command trigger).
- **11 ADRs** (0001-0011) in `docs/adr/`: field-centric planning, rule-based planner, separate reconciler, MONEY first-class, confidence ownership, sequential execution, contract adapter set, license (MIT), dict DSL v1, budget-money-decimal, format auto-detection. ADRs are immutable once Accepted.
- **Public API target: ≤ 5 functions in V1** (`normalize`, `replay`, `register_adapter`, `register_capability`, `__version__`). 29 public symbols total (functions + types + errors + protocols).
- **Coverage targets:** mypy 100% on public surface (interrogate); pytest `fail_under=90`; per-subsystem thresholds enforced by D7.15.
- **Cold-start target: ≤ 100 ms** (D9.5). Measured: 37 ms p50 / 60 ms p99 on Sprint 9 hardware (PEP 562 lazy loading). See `README.md` perf table for full D9.5 before/after numbers.
- **Aspirational perf** (Sprint 9 baseline, commit `71941f5`): `normalize()` 20-field/100 KB → 24.30 ms p50; `replay()` 5 KB → 1.17 ms p50; `replay()` 100 KB → 0.90 ms p50; cold import → 37 ms p50. Run `make benchmark` and `make profile` for up-to-date local numbers.
- **License: MIT** (file `LICENSE`, ADR-0008). Apache-2.0 is the documented alternative if patent concerns emerge.
- **`tests/fixtures/artifacts/`** holds 7-8 golden JSON artifacts + `_catalog.py` + `GENERATION.md` — bootstrapped via `scripts/bootstrap_golden_artifacts.py` from real implementations, never predicted.
- **Research-only datasets** (SROIE, INV-CDIP, FATURA, plus `wildreceipt/`, `oqo/`, `polish_tenders/`, `ted_sample/`, `alamgirqazi/`, `invoicebench/`) may be vendored under `tests/fixtures/inputs/` but their code paths are NOT exercised in CI.
- **Diátaxis docs reorg in progress** (Sprint 11): `docs/` is being reorganized into `concepts/`, `howto/`, `reference/`, `contributing/`, `operations/`, `security/`. Top-level `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md` are short stubs linking into `docs/`.

## AGENT MEMORY (opencode-mem)

> **For every future agent (new session, new task, new sub-task) on this project: READ THIS SECTION FIRST.**

This project is wired to the **opencode-mem** plugin — a local persistent memory store + Memory Explorer UI that captures cross-session context, user preferences, project conventions, and conversation history.

- **Storage:** `~/.opencode-mem/data/metadata.db` (SQLite, project memories) + `~/.opencode-mem/data/user-profiles.db` (cross-project user-profile memories)
- **Config:** `~/.config/opencode/opencode-mem.jsonc` — `autoCaptureEnabled: true`, `webServerEnabled: true` on port `4747`, embedding model `Xenova/nomic-embed-text-v1`
- **Explorer UI:** <http://localhost:4747> — browse, search, pin, and curate memories
- **Auto-injection:** the top-3 most relevant project memories are auto-injected on the **first user message of each new session** (`chatMessage.injectOn: "first"`, `chatMessage.excludeCurrentSession: true`) — so most agents will already have project context pre-loaded; the rules below are for **what to do beyond that**.

### Why this matters

Paxman has hard architectural rules (subsystem boundaries, no `as any`, money-is-Decimal, sequential-execution-only, replay-is-pure-deserialization, no internal-concept-leakage in the API, …) and Leonidas has strong working-style preferences (TDD-first, evidence-before-claim, codegraph-over-grep, minimal fixes, AI-slop-removal). Many of these are now in the memory store, **not** in this file. Always check memory before re-deriving them.

### When to consult opencode-mem (MANDATORY workflow)

| When | What to do |
|---|---|
| **Session start** | Use the `memory` tool with `mode=search` to query for: `paxman conventions`, `paxman anti-patterns`, `subsystem boundaries`, `reconciler confidence`, `replay determinism`, `user workflow preferences`. Read the top hits before doing anything. |
| **User asks about past work** ("what did we do last time", "remember when we…", "we discussed…") | Search memory with the conversation topic as query. Do **not** guess from this file — it only contains static project knowledge, not session history. |
| **About to write a fix / refactor / new feature** | Search for the topic — there is often a recorded user preference ("prefers minimal fix over refactor", "rejects internal concept leakage", etc.) that constrains the approach. |
| **User references a previous session, PR, or discussion by name** | Search the memory DB; do not assume it's in this file. |
| **Major implementation work begins** | Search `mode=search` with the subsystem name to retrieve the latest captured boundary rules and decisions. ADRs are immutable but the *user's current preferences* about them can drift — memory captures that drift. |
| **At task completion** | Consider `mode=add` to record: non-obvious decisions, user corrections, newly-stated preferences, the *what+why* of any non-trivial change. The next agent in the chain benefits. |

### How to query the memory store

You have three access paths. Use the one that matches the moment.

1. **`memory` tool (in-process, fastest, recommended)**
   - `mode=search` with a natural-language query and a `scope` of `project` (default) or `user` — returns ranked hits with content + tags.
   - `mode=add` to record a new memory (use `tags` liberally: `project`, `subsystem-name`, `decision`, `user-preference`, `anti-pattern`).
   - `mode=list` to enumerate everything currently stored.
   - `mode=profile` to see the user-profile cross-project model.
   - `mode=forget` to remove memories that turned out to be wrong or stale.

2. **HTTP API (works from any process; useful for scripts/CI/debug)**
   - `GET  http://localhost:4747/api/memories?scope=project&page=1&pageSize=20`
   - `GET  http://localhost:4747/api/search?q=<query>&limit=5` (semantic, vector-based)
   - `GET  http://localhost:4747/api/stats`
   - `POST http://localhost:4747/api/memories` with JSON body `{content, tags, scope}`
   - Server is local; do not expose publicly.

3. **Memory Explorer UI (human-facing)**
   - <http://localhost:4747> — Pin, edit, delete, deduplicate, export, switch `PROJECT` ↔ `USER PROFILE` tabs.
   - Use this when the user wants to curate, not just retrieve.

### What is currently in memory (snapshot)

Seeded on **2026-07-01** with 5 baseline project memories (under `scope=project`):

1. **Paxman overview** — what it is, public API, headline rules (contract-driven, deterministic, evidence-backed, replayable).
2. **7 subsystems + boundary rules** — `contract/`, `planner/`, `capabilities/`, `executor/`, `reconciler/`, `artifact/`, `api/`, plus 9 cross-cutting modules and their boundary contracts.
3. **Project conventions** — Python ≥ 3.11, src-layout, hatchling, uv, core deps (4 packages), ruff/mypy/pyright/pytest, docstring discipline, coverage thresholds.
4. **Zero-tolerance anti-patterns** — `as any`/`# type: ignore`/noqa, async/parallel in V1, recompute-during-replay, secrets-in-artifacts, raw-input-in-logs, public-API surface growth, internal-concept leakage, JSON-encoder mocking, real PII in test data.
5. **Leonidas's workflow preferences** — delegation chain (explore/librarian/oracle/momus), codegraph-over-grep, skill-loading-first, TDD, evidence-before-claim, minimal-fix-during-bugfix, anti-AI-slop.

Plus a `scope=user` profile that the plugin refines automatically every 10 turns (`userProfileAnalysisInterval: 10`) — it aggregates cross-project behavioural patterns, not project-specific facts.

### Anti-patterns specific to opencode-mem itself

- **Do NOT skip the `memory search` step on session start.** This is the single most common mistake. If you don't search, you re-derive rules that are already in the store, waste context, and risk contradicting a stated user preference.
- **Do NOT treat this AGENTS.md file as a complete picture of user/project state.** It is a static project-knowledge snapshot. Cross-session context, evolving preferences, and conversation history live in opencode-mem.
- **Do NOT write project-specific facts into the `user` scope** (that's cross-project) — use `project` for Paxman-only knowledge.
- **Do NOT write secrets, raw input, or PII into memory** (mirrors the project's `Policy.log_raw_input: bool = False` default — same rule applies to memory).
- **Do NOT add memories that contradict ADRs.** ADRs are immutable; if a memory would, raise it with the user first.
- **Do NOT poll `background_output` on opencode-mem tasks** — let the system notify you.
- **When in doubt, prefer `mode=search` over re-reading this file.** Memory is the source of truth for evolving context; this file is the source of truth for static structure.

### Plugin operational notes

- The plugin runs in-process with the opencode server. If `localhost:4747` is unreachable, the plugin is not running — start opencode and it will boot.
- `autoCaptureEnabled: true` means **the plugin is already writing memories on its own** when meaningful context appears in the conversation. You do not need to duplicate capture — use `mode=add` only for things auto-capture misses (cross-task decisions, explicit user corrections, post-implementation summaries).
- Compaction is on (`compaction.enabled: true`, `memoryLimit: 10`) — older, lower-signal memories are pruned automatically. Pin the ones that must survive.
- If the user says the plugin isn't working: `curl http://localhost:4747/api/stats` first; if it returns, capture is working but the UI may need a refresh. If it 404s, the web server is disabled in config.

# Proposed v2 folder structure

> **Status:** Proposal. The v1.x tree is gone; this is the empty foundation
> the v2 code will grow into. Anything not listed here is intentionally
> absent — the v1.x project had 47 directories and 1,081 tracked files
> for a library that did not work. v2 starts with what is necessary and
> adds only what the code demands.

## The principle

The v1.x project confused *infrastructure* with *implementation*. There
were seven subsystems, four contract adapters, five capabilities, ten
ADRs, eight design specs, and a four-level test-data model — all to
deliver a function that returned `{}` for every realistic input. v2 inverts
this: the code is what it is, and the structure follows.

The only constraint v2 places on itself, by design, is **determinism**.
Every directory, file, and module exists to support the determinism
contract or it does not exist.

---

## The working tree (committed files)

```text
paxman/
├── README.md                          # what the library is, what it is not
├── RETRACTION.md                      # permanent record of the v1.x failure
├── LICENSE                            # MIT
│
├── pyproject.toml                     # project metadata, dependencies
├── .gitignore                         # universal Python + toolchain patterns
├── .pre-commit-config.yaml            # ruff, mypy, interrogate
├── .coderabbit.yaml                   # code-review assistant config
│
├── .github/                           # CI + issue templates + CODEOWNERS
│   ├── workflows/
│   │   └── ci.yml                     # single workflow: test, lint, type-check
│   ├── ISSUE_TEMPLATE/
│   │   └── bug_report.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
│
├── .agents/
│   ├── PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md
│   │                                   # the v1.x audit; permanent record
│   └── skills/                         # agent skills (gitignored, dev-only)
│
├── src/
│   └── paxman/                        # the library
│       ├── __init__.py                 # public API: normalize, replay
│       ├── _core/                     # pure functions: parse, canonicalize, project
│       │   ├── canonicalize.py
│       │   ├── project.py
│       │   └── replay.py
│       ├── _contracts/                # contract adapters (kept minimal)
│       │   ├── dict_dsl.py            #   one format; the canonical one
│       │   └── __init__.py
│       └── _errors.py                 # error hierarchy
│
└── tests/                             # the test suite
    ├── unit/                          # fast, pure-function tests
    ├── property/                      # hypothesis: determinism invariants
    └── integration/                   # the README quickstart, end-to-end
```

**Total: 4 Python source files, 3 test directories, 12 top-level entries.**

Compare to the v1.x tree, which had:
- 7 subsystems × ~10 files each
- 4 contract adapters × ~5 files each
- 10 V1 capabilities × ~3 files each
- 11 ADRs, 4 design specs, 6 how-tos, 9 reference docs
- 1,081 tracked files

v2 starts with **~10 source files and 12 top-level entries**.

---

## What is gone, and why

The following v1.x directories and files were removed because they
encoded decisions the v1.x project was wrong about. Removing them is
not cleanup; it is refusal to re-inherit the v1.x architecture.

| v1.x artifact | Why it is gone |
|---|---|
| `src/paxman/api/` (normalize, replay, registry) | v2 has two public functions, not a 7-stage orchestration. |
| `src/paxman/contract/` (4 adapters, registry, canonical, _types) | v2 starts with Dict DSL only; Pydantic/JSON Schema/OpenAPI are v2.x concerns. |
| `src/paxman/planner/` (heuristics, field_plan, input_profile) | The 7-step planner was the v1.x core failure. v2 has no planner. |
| `src/paxman/capabilities/` (10 capabilities, registry, base) | Capabilities imply orchestration. v2 has a single canonicalization step, not a capability graph. |
| `src/paxman/executor/` (executor, field_runner, budget_tracker) | There is nothing to execute. The canonicalization step is one function call. |
| `src/paxman/reconciler/` (reconciler, confidence, conflict, merge) | The "reconciler picks between multiple candidates" model is gone. If there is ambiguity, v2 returns no result. |
| `src/paxman/artifact/` (artifact, replay, _hash, statistics) | The artifact is the result. There is one canonical artifact schema. |
| `src/paxman/budget.py`, `src/paxman/policy.py` | There is no budget. There is no policy. Determinism is unconditional. |
| `src/paxman/capabilities/v1/inference.py` (the stub) | The LLM stub is deleted. v2 does not pretend to have inference. |
| `src/paxman/providers/` (the v1.2.0 SPI work) | v2 does not have a provider model. The SPI is for an LLM; v2 has no LLM. |
| `tests/integration/`, `tests/property/`, `tests/unit/`, `tests/fixtures/`, `tests/public_api/`, `tests/benchmark/` | Tests are tests. The v1.x project had a 5-layer test-data model, a public-API snapshot test, and benchmark tests. v2 has three directories. |
| `examples/` (3 mini-packages) | v1.x examples demonstrated broken behavior. v2 has no examples; the README is the example. |
| `playground/` (Docker, Jupyter, notebooks) | v1.x notebooks demonstrated broken behavior. v2 has no playground. |
| `docs/adr/` (11 ADRs) | The ADRs describe a v1.x architecture that does not exist in v2. |
| `docs/concepts/`, `docs/reference/`, `docs/howto/`, `docs/specs/`, `docs/guides/`, `docs/contributing/`, `docs/security/`, `docs/operations/`, `docs/initiatives/`, `docs/superpowers/` | Diátaxis is a documentation framework for projects that have something to document. v2 has not earned documentation yet. |
| `docs/index.md` (the RTD landing page) | v2 has no RTD site. |
| `mkdocs.yml`, `.readthedocs.yaml` | v2 has no docs site. |
| `scripts/` (golden bootstrap, coverage check, fetch_test_data, benchmark_import_time) | Scripts that are tied to v1.x subsystems. v2 has no scripts. |
| `Makefile` (236 lines, 47 targets) | v2 has no Makefile. `uv run` is enough. |
| `Makefile` targets: `make ci`, `make test`, `make test-cov`, `make test-unit`, `make test-property`, `make test-integration`, `make test-examples`, `make test-data-verify`, `make lint`, `make format`, `make format-check`, `make typecheck`, `make typecheck-pyright`, `make imports`, `make docs-check`, `make security`, `make benchmark`, `make benchmark-quick`, `make profile`, `make playground-build`, `make playground-up`, `make build`, `make publish`, `make publish-test`, `make install-frozen`, `make install`, `make clean`, `make coverage-html`, `make coverage-report`, `make coverage-erase`, `make coverage-badge`, `make all-v1-types-golden`, `make money-golden`, `make replays-reproducibility`, `make check-public-api`, `make check-imports`, `make check-interrogate`, `make test-data-fetch`, `make examples-install`, `make examples-test`, `make examples-lint`, `make docs-serve`, `make docs` | All 47 targets reference v1.x subsystems. None of them is meaningful for v2. |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `AGENTS.md` | Stub files that referenced the v1.x project structure. v2 has no equivalent stubs. |
| `pyrightconfig.json`, `pyrightconfig-strict.json` | v1.x had a "pyright strict mode" initiative (closed in v1.1.0). v2 has one pyright config when it is needed. |

---

## What stays, and why

| Path | Why |
|---|---|
| `README.md` | The library needs a README. v2's README states what the library is and is not, with no marketing copy. |
| `RETRACTION.md` | Permanent record of the v1.x retraction. Future contributors (including the v2 author) need to read it before making decisions. |
| `LICENSE` | MIT. Unchanged. |
| `.gitignore` | Universal Python + uv + toolchain patterns. No project-specific exclusions. |
| `.pre-commit-config.yaml` | ruff + mypy are non-negotiable. |
| `.coderabbit.yaml` | Code review assistant config (v1.x had it; harmless to keep). |
| `.github/` | CI workflow, issue templates, dependabot, CODEOWNERS. The CI workflow is the one v1.x workflow that v2 keeps; the rest is gone. |
| `.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md` | The audit. v1.x failed in a specific way; v2 needs to know that failure to avoid it. |
| `.agents/skills/` | Agent skills (development-only, gitignored). Not part of the library. |

---

## The v2 library (what is in `src/paxman/`)

The v2 library is four Python files. Each file has one job.

| File | Job |
|---|---|
| `__init__.py` | The public API. `paxman.normalize(input, contract)`, `paxman.replay(artifact, contract)`. Nothing else is exported. |
| `_core/canonicalize.py` | The single function that turns input + contract into a canonical form, or refuses. Pure, deterministic, no I/O. |
| `_core/project.py` | Type-narrowing: from the canonical form, project to a typed result (the contract's type). |
| `_core/replay.py` | The byte-equal rehydration. Given an artifact and a contract, return the same artifact. |
| `_contracts/dict_dsl.py` | The one contract format v2 supports. Dict DSL is sufficient: the caller describes the canonical shape as a dict, Paxman enforces it. |
| `_errors.py` | `CanonicalizationError`, `AmbiguousInputError`, `ContractError`, `VersionMismatchError`. |

If the v2 implementation grows to need more modules, they go under
`src/paxman/_core/` (pure logic) or `src/paxman/_contracts/` (contract
adapters). The leading underscore on both names is a soft signal to
readers and to `import-linter` that they are internal; the public API
is the `paxman.normalize` and `paxman.replay` exports from `__init__.py`.

The `examples/`, `playground/`, `docs/` directories do not exist in v2.
When the v2 library has features worth showing off, examples grow on
demand. Documentation grows when the API stabilizes. The README is the
only contract the user has with v2 right now.

---

## The v2 test suite (what is in `tests/`)

Three directories, each with one role.

| Directory | Role |
|---|---|
| `tests/unit/` | Fast, pure-function tests. One test file per source file. No I/O, no time, no network. |
| `tests/property/` | Hypothesis property tests. The single most important property: **for any (input, contract), `replay(normalize(input, contract), contract) == normalize(input, contract)` byte-for-byte.** |
| `tests/integration/` | The end-to-end test that runs the README example. If the README example ever returns `{}` again, the test fails and the build is red. |

There is no `tests/fixtures/`, no `tests/benchmark/`, no
`tests/public_api/`. The v1.x project had a 5-layer test-data model
and a 2,754-test suite that verified plumbing. v2 has one test per
behavioral claim, plus a hypothesis property per determinism invariant.

---

## Decisions left to make

The folder structure is the easy part. The hard decisions are the
ones the folder structure defers to the code. The v2 author will need
to make these decisions before the first `paxman.normalize` call
can be written:

1. **What is a "canonical form"?** Is it a JSON object with sorted keys? A specific byte sequence? A typed Python value? The README promises "a single canonical form" but does not say what one is. The v2 code decides.
2. **How does the contract express canonicality?** Dict DSL is the starter format, but it cannot express "the only valid canonical form is the sorted-key JSON of this dict" without more machinery. The v2 `_contracts/dict_dsl.py` module decides.
3. **What does `paxman.replay` do when the artifact is from a different Paxman version?** v1.x raised `VersionMismatchError`. v2 might allow it (the byte-equal contract is the same) or reject it (a more conservative posture). The v2 `_core/replay.py` module decides.
4. **Does the v2 library support Pydantic / JSON Schema / OpenAPI contracts?** v1.x did; v2 deliberately does not. v2.x can add them when there is a use case. The v2 roadmap decides.

These are not folder-structure decisions. They are design decisions,
and the folder structure does not constrain them. The folder structure
exists to keep the design decisions visible — small, honest, scoped.

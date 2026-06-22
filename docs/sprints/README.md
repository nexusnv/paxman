# Paxman V1 — Sprint Plan

> **Status:** Planning deliverable (no code).
> **Branch:** `sprint-planning-v1`
> **Generated:** 2026-06-22
> **Target release:** Paxman 1.0.0 on PyPI
> **Total duration:** 10 sprints (~5 months at 2-week sprints + 3-week Sprint 10 for release)

This directory contains the **complete sprint planning** for taking Paxman from its current state (zero source code, design-only) to a production-ready 1.0.0 release. Each sprint has scope, deliverables, prerequisites, exit criteria, risk register, and per-sprint tooling/API-key/prerequisite checklist.

## How to read this plan

| Reader | Read first |
|---|---|
| **Project lead / engineering manager** | `README.md` (this file) → `sprint-00-design-closure.md` → `sprint-10-release.md` |
| **Engineer starting Sprint N** | `sprint-NN-*.md` only — each is self-contained |
| **Stakeholders / reviewers** | `README.md` → `CHANGES_LOG.md` → each sprint's "Exit Criteria" |
| **Operations / DevOps** | `sprint-01-foundation.md` §Prerequisites + `sprint-08-docs-ci-hardening.md` |
| **Security reviewer** | `sprint-09-production-hardening.md` + `sprint-10-release.md` §Security |

## Sprint overview

| # | Name | Focus | Duration | Ideal Eng-Days | Exit artifact |
|---|---|---|---|---|---|
| **0** | Design closure | 3 spec gaps + license decision | 1 week | 3 | `docs/sprints/v0-specs/` containing Dict DSL spec, Input Profile spec, CostHint values per capability, license ADR |
| **1** | Foundation | pyproject.toml, Makefile, CI, src layout, all 9 cross-cutting modules, py.typed, smoke test | 2 weeks | 18 | `pip install -e .` works, `make ci` is green, public `paxman/__init__.py` empty re-export shell |
| **2** | Contract subsystem | `contract/canonical.py`, `contract/_types.py`, `contract/validator.py`, Pydantic + Dict DSL adapters, fixture contracts | 2 weeks | 14 | `paxman.contract.adapt(InvoiceModel) → CanonicalContract` round-trips; first passing adapter tests |
| **3** | Planner + 3 capabilities | `planner/*` (7 modules), 3 capabilities (text_extraction, regex_extraction, validation), planner determinism tests | 2 weeks | 16 | `paxman.normalize(text, contract)` produces a deterministic `ExecutionPlan` (no execution yet); first capability unit tests pass |
| **4** | Executor + 2 capabilities | `executor/*` (7 modules), `lookup` + `inference` capabilities with stub provider, golden JSON encoder | 2 weeks | 15 | End-to-end: `normalize(text, contract)` produces `ExecutionArtifact` with candidates + evidence (no confidence yet) |
| **5** | Reconciler | `reconciler/*` (9 modules) including `money.py`, `fetch_test_data.py` fully implemented | 2 weeks | 15 | `normalize()` returns a confidence-scored artifact; `MONEY` arithmetic property-tested; adversarial corpus vendored |
| **6** | Artifact + API | `artifact/*` (8 modules), `api/*` (7 modules), `paxman.normalize()` end-to-end, replay rehydration | 2 weeks | 16 | `paxman.normalize()` and `paxman.replay()` work end-to-end; first golden artifact produced |
| **7** | Integration + property tests | E2E fixtures, golden artifacts (≥5), Hypothesis strategies, replay tests, public API snapshot | 2 weeks | 15 | Full test pyramid green: 90% coverage on `contract/`, `planner/`, `executor/`, `reconciler/`; 95% on `artifact/`; replay equality proven |
| **8** | Documentation + community + CI hardening | `docs/concepts/` (5 docs), `docs/howto/` (4 docs), `README.md` quickstart, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub Actions CI, import-linter, interrogate, bandit, pip-audit | 2 weeks | 14 | All CI checks pass on PR; documentation site builds; new contributor can ship a PR in <30 min |
| **9** | Production hardening | `pytest-benchmark` performance harness, security audit, p50/p99 measurements, import-time profiling, OIDC trusted publishing setup, issue/PR templates, branch protection | 2 weeks | 12 | `make ci` green + performance targets measured; security lint clean; `pip-audit` clean |
| **10** | Release | TestPyPI publish, v0.5.0 → v1.0.0 RC cycle, smoke install on 3 platforms (linux/amd64, osx/arm64, win/amd64), 3 external users validation, GitHub release, post-release retrospective | 3 weeks | 8 | **Paxman 1.0.0 on PyPI** with passing acceptance criteria, ≥3 external users, golden artifact reproducibility across two independent runs |

**Total: ~190 ideal engineering days across 10 sprints (5+ months) with a 4-person team.**

## Critical-path visual

```
Sprint 0  Design closure ─┐
                          ▼
Sprint 1  Foundation (cross-cutting) ─┐
                                      ▼
Sprint 2  contract/ + Pydantic + Dict DSL adapters ─┐
                                                    ▼
Sprint 3  planner/ + 3 capabilities (text, regex, validation) ─┐
                                                               ▼
Sprint 4  executor/ + 2 capabilities (lookup, inference) ─┐
                                                           ▼
Sprint 5  reconciler/ + MONEY + fetch_test_data.py ─┐
                                                     ▼
Sprint 6  artifact/ + api/ (normalize + replay) ─┐
                                                 ▼
Sprint 7  Integration + E2E + property tests + goldens ─┐
                                                        ▼
Sprint 8  Docs + CI hardening + community ─┐
                                           ▼
Sprint 9  Production hardening + OIDC ─┐
                                       ▼
Sprint 10 Release (v1.0.0) ─── DONE
```

## Pre-Sprint-0 (must complete before Sprint 1)

These are **decisions** the project owner must make; they are documented in `sprint-00-design-closure.md`:

1. **License decision:** MIT or Apache-2.0? (Currently TBD per `README.md`.)
2. **Dict DSL syntax:** Spec the internal Dict DSL format. Required as the "test source of truth" per ADR-0007.
3. **Input Profile spec:** What fields does `planner/input_profile.py` produce? How is `InputProfile` constructed?
4. **`CostHint` values per capability:** Document the cost model (`tokens, ms, usd`) for all 5 V1 capabilities.

## Critical parallelization

The following can run **in parallel** within a sprint (4-person team):

| Sprint | Parallel tracks |
|---|---|
| **1** | (a) cross-cutting modules, (b) `pyproject.toml` + `Makefile` + `.pre-commit-config.yaml`, (c) GitHub Actions CI workflow, (d) `.gitignore` + `LICENSE` + repo boilerplate |
| **2** | (a) Pydantic adapter, (b) Dict DSL adapter, (c) Validator + canonical model, (d) fixture Pydantic contracts + Dict DSL contracts |
| **3** | (a) `planner/heuristics.py` + `planner/scoring.py`, (b) `planner/field_plan.py` + `planner/input_profile.py`, (c) `capabilities/v1/regex_extraction.py` + `capabilities/v1/validation.py`, (d) `capabilities/v1/text_extraction.py` + tests |
| **4** | (a) `executor/field_runner.py` + `executor/budget_tracker.py`, (b) `executor/early_stop.py` + `executor/evidence.py`, (c) `capabilities/v1/lookup.py`, (d) `capabilities/v1/inference.py` with stub provider |
| **5** | (a) `reconciler/merge.py` + `reconciler/conflict.py`, (b) `reconciler/money.py` (MONEY arithmetic), (c) `reconciler/confidence.py` + `reconciler/unresolved.py`, (d) `fetch_test_data.py` implementation + license gating |
| **6** | (a) `artifact/artifact.py` + `artifact/evidence.py`, (b) `artifact/_hash.py` + `artifact/serializer.py`, (c) `artifact/replay.py` + `api/replay.py`, (d) `api/normalize.py` orchestration |
| **7** | (a) E2E fixtures + golden artifacts, (b) Hypothesis strategies, (c) replay equality tests, (d) public API snapshot test |
| **8** | (a) `docs/concepts/*` (5 docs), (b) `docs/howto/*` (4 docs), (c) `CHANGELOG.md` + `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md`, (d) GitHub Actions CI refinement + import-linter config |
| **9** | (a) Performance benchmarks, (b) security audit + bandit/pip-audit, (c) issue/PR templates, (d) OIDC trusted publishing setup |
| **10** | (a) TestPyPI publish + smoke tests, (b) external user validation, (c) GitHub release + changelog excerpt, (d) post-release retrospective |

## Sprint exit gate

A sprint is "done" when **all** of these are true:

- All scope items in that sprint's "Deliverables" section are complete.
- All exit-criteria tests pass.
- The CI matrix (py311/3.12/3.13) is green.
- `mypy --strict src/paxman` is clean.
- `ruff check` and `ruff format --check` are clean.
- `interrogate` reports 100% docstring coverage on the public surface.
- For sprints 2+: `import-linter` is clean (DAG contract).
- For sprints 6+: at least one end-to-end smoke test runs and produces an artifact.

## Definition of Done (V1)

Paxman 1.0.0 ships when **all V1 acceptance criteria** in `V1_ACCEPTANCE_CRITERIA.md` are checked. The Sprint 10 doc lists the specific checklist.

## See also

- `CHANGES_LOG.md` — documentation changes made during this planning exercise
- `../PRD.md` — product requirements and success metrics
- `../V1_ACCEPTANCE_CRITERIA.md` — definition of done for 1.0
- `../PACKAGE_STRUCTURE.md` — module layout (the source of truth for code structure)
- `../docs/adr/` — 7 ADRs that constrain the design

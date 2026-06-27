# Sprint 10 — Release (v1.0.0)

> **Duration:** 3 weeks
> **Goal:** Ship **Paxman 1.0.0** to PyPI, validate with **≥3 external users**, and conduct a **post-release retrospective**.
> **Status:** This is the **final sprint**. Paxman graduates from "v0.x pre-release" to "1.0.0 production-ready."

## Scope (in)

### Release cycle
- Tag `v1.0.0-rc.1` on `main`; publish to TestPyPI
- Smoke test the RC with the 3 target personas (per `PRD.md` §6.1):
  - Persona A: Backend developer building a normalization service
  - Persona B: AI engineer building an agentic ingestion flow
  - Persona C: SaaS team building procurement / invoice / quotation pipelines
- Fix any critical issues found in the RC
- Tag `v1.0.0`; publish to PyPI via OIDC
- Create GitHub release with changelog excerpt

### External user validation (gating)
- ≥3 external users (from the target personas) use Paxman for a real workload
- All 3 report no blocking issues (per `V1_ACCEPTANCE_CRITERIA.md` §5.4)
- ≥1 end-to-end fixture from a real-world use case reproduces the same `replay_hash` across two independent runs (per `V1_ACCEPTANCE_CRITERIA.md` §5.3)

### Final documentation
- Update `README.md` with v1.0.0 quickstart (the one verified in Sprint 8)
- Final `CHANGELOG.md` entry: `## [1.0.0] - YYYY-MM-DD`
- `docs/concepts/RELEASE_NOTES_v1.0.0.md` (or similar) — what shipped, what's deferred to V2

### Reference examples (3 personas, in-tree)
- `examples/backend_service/` — Minimal FastAPI service exposing `POST /normalize`.
  Mirrors D10.2 Persona A (Backend developer building a normalization service).
  The smoke-test script from D10.2 is the seed for this example.
- `examples/ai_agent_ingest/` — Stdlib-only, framework-agnostic tool-calling loop
  that calls `paxman.normalize()` from a fake agent step. **Intentionally
  framework-free** (no LangChain / LlamaIndex dep) so it survives framework churn
  and acts as a copy-able reference for any agent framework. Mirrors D10.2
  Persona B (AI engineer building an agentic ingestion flow).
- `examples/saas_procurement/` — Invoice/quotation batch pipeline: reads a CSV
  manifest of raw input files, calls `paxman.normalize()` per row, writes
  artifacts to disk. Mirrors D10.2 Persona C (SaaS team building
  procurement / invoice / quotation pipelines). **This example's output
  artifact is the D10.7 `replay_hash` reproducibility fixture.**
- Per-example contract (required for all 3):
  - `README.md` — problem statement, install, run, expected output
  - `pyproject.toml` declaring `paxman[pydantic]` as the only runtime dep
    (dev deps may include test frameworks; the core-dep-cap rule applies only
    to the main `pyproject.toml` per `DEPENDENCIES.md`)
  - `tests/` directory wired into `make ci` so examples are smoke-tested on
    every PR (no manual gate)
- Cross-link the 3 examples from the top-level `README.md` under a new
  "Examples" section so PyPI visitors land on runnable code, not just prose.

### Post-release retrospective
- Internal retrospective with the team
- Document the 5 things that went well, 5 things that didn't, 5 things to do differently in V1.x
- File V1.x issues (e.g., "open V1.1.0 perf sprint", "add type stubs", etc.)
- Update `docs/sprints/` with retrospective notes (`docs/sprints/retrospective-v1.0.0.md`)

### Repository finalization
- Verify `LICENSE` matches Sprint 0 decision
- Verify branch protection on `main` is enabled
- Verify all CI checks pass on `main`
- Tag `v1.0.0` in git
- Create GitHub release with changelog

## Scope (out)

- **V1.0.x patches** (post-release) — separate sprints.
- **V2 features** — LLM planner, async API, parallel execution, RAG, etc. (deferred).
- **Migration tooling** for v0.x → 1.0 — N/A (V1 is the first stable release).
- **Marketing / launch announcement blog post** (optional, post-sprint).

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D10.1 | `v1.0.0-rc.1` tag + TestPyPI publish | 0.5 |
| D10.2 | RC smoke test with 3 target personas (3 separate use cases) | 3.0 |
| D10.3 | Fix any critical issues found in the RC | 2.0 |
| D10.4 | `v1.0.0` tag + PyPI publish via OIDC | 0.5 |
| D10.5 | GitHub release with changelog excerpt | 0.3 |
| D10.6 | ≥3 external users validation (per `V1_ACCEPTANCE_CRITERIA.md` §5.4) | — (parallel; not engineer-effort) |
| D10.7 | ≥1 real-world fixture with cross-run `replay_hash` reproducibility | 0.5 |
| D10.8 | Final `CHANGELOG.md` update | 0.2 |
| D10.9 | `docs/concepts/RELEASE_NOTES_v1.0.0.md` | 1.0 |
| D10.10 | Post-release retrospective (`docs/sprints/retrospective-v1.0.0.md`) | 1.0 |
| D10.11 | V1.x issue list (created on GitHub) | 0.5 |
| D10.12 | Verify all V1 acceptance criteria in `V1_ACCEPTANCE_CRITERIA.md` are checked | 0.3 |
| D10.13 | Final CI run on `main` is green | — |
| D10.14 | `SECURITY.md` §7 disclosure email is real and monitored | 0.1 |
| D10.15 | Verify PyPI page renders correctly (project description, links) | 0.2 |
| D10.16 | Verify `pip install paxman` works on a clean machine (3 platforms) | 0.5 |
| D10.17 | `examples/backend_service/` (FastAPI + tests + README) | 0.8 |
| D10.18 | `examples/ai_agent_ingest/` (stdlib-only + tests + README) | 0.8 |
| D10.19 | `examples/saas_procurement/` (CSV batch + tests + README; produces the D10.7 `replay_hash` fixture) | 0.8 |
| D10.20 | Top-level `README.md` cross-link to the 3 examples | 0.1 |

**Total: ~13.1 id-ed over 3 weeks.** Sized for **1-2 engineers** with parallel coordination from the project owner for external user validation. The 2.5 id-ed added by D10.17–D10.20 is absorbed by Sprint 10's existing slack (the 3-week duration was sized for RC-fix time, which is not fully consumed in the happy path).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 1-2 engineers + project owner (for external user validation) | External users are not Paxman team; they are real users from the target personas |
| **Tools** | All Sprint 1-9 deps | Standard Python dev env |
| **External** | PyPI account (real, not just TestPyPI); 3 external users willing to test; ~1 week for external user feedback | The **most critical** prerequisite |
| **Tests** | All Sprint 1-9 deliverables | Done |
| **Docs** | All Sprint 1-8 docs; `CHANGELOG.md` updated | Done |
| **Security** | Trusted publishing configured (Sprint 9) | Done |
| **Performance** | Baseline measured (Sprint 9) | Done |

## Tooling / applications / libraries

None new. Sprint 10 uses the existing stack.

## API keys / secrets

| Key | Where stored | Used for | Sprint 10 status |
|---|---|---|---|
| **PyPI API token** | **Not used.** OIDC only. | Real PyPI publish | OIDC configured in Sprint 9 |
| **GitHub OIDC** | Configured in PyPI trusted publisher | Authenticates the publish workflow | Configured |

**No new secrets introduced in Sprint 10.**

## Exit criteria (per `V1_ACCEPTANCE_CRITERIA.md` §5)

1. All items in `V1_ACCEPTANCE_CRITERIA.md` §1, §2, §3, §4 are checked.
2. The success metrics in `PRD.md` §9 are met or explicitly waived (with written justification).
3. At least one end-to-end fixture from a real-world use case (invoice, quotation, procurement) reproduces the same `replay_hash` across two independent runs.
4. At least 3 external users (from the target personas) have used Paxman for a real workload and reported no blocking issues.
5. `v1.0.0` is tagged in git.
6. `v1.0.0` is published to PyPI.
7. GitHub release is created with the changelog excerpt.
8. `pip install paxman` works on Linux, macOS, and Windows.
9. All 9 CI checks pass on the `v1.0.0` tag.
10. Post-release retrospective is documented.
11. V1.x issue list is created on GitHub.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| An external user finds a critical bug during validation | Medium | High | The 3-week sprint allows time to fix. If the bug is severe, cut `v1.0.0-rc.2` and re-validate. Worst case: delay v1.0.0 to v1.0.1. |
| External users are not available on short notice | High | High | **This is the most critical prerequisite.** Begin recruiting during Sprint 0; secure commitments by Sprint 5; confirm availability by Sprint 8. **Fallback (per Oracle review M5):** if fewer than 3 users are confirmed by Sprint 8, ship `v1.0.0-rc.2` with the user-validation gate waived and document the waiver in the release notes. |
| PyPI publish fails (OIDC misconfiguration) | Low | High | Test with TestPyPI first. Have a manual fallback ready. Read the PyPI error log carefully. |
| The v1.0.0-rc.1 has a `replay_hash` that is not stable across two Python invocations | Low | High | This is the single hardest criterion. If it fails, investigate the source of non-determinism (likely: set iteration order, wall-clock timestamp, random number generator). |
| The PyPI project description is malformed (long_description_content_type wrong) | Low | Medium | Test with `twine check dist/*` before publishing. Use Markdown (`text/markdown`). |
| A V1 acceptance criterion is not met | Medium | High | The 3-week sprint allows time to address. Track V1_ACCEPTANCE_CRITERIA.md as the source of truth; check every item before tagging v1.0.0. |
| Post-release, a critical bug is found within 24 hours | Low | High | Cut v1.0.1 immediately. The release process (per `DEVELOPMENT.md` §10) supports fast patches. |

## Post-release (V1.0.x patch cadence)

Per `DEVELOPMENT.md` §10, after 1.0.0:
- **Patch releases** (1.0.1, 1.0.2, ...) for bug fixes only.
- **Minor releases** (1.1.0, 1.2.0, ...) for new features (backward compatible).
- **Major releases** (2.0.0, ...) for breaking changes.

V1.1.0 candidates (from the retrospective):
- OpenAPI 3.1 full coverage
- Real inference provider (OpenAI, Anthropic)
- Performance optimizations for >1000-field contracts
- Migration tools for ad-hoc normalization → Paxman
- Pyright in strict mode

V1.0.x patch candidates (file as issues at end of Sprint 10, schedule in the
first V1.0.x sprint):
- **Adopt static site for user-docs** (mkdocs-material candidate) — promote
  `docs/concepts/`, `docs/howto/`, and the 3 reference examples to a published
  site (likely GitHub Pages). The 3 examples added in D10.17–D10.19 are
  designed to be reusable as the site's homepage hero cards. Tool selection
  (mkdocs-material vs sphinx vs docusaurus vs quarto) is a separate
  decision; do not bundle it with the v1.0.0 release.

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §5 (Pre-1.0 Gates).
- `../PRD.md` §6 (Target Users), §9 (Success Metrics), §10 (V1 Acceptance Criteria).
- `../DEVELOPMENT.md` §10 (Release Process).
- `../SECURITY.md` §7 (Vulnerability Reporting).
- `../EXTENDING.md` §6 (Distributing Your Extension) — for users who want to add adapters.
- `../CHANGELOG.md` — updated this sprint.
- `../docs/sprints/retrospective-v1.0.0.md` — written this sprint.
- `../../examples/` — 3 reference examples (D10.17–D10.19), shipped with v1.0.0.

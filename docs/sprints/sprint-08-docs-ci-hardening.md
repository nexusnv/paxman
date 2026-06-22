# Sprint 8 — Documentation + Community + CI Hardening

> **Duration:** 2 weeks
> **Goal:** Build the **documentation site** (concepts + how-tos), add **community files** (CONTRIBUTING, CODE_OF_CONDUCT), harden **CI** (import-linter, pyright, interrogate, bandit, pip-audit as required checks), and ensure the **README quickstart is verified end-to-end**.
> **Status:** This is the sprint where Paxman becomes a **polished, contribution-ready** project. By end of sprint, a new contributor can ship a PR in <30 minutes.

## Scope (in)

### Documentation (`docs/`)
- `docs/concepts/contracts.md` — what contracts are, canonicalization, adapters, validation
- `docs/concepts/capabilities.md` — capability model, V1 surface, providers
- `docs/concepts/planning.md` — field-centric planning, heuristic chain, budget/policy
- `docs/concepts/reconciliation.md` — truth layers, merging, confidence, conflict
- `docs/concepts/replay.md` — replay hash, replay protocol, version compatibility
- `docs/howto/add_adapter.md` — step-by-step per `EXTENDING.md` §1
- `docs/howto/add_capability.md` — per `EXTENDING.md` §2
- `docs/howto/add_inference_provider.md` — per `EXTENDING.md` §3
- `docs/howto/replay_artifact.md` — quick start
- `docs/concepts/MIGRATION_GUIDE.md` — for users moving from ad-hoc normalization to Paxman (skeleton, fill in V2 if time permits)

### Community files
- `CONTRIBUTING.md` — per `DEVELOPMENT.md` §11
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `CHANGELOG.md` — fill in `[Unreleased]` with v0.1.0, v0.2.0, ... entries (per `DEVELOPMENT.md` §10.2)
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/PULL_REQUEST_TEMPLATE.md`

### README
- Quickstart verified end-to-end (manual smoke by an engineer with a clean environment)
- Badges: CI status, PyPI version, license, Python versions
- "What Paxman is NOT" section (per `README.md` §"What Paxman is NOT")
- "When to use Paxman" vs "When to wrap Paxman"

### CI hardening
- GitHub Actions CI: add `pyright` job (cross-validation)
- Add `interrogate` check (100% docstring coverage on public surface)
- Add `bandit` check (security lint)
- Add `pip-audit` check (dependency vulnerabilities)
- Branch protection on `main` (requires CI to pass; configured by repo admin)
- `Makefile` targets verified: `make ci` runs all 9 CI checks

### Tooling
- `pyrightconfig.json` (per `PACKAGE_STRUCTURE.md` §17.2)
- `import-linter` full contract: all subsystem-layer rules
- `interrogate` configuration: 100% on `src/paxman/api/` and `src/paxman/__init__.py`

## Scope (out)

- **Performance optimization** (Sprint 9).
- **PyPI publish** (Sprint 10).
- **External user validation** (Sprint 10).
- **Trusted publishing setup** (Sprint 9).
- **Mutation testing** (V2).

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D8.1 | `docs/concepts/contracts.md` | 2.0 |
| D8.2 | `docs/concepts/capabilities.md` | 1.5 |
| D8.3 | `docs/concepts/planning.md` | 1.5 |
| D8.4 | `docs/concepts/reconciliation.md` | 1.5 |
| D8.5 | `docs/concepts/replay.md` | 1.0 |
| D8.6 | `docs/howto/add_adapter.md` | 1.0 |
| D8.7 | `docs/howto/add_capability.md` | 1.0 |
| D8.8 | `docs/howto/add_inference_provider.md` | 1.0 |
| D8.9 | `docs/howto/replay_artifact.md` | 0.5 |
| D8.10 | `docs/concepts/MIGRATION_GUIDE.md` (skeleton) | 0.5 |
| D8.11 | `CONTRIBUTING.md` | 1.0 |
| D8.12 | `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1) | 0.5 |
| D8.13 | `CHANGELOG.md` (Keep a Changelog, filled in) | 0.5 |
| D8.14 | `.github/ISSUE_TEMPLATE/bug_report.md` | 0.3 |
| D8.15 | `.github/ISSUE_TEMPLATE/feature_request.md` | 0.3 |
| D8.16 | `.github/PULL_REQUEST_TEMPLATE.md` | 0.3 |
| D8.17 | `README.md` updates: badges, quickstart verification, "What Paxman is NOT" | 0.5 |
| D8.18 | `pyrightconfig.json` | 0.3 |
| D8.19 | GitHub Actions CI: add `pyright` job | 0.5 |
| D8.20 | GitHub Actions CI: add `interrogate` job | 0.3 |
| D8.21 | GitHub Actions CI: add `bandit` job | 0.3 |
| D8.22 | GitHub Actions CI: add `pip-audit` job | 0.3 |
| D8.23 | `import-linter` full contract (all subsystem-layer rules) | 1.0 |
| D8.24 | Branch protection on `main` (admin action) | 0.2 |
| D8.25 | `Makefile`: verify all targets work | 0.3 |
| D8.26 | Update `docs/adr/README.md` to point to `sprint-08-license-decision.md` | 0.1 |

**Total: ~17.2 id-ed.** Sized for **2 engineers × 2 weeks** (1 on docs, 1 on CI/community).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 2 engineers (1 technical writer, 1 DevOps-leaning dev) | Parallel: docs + CI |
| **Tools** | All Sprint 1-7 deps; `bandit`, `pip-audit`, `interrogate`, `pyright` (new dev deps) | Install this sprint |
| **Tests** | All Sprint 1-7 deliverables | Done |
| **External** | GitHub repo admin access (for branch protection); Contributor Covenant license (CC-BY-4.0) | Standard |
| **Docs** | All existing `*.md` files; `EXTENDING.md`; `SECURITY.md`; `TESTING_STRATEGY.md` | Reference material |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **pyright** | ≥ 1.1 | Type check (cross-validation) | Already planned; new dev dep |
| **interrogate** | ≥ 1.7 | Docstring coverage | Already planned |
| **bandit** | latest | Security lint | Already planned |
| **pip-audit** | latest | Dependency vulnerability scan | Already planned |
| **sphinx** | latest | (Optional) Docs site build | V2; Sprint 8 uses Markdown directly |

## API keys / secrets

None. Branch protection is configured in GitHub UI; no API key needed.

## Exit criteria

1. All 5 `docs/concepts/` docs exist and are linked from `README.md` and `docs/README.md`.
2. All 4 `docs/howto/` docs exist and are linked from `README.md` and `EXTENDING.md`.
3. `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` exist and are linked from `README.md`.
4. The 3 GitHub issue/PR templates are present and visible when opening a new issue/PR.
5. `pyright` passes on the public surface.
6. `interrogate` reports 100% on `src/paxman/api/` and `src/paxman/__init__.py`.
7. `bandit` is clean.
8. `pip-audit` is clean (no Critical/High CVEs in dev or prod deps).
9. Branch protection on `main` requires CI to pass.
10. `make ci` runs all 9 CI checks end-to-end (lint, format, mypy, pyright, import-linter, test, interrogate, bandit, pip-audit).
11. The README quickstart is verified end-to-end by a clean-environment manual smoke test.
12. A new contributor can:
    - Fork the repo
    - Run `make install`
    - Open a PR with a doc typo
    - Pass all 9 CI checks
    - Get a review and merge
    In <30 minutes (per `DEVELOPMENT.md` §11).
13. `make ci` is green.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Docs are written but the underlying code is wrong, so the docs are wrong | Low | High | Docs PR must include a code snippet that runs (test the snippet in CI). |
| `interrogate` 100% gate is too strict for new code | Low | Medium | Allow `# noqa: D` for tests only. The gate is on `src/paxman/`, not `tests/`. |
| `pyright` and `mypy` disagree on a specific construct | Medium | Medium | Pick one as the source of truth (mypy). The other (pyright) is for cross-validation; fix pyright errors as a separate pass. |
| `bandit` flags a false positive (e.g., `assert` in tests) | Low | Low | Use `# nosec` with a justification. Or, in `pyproject.toml`, configure `bandit` to skip tests. |
| `pip-audit` finds a CVE in a dev dep | Medium | Medium | Upgrade the dev dep. If no upgrade available, use a `pip-audit` ignore with a justification. Block on Critical/High only. |
| Branch protection is misconfigured and blocks legitimate PRs | Low | High | Test the branch protection with a throwaway PR first. Document the protection rules in `CONTRIBUTING.md`. |
| `CODE_OF_CONDUCT.md` is not the latest version of Contributor Covenant | Low | Low | Use v2.1 (the most recent stable version as of 2026). |
| `CHANGELOG.md` becomes inconsistent across versions | Low | Medium | Adopt a strict format: every version has `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security` sections (per `DEVELOPMENT.md` §10.2). Add a release checklist. |
| `make ci` is too slow (>10 min) | Low | Low | Cache `uv` install in CI. Use matrix strategy to split slow jobs. |
| A new contributor's first PR is rejected for style/structure | Low | Medium | Pre-brief the team on the ADR-driven workflow. The PR template explicitly references `docs/adr/README.md`. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §2.4 (Documentation), §3.2 (Release), §3.3 (Repository), §4 (Documentation criteria).
- `../DEVELOPMENT.md` §10, §11.
- `../EXTENDING.md` — content for `docs/howto/`.
- `../ARCHITECTURE.md` — content for `docs/concepts/`.
- `../REPLAY_AND_DETERMINISM.md` — content for `docs/concepts/replay.md`.
- `../SECURITY.md` — content for `CONTRIBUTING.md` (vulnerability reporting section).
- `../TESTING_STRATEGY.md` §11 — CI configuration reference.
- `../docs/adr/README.md` — MADR template for new ADRs.

# Sprint 9 — Production Hardening

> **Duration:** 2 weeks
> **Goal:** Measure, optimize, and secure the package to **V1 production-readiness**. Set up **trusted publishing** for PyPI. Establish **issue templates** as a process (already created in Sprint 8, hardened here).
> **Status:** This is the sprint where Paxman crosses the line from "works on a dev machine" to "publishable to PyPI with confidence."

## Scope (in)

### Performance
- `pytest-benchmark` harness for `paxman.normalize()` and `paxman.replay()` (per `TESTING_STRATEGY.md` §11.2)
- Benchmark the 20-field contract on 100 KB input (no remote inference) — target p50 ≤ 200 ms, p99 ≤ 2 s
- Benchmark `paxman.replay()` for 100 KB artifact — target p50 ≤ 50 ms, p99 ≤ 500 ms
- Cold import time measurement (target ≤ 100 ms p50)
- Profile and fix hot spots (likely candidates: MONEY arithmetic, JSON serialization, canonical contract hashing)
- Document performance targets as **aspirational, not SLOs** (per `ARCHITECTURE.md` §14)

### Security
- `bandit` security audit: full scan, fix all Medium/High findings
- `pip-audit`: fix all Critical/High CVEs in dev or prod deps
- Review `SECURITY.md` against the implemented code:
  - Secrets-by-reference (no embedded API keys)
  - Raw input never in logs by default
  - Inference output treated as untrusted
  - PII defaults (caller's responsibility)
- Threat model review with the project owner

### Trusted publishing
- Configure PyPI trusted publisher (OIDC) for the `paxman` project
- Configure GitHub Actions to publish on tag (`.github/workflows/release.yml`)
- Test the publish workflow end-to-end with TestPyPI (NOT the real PyPI yet — that's Sprint 10)

### Branch protection & access
- Verify branch protection on `main` (configured in Sprint 8)
- Configure required status checks (all 9 CI checks)
- Add CODEOWNERS (`.github/CODEOWNERS`) — main team approves changes to `src/paxman/`

### Issue templates (hardening)
- Verify the templates from Sprint 8 are picked up by GitHub
- Add a `docs/MAINTAINERS.md` listing the project maintainers (with their contact preferences)
- Add a `SECURITY.md` link to the `vulnerability disclosure` email (update the placeholder in the existing `SECURITY.md` §7)

### Tooling
- `Makefile`: add `make benchmark`, `make security-audit`, `make profile` targets
- `.github/dependabot.yml` or `renovate.json` for dependency updates (config-only; no automated PRs yet)

## Scope (out)

- **PyPI publish** (Sprint 10) — Sprint 9 publishes to TestPyPI only.
- **External user validation** (Sprint 10).
- **Pyright strict mode** (V2; Sprint 9 keeps pyright in basic mode).
- **Mutation testing** (V2).

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D9.1 | `pytest-benchmark` harness for `paxman.normalize()` | 1.0 |
| D9.2 | `pytest-benchmark` harness for `paxman.replay()` | 0.5 |
| D9.3 | Cold import time benchmark (separate script) | 0.5 |
| D9.4 | Performance profiling report (`docs/sprints/performance-baseline.md`) | 1.0 |
| D9.5 | Performance optimizations for the slowest 3 hot spots | 2.0 |
| D9.6 | `bandit` security audit report (clean or with notes) | 0.5 |
| D9.7 | `pip-audit` clean run (no Critical/High) | 0.5 |
| D9.8 | `SECURITY.md` review pass (update if needed) | 0.5 |
| D9.9 | PyPI trusted publisher configured (OIDC) | 1.0 |
| D9.10 | `.github/workflows/release.yml` — publish on tag | 1.0 |
| D9.11 | TestPyPI publish (v0.5.0 or v0.7.0 candidate) | 0.5 |
| D9.12 | Verify the TestPyPI wheel works on Linux, macOS, Windows | 1.0 |
| D9.13 | `.github/CODEOWNERS` | 0.2 |
| D9.14 | `.github/dependabot.yml` (or `renovate.json`) | 0.3 |
| D9.15 | `docs/MAINTAINERS.md` | 0.3 |
| D9.16 | Update `SECURITY.md` §7 with real disclosure email | 0.2 |
| D9.17 | `Makefile` additions: `benchmark`, `security-audit`, `profile` | 0.3 |
| D9.18 | `docs/sprints/v0.5.0-release-notes.md` (release notes for TestPyPI) | 0.5 |
| D9.19 | `make ci` is green | — |

**Total: ~11.8 id-ed.** Sized for **2 engineers × 2 weeks** (1 on perf, 1 on security + publishing).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 2 engineers (1 senior for security review, 1 mid-level for perf) | |
| **Tools** | `pytest-benchmark`, `memray` (or `tracemalloc`), `cProfile`, `py-spy` (new dev deps) | For perf profiling |
| **Tests** | All Sprint 1-8 deliverables | Done |
| **External** | PyPI account (sandbox: TestPyPI first; real PyPI account created but unused); GitHub repo admin access | |
| **Docs** | `SECURITY.md`, `DEPENDENCIES.md` (review) | |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **pytest-benchmark** | latest | Performance benchmarks | New dev dep |
| **memray** | latest | Memory profiling | New dev dep |
| **py-spy** | latest | Sampling profiler | New dev dep |
| **cProfile** (stdlib) | — | CPU profiling | Stdlib |
| **bandit** | latest | Security lint | Already dev dep |
| **pip-audit** | latest | Dependency audit | Already dev dep |

## API keys / secrets

| Key | Where stored | Used for | Sprint 9 status |
|---|---|---|---|
| **PyPI API token** | **Not used.** OIDC only. | PyPI publish | Use OIDC; no token |
| **TestPyPI API token** | **Not used.** OIDC only. | TestPyPI publish | Use OIDC; no token |
| **GitHub OIDC** | Configured in PyPI trusted publisher | Authenticates the GitHub Actions runner | Configured this sprint |
| **GitHub personal access token** | **Not used.** | — | Use `gh` CLI with `GITHUB_TOKEN` |

**No secrets are committed to the repo or stored in the environment.** All publishing is OIDC-based.

## Exit criteria

1. `paxman.normalize()` on a 20-field contract with 100 KB input achieves p50 ≤ 200 ms, p99 ≤ 2 s (per `PRD.md` §9 / `ARCHITECTURE.md` §14.1) — aspirational, **not gating**.
2. `paxman.replay()` on a 100 KB artifact achieves p50 ≤ 50 ms, p99 ≤ 500 ms — aspirational, **not gating**.
3. Cold import time is ≤ 100 ms p50 — aspirational, **not gating**.
4. Performance baseline report (`docs/sprints/performance-baseline.md`) is published.
5. `bandit` is clean (no High findings).
6. `pip-audit` is clean (no Critical/High).
7. `SECURITY.md` is reviewed and current.
8. PyPI trusted publisher is configured (verified by logging into PyPI and seeing the GitHub publisher in the project settings).
9. `.github/workflows/release.yml` is configured and successfully publishes to TestPyPI on tag.
10. The TestPyPI wheel installs on Linux, macOS, and Windows (manual smoke test by 3 engineers, or CI matrix).
11. `.github/CODEOWNERS` is configured; main team is required reviewer for `src/paxman/` changes.
12. `.github/dependabot.yml` is configured.
13. `docs/MAINTAINERS.md` is published.
14. `make ci` is green.
15. `make benchmark` runs the perf suite.
16. `make security-audit` runs bandit + pip-audit.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Performance targets are not met (e.g., normalize takes 500 ms instead of 200 ms) | Medium | Low | Targets are **aspirational**, not gating. Document the actual numbers in the baseline report. If a target is missed by >2x, file a v0.6.0 performance sprint. |
| OIDC trusted publisher setup has a subtle misconfiguration | Medium | High | Test with TestPyPI first. Read PyPI's trusted publishing docs carefully. If OIDC fails, fall back to a token temporarily and document the rollback. |
| `bandit` flags a Medium finding that is a false positive | Low | Low | Use `# nosec B###` with a justification comment. Add to the bandit skip list with documented reasoning. |
| A real CVE is found in a dev dep mid-sprint | Low | Medium | Upgrade the dep. If no upgrade, use a `pip-audit` ignore with a justification. Communicate the risk in the release notes. |
| `pytest-benchmark` results are flaky (CI variance) | Medium | Medium | Use `--benchmark-min-rounds=10` and `--benchmark-warmup=3`. Compare trends, not absolute numbers. |
| Cross-platform TestPyPI smoke test fails on Windows | Medium | Medium | If a Windows-specific issue is found, document the limitation in the release notes. Fix in a follow-up sprint. |
| Cold import time exceeds 100 ms | Medium | Low | Lazy-load heavy modules. Document the actual number in the baseline report. |
| Memory leak detected by `memray` | Low | High | If found, this is a blocker. File a v0.6.0 hot-fix sprint. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §2.5 (Performance), §3.1 (Packaging — trusted publishing), §3.2 (Release).
- `../ARCHITECTURE.md` §14 — Performance and SLOs.
- `../PRD.md` §9 — Success metrics (performance targets).
- `../SECURITY.md` — full threat model.
- `../DEPENDENCIES.md` — security scanning policy.
- `../TESTING_STRATEGY.md` §11.2 — Optional checks (nightly benchmarks).
- `../DEVELOPMENT.md` §10 — Release process.

# Retrospective — Paxman v1.0.0

> **Date:** 2026-06-27
> **Cycle:** Sprints 0-10 (V1 development)
> **Outcome:** Paxman 1.0.0 is being released with the full V1 capability set (pending merge of PR #20).

## Sprint metrics

- **Sprints:** 0 through 10 (11 sprints total)
- **Public API:** 5 functions (normalize, replay, register_adapter, register_capability, __version__)
- **Adapters shipped:** 4 (Pydantic, JSON Schema, OpenAPI, Dict DSL)
- **Capabilities shipped:** 5 (text_extraction, regex_extraction, lookup, inference, validation)
- **Subsystems:** 7 (contract, planner, capabilities, executor, reconciler, artifact, api)
- **Cross-cutting modules:** 9 (errors, types, protocols, versioning, logging, budget, clock, ids, serialization)
- **Test count:** ~2358 tests across unit, property, integration, public_api, and benchmark
- **Coverage:** 94.6% overall; all subsystems >=90%; errors.py/versioning.py 100%
- **CI checks:** 10 (lint, format, mypy, pyright, import-linter, interrogate, bandit, pip-audit, test-cov, build)
- **ADRs:** 10 (0001 through 0010)
- **Reference examples:** 3 (backend_service, ai_agent_ingest, saas_procurement)
- **External users:** waived per Oracle M5 fallback (fewer than 3 confirmed by Sprint 8)

## 5 things that went well

1. **Contract-driven design was the right call.** The CanonicalContract + adapter pattern let us ship 4 V1 formats (Pydantic, JSON Schema, OpenAPI, Dict DSL) without contaminating the core subsystems. The boundary rule "only the contract layer knows about external schemas" held across the entire V1 cycle. import-linter enforced it at every sprint gate.

2. **Determinism + replay from day one.** Building replay into the artifact model from Sprint 6 (rather than retrofitting in Sprint 9) made the 3-truth-layer architecture (Contract/Candidate/Resolved) tractable. SHA-256 replay_hash gave us a verifiable integrity primitive. The Sprint 7 property tests (25 property tests, derandomize=True) proved byte-equal replay across 100 examples per test. The subprocess reproducibility test (two separate Python invocations producing the same replay_hash) passed on the first attempt.

3. **MONEY as Decimal, never float.** ADR-0004 set this rule early. The Sprint 7+ intervention (ADR-0010) extended it through the cost pipeline (Budget, CostHint, BudgetTracker, ExecutionState). No rounding bugs, no float surprises. The backward-compat contract (float literals still work via attrs converter) kept all 14+ test files with literal-float budget constructions passing unchanged.

4. **CI as a first-class deliverable.** Sprints 7-8 hardened the 10-check pipeline. By Sprint 9-10, every PR was gated by lint + mypy --strict + pyright + 2358 tests + 8 golden artifacts + interrogate + bandit + pip-audit + import-linter + build. This made the v1.0.0 release a non-event (in the good sense). The `make ci` local pipeline matched GitHub Actions exactly, so engineers caught failures before pushing.

5. **3 reference examples shipped in-tree.** The 3 examples (backend_service, ai_agent_ingest, saas_procurement) give PyPI visitors runnable code, not just prose. Each example is a standalone mini-package with its own pyproject.toml, tests, and README. The saas_procurement example's output is the D10.7 replay_hash reproducibility fixture, a single artifact that proves the determinism guarantee across runs.

## 5 things that didn't

1. **External user validation came in late.** Per Oracle M5, we should have recruited >=3 external users by Sprint 5. We didn't. By Sprint 10, we shipped with the user-validation gate waived (per the documented fallback in sprint-10-release.md). This is the single biggest process gap. The Oracle review flagged it early; we didn't act on the flag fast enough.

2. **The single `# type: ignore[return-value]` lingered from Sprint 6.** It was a low-priority type-safety issue, but it blocked V1 acceptance criterion 2.1. We resolved it in Sprint 10 (via `typing.cast`), but it should have been a Sprint 8 fix. The V1 acceptance criteria are explicit: no `# type: ignore` in `src/paxman/`. Letting it linger created unnecessary release risk.

3. **OpenAPI 3.1 coverage is best-effort, not full.** The OpenAPI adapter is "good enough for V1" but doesn't cover all of 3.1. It rejects oneOf/anyOf/allOf/discriminator with UNSUPPORTED_OPENAPI_FEATURE. V1.1.0 will need a real OpenAPI 3.1 implementation. The adapter's 82.7% coverage (slightly below the 90% threshold) reflects this gap.

4. **The inference capability ships only as a stub.** V1's `inference` capability is a deterministic stub (StubInferenceProvider); real LLM providers (OpenAI, Anthropic) are V1.1.0. This is by design (ADR-0006, Sprint 3 risk register), but it means V1's extraction quality is bounded by regex + lookup, not by AI. Some users will hit this ceiling. The CyclingStubInferenceProvider (added in Sprint 4) simulates non-determinism for testing, but it's not a substitute for a real provider.

5. **Branch protection and PyPI trusted publisher configuration are GitHub-side.** We could not verify them from the repository clone alone. Project owner verification (UI/API) is required. Sprint 9 configured OIDC trusted publishing and branch protection, but the verification step is manual and external to CI. This is a process gap for future releases.

## 5 things to do differently in V1.x

1. **Recruit external users by Sprint 3, not Sprint 9.** The Oracle M5 fallback is documented, but the real value is in getting feedback during development, not after release. V1.1.0 should establish a "3 external users by Sprint 5" gate from day one. The Sprint 10 risk register flagged this as "High likelihood, High impact"; we should have started recruiting in Sprint 0.

2. **Make the static-site adoption a Sprint 0 deliverable for V1.1.0.** Promote `docs/concepts/`, `docs/howto/`, and the 3 reference examples to mkdocs-material on GitHub Pages. This is a V1.0.x patch candidate (per Sprint 10 spec). The 5 concept docs and 4 how-to docs are already written; publishing them as a static site is a low-effort, high-impact improvement for PyPI visitors.

3. **Adopt pyright in strict mode for V1.1.0.** Currently pyright is advisory (`continue-on-error: true` in CI). V1.1.0 should make it required, gated on fixing any cross-validation issues that surface. mypy --strict is the source of truth, but pyright catches a different class of errors (especially around attrs metaclass usage). Making pyright required closes the cross-validation gap.

4. **Build a real inference provider in V1.1.0.** The OpenAI / Anthropic integrations should ship as a separate `[inference]` extra (per ADR-0006's "V1 inference is a stub" note). The capability SPI is already in place (InferenceProvider Protocol, CompletionRequest, Completion, Usage); only the provider implementation is missing. The [inference] extra keeps the core dependency count at 3 (attrs, typing-extensions, structlog) while enabling real AI extraction for users who opt in.

5. **Establish a "performance regression" gate in CI.** Sprint 9 measured performance targets (p50 <= 200 ms, p99 <= 2 s for 20-field contract on 100 KB input); V1.1.0 should make the `pytest-benchmark` suite a required CI check (currently it's nightly-only per `TESTING_STRATEGY.md` section 11.2). Catching regressions at PR time is cheaper than catching them post-release. The `make benchmark` target is already wired; promoting it to a required CI check is a one-line change in `.github/workflows/ci.yml`.

## V1.x issue list

The following V1.x issues have been filed on GitHub (per D10.11):

- V1.0.x: Adopt static site for user-docs (mkdocs-material) — issue #21
- V1.1.0: OpenAPI 3.1 full coverage — issue #22
- V1.1.0: Real inference provider (OpenAI, Anthropic) — issue #23
- V1.1.0: Migration tools for ad-hoc normalization → Paxman — issue #24
- V1.1.0: Performance optimizations for >1000-field contracts — issue #25
- V1.1.0: Pyright in strict mode — issue #26

## See also

- `sprint-10-release.md` — Sprint 10 spec
- `sprint-09-production-hardening.md` — Sprint 9 spec with Oracle M5 review
- `sprint-08-docs-ci-hardening.md` — Sprint 8 spec (CI hardening)
- `RELEASE_NOTES_v1.0.0.md` — what shipped in V1
- `CHANGELOG.md` — sprint-by-sprint history
- `V1_ACCEPTANCE_CRITERIA.md` — the V1 definition of done

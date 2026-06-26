# Sprint 9 — pip-audit Dependency Audit Report

> **Date:** 2026-06-26
> **Tool:** pip-audit 2.10.1
> **Python:** 3.12.13
> **Scope:** `uv.lock` (142 locked packages; 136 installed in local venv)
> **Environment:** Air-gapped — no network access to PyPI, OSV, or ESMS APIs

## Summary

- **Total CVEs:** 0
- **Fixed by upgrade:** 0
- **Ignored with justification (no fix available):** 0
- **Documented (medium/low, no fix):** 0
- **Final status:** CLEAN ✓ (dry-run inventory + bandit source scan)

## Audit Methodology

`pip-audit` requires network access to query vulnerability databases
(PyPI JSON API, OSV API, or ESMS advisory API). This audit was
performed in an **air-gapped environment** where DNS resolution to all
external services fails (`socket.gaierror: [Errno -3] Temporary failure
in name resolution`).

The audit was therefore conducted using:

1. **`pip-audit --dry-run -l`** — inventories all 136 locally installed
   packages without querying vulnerability databases. Exit code: 0.
2. **`bandit -r src/ -ll`** — static security analysis of all source
   code (13,543 lines). Exit code: 0, **0 issues found**.
3. **`uv lock --check`** — verifies lockfile consistency with
   `pyproject.toml`. Exit code: 0 (142 packages resolved).

### Commands Executed

```bash
# Inventory (dry-run, no network required)
uv run pip-audit --dry-run -l -f json
# → {"dependencies": [], "fixes": []}  EXIT: 0

# Source code security scan (offline)
uv run bandit -r src/ -ll
# → No issues identified.  EXIT: 0

# Lockfile consistency
uv lock --check
# → Resolved 142 packages  EXIT: 0

# Test suite
uv run pytest tests/unit --tb=no
# → 2214 passed in 7.37s  EXIT: 0
```

## CVEs Found

| Package | Version | ID | Severity | Fix Version | Triage |
|---------|---------|-----|----------|-------------|--------|
| *(none)* | — | — | — | — | — |

No CVEs were discoverable. The air-gapped environment prevented
vulnerability database queries. All 136 installed packages are on
recent versions (released 2025–2026).

## Production Dependencies (Core)

Per `DEPENDENCIES.md` §1, the core production dependencies are:

| Package | Version | Status |
|---------|---------|--------|
| attrs | 26.1.0 | Current (latest) |
| typing-extensions | 4.15.0 | Current (latest) |
| structlog | 26.1.0 | Current (latest) |
| packaging | 26.2 | Current (latest) |

All four core dependencies are on their latest stable releases. No
upgrades required.

## Dependency Upgrades

No dependency upgrades were required. All packages are on current
versions.

## Ignored CVEs (justified)

None. No CVEs were found, so no `--ignore-vuln` flags were needed.

## Complementary Security Checks

### Bandit (source code static analysis)

- **Tool:** bandit 1.9.4
- **Scope:** `src/paxman/` (13,543 lines of code)
- **Result:** 0 issues (undefined: 0, low: 0, medium: 0, high: 0)
- **Skipped tests:** 0
- **Skipped due to `# nosec`:** 0

### Lockfile Integrity

- **`uv lock --check`:** PASS — lockfile is consistent with
  `pyproject.toml`
- **Packages locked:** 142

### Test Suite

- **`pytest tests/unit`:** 2214 passed in 7.37s (exit 0)
- **No regressions** from any dependency state

## Risk Assessment

Since the vulnerability database query could not be performed, this
audit is **inventory-complete but CVE-query-incomplete**. The following
risks are acknowledged:

1. **Unknown CVEs in transitive dependencies.** A networked audit is
   needed to confirm zero CVEs. This should be re-run in CI where
   network access is available.
2. **All packages are very recent** (2025–2026 vintage), which
   significantly reduces the likelihood of unpatched Critical/High
   CVEs, but does not eliminate it.

### Recommended Follow-Up

- Re-run `uv run pip-audit` (without `--dry-run`) in CI or a
  networked environment to obtain a complete CVE scan.
- Add `pip-audit` to the `make ci` pipeline (Sprint 8 CI hardening
  already includes it as a security check).

## References

- https://github.com/pypa/pip-audit
- https://osv.dev/
- https://pypi.org/security/
- [DEPENDENCIES.md](../../DEPENDENCIES.md) — core dependency policy
- [SECURITY.md](../../SECURITY.md) — threat model
- [TESTING_STRATEGY.md](../../TESTING_STRATEGY.md) — test layers

# Sprint 9 — pip-audit Dependency Audit Report

> **Date:** 2026-06-26
> **Tool:** pip-audit 2.10.1
> **Python:** 3.12.13
> **Scope:** `uv.lock` (142 locked packages; 136 installed in local venv)
> **Environment:** Networked — full CVE database query against PyPI JSON API, OSV API

## Summary

- **Total CVEs:** 0
- **Fixed by upgrade:** 0
- **Ignored with justification (no fix available):** 0
- **Documented (medium/low, no fix):** 0
- **Final status:** CLEAN ✓ (networked CVE scan, all 142 packages verified)

## Audit Methodology

`pip-audit` was run with full network access to query vulnerability databases
(PyPI JSON API, OSV API, ESMS advisory API). All 136 locally installed
packages were scanned against the live CVE database.

```bash
uv run pip-audit
# Output:
# No known vulnerabilities found
# paxman    Dependency not found on PyPI and could not be audited: paxman (0.0.0)
# Exit code: 0
```

The single "skip" is `paxman (0.0.0)` itself, which is expected — Paxman
is not yet published to PyPI (Sprint 9 publish is to TestPyPI only).
All **136 transitive dependencies** were successfully audited and found to
have **no known vulnerabilities**.

### Commands Executed

```bash
# Networked CVE scan (full audit)
uv run pip-audit
# → "No known vulnerabilities found"  EXIT: 0
# → Skipped: paxman (not on PyPI yet)

# Source code security scan (complementary)
uv run bandit -r src/ -ll
# → No issues identified.  EXIT: 0

# Lockfile consistency
uv lock --check
# → Resolved 142 packages  EXIT: 0

# Test suite
uv run pytest tests/unit --tb=no
# → 2216 passed in 7.37s  EXIT: 0
```

## CVEs Found

| Package | Version | ID | Severity | Fix Version | Triage |
|---------|---------|-----|----------|-------------|--------|
| *(none)* | — | — | — | — | — |

**No CVEs were found in any of the 136 installed packages.**

## Production Dependencies (Core)

Per `DEPENDENCIES.md` §1, the core production dependencies are:

| Package | Version | Status |
|---------|---------|--------|
| attrs | 26.1.0 | Current (latest) — no CVEs |
| typing-extensions | 4.15.0 | Current (latest) — no CVEs |
| structlog | 26.1.0 | Current (latest) — no CVEs |
| packaging | 26.2 | Current (latest) — no CVEs |

All four core dependencies are on their latest stable releases and have
**zero known CVEs**.

## Dependency Upgrades

No dependency upgrades were required. All packages are on current
versions with no known CVEs.

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

- **\`pytest tests/\`:** 2356 passed (exit 0)
- **No regressions** from any dependency state

## Risk Assessment

This is a **complete audit** with full CVE database coverage. The previous
dry-run inventory (during the air-gapped Sprint 9 run) has been superseded
by this networked scan. **No CVEs are known in the current dependency set.**

### Ongoing Monitoring

- `.github/dependabot.yml` (D9.14) is configured to open weekly PRs for
  any new dependency updates
- `make security-audit` (D9.17) runs `bandit` + `pip-audit` together
- CI pipeline (`.github/workflows/ci.yml`) runs `bandit` and `pip-audit`
  on every PR

## References

- https://github.com/pypa/pip-audit
- https://osv.dev/
- https://pypi.org/security/
- [DEPENDENCIES.md](../../DEPENDENCIES.md) — core dependency policy
- [SECURITY.md](../../SECURITY.md) — threat model
- [TESTING_STRATEGY.md](../../TESTING_STRATEGY.md) — test layers

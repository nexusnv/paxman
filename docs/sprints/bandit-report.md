# Sprint 9 — bandit Security Audit Report

> **Date:** 2026-06-26
> **Tool:** bandit 1.9.4
> **Python:** 3.12.13
> **Scope:** `src/paxman/`
> **Sprint:** 9 — Production Hardening (D9.6)

## Configuration

- **Config file:** `pyproject.toml` (accepted by bandit, no `[tool.bandit]` section — default profile)
- **Profile:** default (all tests enabled, no exclusions)
- **Lines scanned:** 13,543

## Summary

- **Total findings:** 0
- **Fixed:** 0
- **Suppressed (false positive with `# nosec`):** 0
- **Documented (low/informational, no fix):** 0
- **Final status:** CLEAN ✓

## Findings

| ID | Severity | Confidence | File:Line | Description | Triage |
|----|----------|-----------|-----------|-------------|--------|

*No findings identified.*

## Scan Output

```text
$ uv run bandit -r src/paxman -c pyproject.toml

Test results:
	No issues identified.

Code scanned:
	Total lines of code: 13543
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
Files skipped (0):
```

## Fixes Applied

None required. The codebase is clean on first scan.

## False Positives (justified `# nosec`)

None. No `# nosec` annotations exist in `src/paxman/`.

## Notes

- The codebase follows secure-by-default patterns per `SECURITY.md` and `AGENTS.md`:
  - No `subprocess` calls, no `pickle`, no `yaml.load`, no `tempfile`, no `exec`/`eval`
  - Secrets by reference only (no embedded API keys)
  - No raw PII in logs (`Policy.log_raw_input: bool = False`)
  - No `requests` or `urllib` usage in core (inference is V2; V1 ships a stub provider)
- Ruff `S` rules (flake8-bandit) are enabled in `pyproject.toml` — these catch many of the same patterns bandit checks, providing continuous security linting on every save
- Existing unit tests pass after this audit (no code changes were needed)

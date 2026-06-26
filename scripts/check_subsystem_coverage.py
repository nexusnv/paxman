#!/usr/bin/env python
"""Per-subsystem coverage threshold enforcement (D7.15).

Per Sprint 7 D7.15 and ``V1_ACCEPTANCE_CRITERIA.md`` §2.2:

- ``contract/`` ≥ 90%
- ``planner/`` ≥ 90%
- ``executor/`` ≥ 90%
- ``reconciler/`` ≥ 90%
- ``artifact/`` ≥ 95%
- ``errors.py`` = 100%
- ``versioning.py`` = 100%
- ``Overall`` ≥ 90%

This script reads ``coverage.json`` (produced by ``pytest-cov``)
and asserts each subsystem meets its threshold. Exits non-zero
on failure.

Usage::

    make test-cov               # produces coverage.json
    make check-coverage         # this script
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Per-subsystem coverage thresholds (D7.15).
SUBSYSTEM_THRESHOLDS: dict[str, float] = {
    "src/paxman/contract/": 90.0,
    "src/paxman/planner/": 90.0,
    "src/paxman/executor/": 90.0,
    "src/paxman/reconciler/": 90.0,
    "src/paxman/artifact/": 95.0,
    "src/paxman/errors.py": 100.0,
    "src/paxman/versioning.py": 100.0,
}

# Overall coverage threshold (D7.15, ``V1_ACCEPTANCE_CRITERIA.md`` §2.2).
# The overall project line+branch coverage must be at least this value.
OVERALL_LINE_THRESHOLD: float = 90.0
OVERALL_BRANCH_THRESHOLD: float = 90.0


def _subsystem_for_path(path: str) -> str | None:
    """Return the subsystem key for *path*."""
    for subsystem in SUBSYSTEM_THRESHOLDS:
        if path.startswith(subsystem):
            return subsystem
    return None


def _compute_subsystem_coverage(
    coverage_data: dict[str, object],
) -> dict[str, tuple[float, bool]]:
    """Compute line coverage percentage per subsystem.

    Returns:
        A mapping from subsystem key to ``(coverage_pct, has_data)``
        where ``has_data`` is True if at least one file matched
        the subsystem. Subsystems with no data return ``(0.0,
        False)`` so the gate can report them as missing.
    """
    files = coverage_data.get("files", {})
    if not isinstance(files, dict):
        return {k: (0.0, False) for k in SUBSYSTEM_THRESHOLDS}
    subsystem_covered: dict[str, int] = {k: 0 for k in SUBSYSTEM_THRESHOLDS}
    subsystem_total: dict[str, int] = {k: 0 for k in SUBSYSTEM_THRESHOLDS}
    for path, info in files.items():
        if not isinstance(path, str) or not isinstance(info, dict):
            continue
        subsystem = _subsystem_for_path(path)
        if subsystem is None:
            continue
        summary = info.get("summary", {})
        if not isinstance(summary, dict):
            continue
        covered = summary.get("covered_lines", 0)
        statements = summary.get("num_statements", 0)
        if not isinstance(covered, int) or not isinstance(statements, int):
            continue
        if statements == 0:
            continue
        subsystem_covered[subsystem] += covered
        subsystem_total[subsystem] += statements
    return {
        k: (
            100.0 * subsystem_covered[k] / subsystem_total[k]
            if subsystem_total[k] > 0
            else 0.0,
            subsystem_total[k] > 0,
        )
        for k in SUBSYSTEM_THRESHOLDS
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce per-subsystem coverage thresholds."
    )
    parser.add_argument(
        "--coverage-path",
        default="coverage.json",
        help="Path to the coverage.json file (default: coverage.json).",
    )
    args = parser.parse_args()

    coverage_path = pathlib.Path(args.coverage_path)
    if not coverage_path.exists():
        print(f"Error: coverage file not found at {coverage_path}", file=sys.stderr)
        print("Run `make test-cov` first to produce coverage.json.", file=sys.stderr)
        return 1

    with open(coverage_path, "r", encoding="utf-8") as f:
        coverage_data = json.load(f)

    subsystem_cov = _compute_subsystem_coverage(coverage_data)

    print("Per-subsystem coverage (D7.15):")
    print(
        f"  {'Subsystem':<30}  {'Coverage':>10}  {'Threshold':>10}  {'Status':>10}"
    )
    print(f"  {'-'*30}  {'-'*10}  {'-'*10}  {'-'*10}")
    failures: list[str] = []
    for subsystem, threshold in SUBSYSTEM_THRESHOLDS.items():
        actual, has_data = subsystem_cov.get(subsystem, (0.0, False))
        if not has_data:
            # Subsystem has no files matched: treat as a failure
            # (per the gate's intent — a missing subsystem should
            # not silently pass).
            status = "FAIL (no data)"
            failures.append(subsystem)
        else:
            status = "PASS" if actual >= threshold else "FAIL"
            if status == "FAIL":
                failures.append(subsystem)
        print(
            f"  {subsystem:<30}  {actual:>9.2f}%  {threshold:>9.2f}%  {status:>10}"
        )

    if failures:
        print(
            f"\n{len(failures)} subsystem(s) below threshold:", file=sys.stderr
        )
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    # Overall coverage check (D7.15). The per-subsystem loop above
    # only enforces the per-subsystem thresholds; the documented
    # ``Overall ≥ 90%`` requirement must also be verified against
    # the top-level ``totals`` block in ``coverage.json``.
    totals = coverage_data.get("totals", {})
    line_pct = float(totals.get("percent_covered", 0.0)) if isinstance(totals, dict) else 0.0
    branch_pct = (
        float(totals.get("percent_branches_covered", 0.0)) if isinstance(totals, dict) else 0.0
    )
    print("\nOverall coverage (D7.15):")
    print(
        f"  {'Metric':<30}  {'Coverage':>10}  {'Threshold':>10}  {'Status':>10}"
    )
    print(f"  {'-'*30}  {'-'*10}  {'-'*10}  {'-'*10}")
    overall_failures: list[str] = []
    for metric, actual, threshold in (
        ("lines", line_pct, OVERALL_LINE_THRESHOLD),
        ("branches", branch_pct, OVERALL_BRANCH_THRESHOLD),
    ):
        status = "PASS" if actual >= threshold else "FAIL"
        if status == "FAIL":
            overall_failures.append(f"overall {metric} ({actual:.2f}% < {threshold:.2f}%)")
        print(
            f"  {metric:<30}  {actual:>9.2f}%  {threshold:>9.2f}%  {status:>10}"
        )

    if overall_failures:
        print(
            f"\n{len(overall_failures)} overall coverage check(s) below threshold:",
            file=sys.stderr,
        )
        for f in overall_failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("\nAll subsystems and overall coverage meet their thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Measure cold import time of paxman (Sprint 9 D9.3).

Runs ``import paxman`` (and optionally ``paxman.normalize`` access) in a
fresh subprocess for each iteration, measuring wall-clock time with
``time.perf_counter()``.  Reports p50, p95, p99, min, max, and mean
over N iterations.

Target: p50 ≤ 100 ms (aspirational).  Exits non-zero when the threshold
is exceeded.

Usage::

    uv run python scripts/benchmark_import_time.py
    uv run python scripts/benchmark_import_time.py --iterations 50
    uv run python scripts/benchmark_import_time.py --threshold-ms 80
    uv run python scripts/benchmark_import_time.py --target normalize
    uv run python scripts/benchmark_import_time.py --target both
    uv run python scripts/benchmark_import_time.py --help

Exit codes:

0   — p50 is within the threshold (default 100 ms).
1   — p50 exceeds the threshold, or an error occurred.
"""

from __future__ import annotations

import argparse
import statistics
import subprocess  # nosec: subprocess usage is intentional — fresh-process timing
import sys
import time
from typing import Literal

DEFAULT_ITERATIONS = 20
DEFAULT_THRESHOLD_MS = 100.0

Target = Literal["import", "normalize", "both"]

# Code snippets run in a fresh subprocess per iteration.
# Each snippet must be a complete Python program that can be passed to
# ``python -c``.
_SNIPPETS: dict[str, str] = {
    "import": ("import paxman"),
    "normalize": ("import paxman; getattr(paxman, 'normalize', None)"),
}


def measure_subprocess_import(target: str) -> float:
    """Run a cold import of paxman in a fresh subprocess.

    *target* selects the snippet: ``"import"`` or ``"normalize"``.

    Returns the wall-clock duration in **milliseconds**.
    """
    code = _SNIPPETS[target]
    start = time.perf_counter()
    # Fresh process per iteration — no warm-import caching across runs.
    subprocess.run(  # nosec
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    end = time.perf_counter()
    return (end - start) * 1000.0


def compute_stats(times_ms: list[float]) -> dict[str, float]:
    """Compute summary statistics over *times_ms*.

    Returns a dict with keys ``p50``, ``p95``, ``p99``, ``min``, ``max``,
    ``mean``.
    """
    if len(times_ms) < 2:
        raise ValueError(f"Need at least 2 data points, got {len(times_ms)}")
    sorted_times = sorted(times_ms)
    # statistics.quantiles(data, n=100) returns 99 values: the 1st through
    # 99th percentiles.  Index 49 → p50, 94 → p95, 98 → p99.
    percentiles = statistics.quantiles(sorted_times, n=100, method="inclusive")
    return {
        "p50": percentiles[49],
        "p95": percentiles[94],
        "p99": percentiles[98],
        "min": sorted_times[0],
        "max": sorted_times[-1],
        "mean": statistics.mean(sorted_times),
    }


def print_table(stats: dict[str, float], label: str) -> None:
    """Print a markdown table of *stats* with an optional *label* header."""
    if label:
        print(f"\n### {label}")
    print("| Metric | Value (ms) |")
    print("|--------|-----------|")
    for key in ("p50", "p95", "p99", "min", "max", "mean"):
        print(f"| {key:<6} | {stats[key]:>9.2f} |")


def run_single_benchmark(
    iterations: int,
    target: str,
    threshold_ms: float,
) -> int:
    """Run a single benchmark (one target) and return the exit code."""
    times: list[float] = []
    failures: int = 0
    print(f"Running {iterations} cold-import iterations for target='{target}' ...")

    for i in range(iterations):
        try:
            elapsed = measure_subprocess_import(target)
            times.append(elapsed)
            print(f"  [{i + 1}/{iterations}] {elapsed:>8.2f} ms")
        except subprocess.CalledProcessError as exc:
            failures += 1
            print(
                f"  [{i + 1}/{iterations}] FAILED (stderr: {exc.stderr.strip()})",
                file=sys.stderr,
            )

    if not times:
        print("Error: no successful iterations.", file=sys.stderr)
        return 1

    stats = compute_stats(times)
    print_table(stats, target)

    if failures:
        print(f"\nError: {failures} iteration(s) failed.", file=sys.stderr)

    passed = stats["p50"] <= threshold_ms
    if passed:
        print(f"✓ p50 ({stats['p50']:.2f} ms) ≤ {threshold_ms:.0f} ms threshold — PASS")
    else:
        print(
            f"✗ p50 ({stats['p50']:.2f} ms) > {threshold_ms:.0f} ms threshold — FAIL",
            file=sys.stderr,
        )

    return 0 if passed and failures == 0 else 1


def _resolve_targets(target_arg: str) -> list[str]:
    """Normalise the ``--target`` CLI argument into a list of target keys."""
    target_map: dict[str, Target] = {
        "import": "import",
        "normalize": "normalize",
    }
    if target_arg == "both":
        return ["import", "normalize"]
    if target_arg not in target_map:
        print(
            f"Error: unknown target '{target_arg}'. Choose from: import, normalize, both.",
            file=sys.stderr,
        )
        sys.exit(1)
    return [target_map[target_arg]]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark cold import time of paxman. "
            "Measures p50, p95, p99 over N iterations in a fresh subprocess."
        ),
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Number of cold-import iterations (default: {DEFAULT_ITERATIONS})",
    )
    parser.add_argument(
        "--threshold-ms",
        type=float,
        default=DEFAULT_THRESHOLD_MS,
        help=f"p50 threshold in ms (default: {DEFAULT_THRESHOLD_MS})",
    )
    parser.add_argument(
        "--target",
        choices=["import", "normalize", "both"],
        default="import",
        help=(
            "What to benchmark: 'import' (just ``import paxman``), "
            "'normalize' (also touch ``paxman.normalize``), "
            "or 'both' (run both benchmarks).  Default: import."
        ),
    )

    args = parser.parse_args()

    if args.iterations < 2:
        print(
            "Error: --iterations must be at least 2 for meaningful statistics.",
            file=sys.stderr,
        )
        return 1

    targets = _resolve_targets(args.target)
    exit_codes: list[int] = []

    for target in targets:
        code = run_single_benchmark(
            iterations=args.iterations,
            target=target,
            threshold_ms=args.threshold_ms,
        )
        exit_codes.append(code)

    # Return 1 if any benchmark failed.
    overall = 0 if all(c == 0 for c in exit_codes) else 1
    if overall != 0:
        print("\nOne or more benchmarks exceeded the threshold.", file=sys.stderr)
    return overall


if __name__ == "__main__":
    sys.exit(main())

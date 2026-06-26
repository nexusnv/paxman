"""Benchmark harness for ``paxman.normalize()`` — Sprint 9 D9.1.

Benchmarks ``normalize()`` on a 20-field contract with ~100 KB input
(no remote inference).  Targets (aspirational, not gating):

    p50 <= 200 ms
    p99 <= 2 s

Uses ``pytest-benchmark`` with ``pedantic()`` mode for statistical
rigor (explicit rounds and warmup).
"""

from __future__ import annotations

import pytest

import paxman
import paxman.contract.adapters.dict_dsl  # noqa: F401 — triggers adapter self-registration
from paxman.artifact.artifact import ExecutionArtifact
from paxman.budget import Policy
from paxman.types import Status

pytestmark = pytest.mark.benchmark


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------


def test_benchmark_normalize_20_fields_100kb(
    benchmark,
    benchmark_contract_20_fields: dict[str, object],
    benchmark_input_100kb: str,
    benchmark_policy: Policy,
) -> None:
    """Benchmark normalize() on a 20-field contract with ~100 KB input.

    This is the primary D9.1 benchmark.  The contract covers all V1
    types (STRING, INTEGER, DECIMAL, BOOLEAN, DATE, ENUM, MONEY,
    ARRAY) except OBJECT.  Remote inference is disabled.
    """
    # Verify input size before benchmarking.
    size = len(benchmark_input_100kb.encode("utf-8"))
    assert size >= 90_000, f"Input too small: {size:,} bytes (expected >= 90,000)"

    def _normalize() -> ExecutionArtifact:
        artifact = paxman.normalize(
            input_data=benchmark_input_100kb,
            contract=benchmark_contract_20_fields,
            policy=benchmark_policy,
        )
        assert artifact.status in {
            Status.SUCCESS,
            Status.PARTIAL_SUCCESS,
            Status.UNRESOLVED,
        }
        return artifact

    benchmark.pedantic(_normalize, rounds=10, warmup_rounds=3)


def test_benchmark_normalize_20_fields_small_input(
    benchmark,
    benchmark_contract_20_fields: dict[str, object],
    benchmark_input_small: str,
    benchmark_policy: Policy,
) -> None:
    """Benchmark normalize() on a 20-field contract with a small (~300 B) input.

    Baseline comparison — shows how input size affects throughput.
    """

    def _normalize() -> ExecutionArtifact:
        return paxman.normalize(
            input_data=benchmark_input_small,
            contract=benchmark_contract_20_fields,
            policy=benchmark_policy,
        )

    benchmark.pedantic(_normalize, rounds=10, warmup_rounds=3)


def test_benchmark_normalize_invoice_baseline(
    benchmark,
    benchmark_input_small: str,
    benchmark_policy: Policy,
) -> None:
    """Benchmark normalize() on the standard 6-field invoice contract.

    Uses the same DICT_DSL_INVOICE fixture as integration tests for
    cross-suite comparability.
    """
    from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE

    def _normalize() -> ExecutionArtifact:
        return paxman.normalize(
            input_data=benchmark_input_small,
            contract=DICT_DSL_INVOICE,
            policy=benchmark_policy,
        )

    benchmark.pedantic(_normalize, rounds=10, warmup_rounds=3)

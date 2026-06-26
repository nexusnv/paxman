"""Benchmark harness for paxman.replay() — Sprint 9 D9.2.

Benchmarks replay() on artifacts of varying sizes.  Targets
(aspirational, not gating):
    p50 <= 50 ms
    p99 <= 500 ms

Uses ``pytest-benchmark`` with ``pedantic()`` mode for statistical
rigor (explicit rounds and warmup).

Golden artifact sizes (all well under 100 KB):
    all_v1_types_unresolved.json       — 8,717 bytes  (largest golden)
    invoice_unresolved_dict_dsl.json   — 4,970 bytes

Since all goldens are under 100 KB, we inflate an artifact by
padding ``normalized_data`` with a large synthetic dict to reach
the target size for the inflated benchmark.
"""

from __future__ import annotations

import attrs
import pytest

import paxman
import paxman.contract.adapters.dict_dsl  # triggers adapter self-registration
from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact
from paxman.artifact.serializer import encode_artifact
from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE

pytestmark = pytest.mark.benchmark

_INVOICE_INPUT: str = "ACME Corp\nInvoice #1234\nTotal: $1,234.56\nDate: 2026-06-22\nCurrency: USD"


@pytest.fixture(scope="session")
def invoice_artifact() -> ExecutionArtifact:
    """Standard-size artifact (~5 KB) from the invoice contract.

    Same inputs as golden ``invoice_unresolved_dict_dsl.json``
    (4,970 bytes on disk).
    """
    return paxman.normalize(
        input_data=_INVOICE_INPUT,
        contract=DICT_DSL_INVOICE,
    )


@pytest.fixture(scope="session")
def inflated_artifact_100kb() -> ExecutionArtifact:
    """Artifact with normalized_data padded to ~100 KB.

    Strategy: pad normalized_data with 120 synthetic dict entries
    (~960 bytes each in compact JSON) so the serialized artifact
    exceeds 100 KB.  The replay_hash is recomputed to keep the
    artifact replayable.
    """
    base = paxman.normalize(
        input_data=_INVOICE_INPUT,
        contract=DICT_DSL_INVOICE,
    )
    padding: dict[str, object] = {}
    for i in range(120):
        padding[f"synthetic_field_{i:04d}"] = {
            "description": f"Synthetic benchmark padding field {i}. " * 15,
            "values": list(range(100)),
            "metadata": {"index": i, "category": "benchmark_padding", "active": True},
        }
    inflated = attrs.evolve(base, normalized_data={**base.normalized_data, **padding})
    inflated = attrs.evolve(inflated, replay_hash=compute_replay_hash(inflated))
    return inflated


def test_benchmark_replay_standard(
    benchmark,
    invoice_artifact: ExecutionArtifact,
) -> None:
    """Benchmark paxman.replay() on a standard-size artifact (~5 KB).

    Contract: DICT_DSL_INVOICE (6 fields).
    Artifact source: invoice_unresolved_dict_dsl.json (4,970 bytes).
    """
    benchmark.pedantic(
        paxman.replay,
        args=(invoice_artifact, DICT_DSL_INVOICE),
        rounds=10,
        warmup_rounds=3,
    )


def test_benchmark_replay_inflated_100kb(
    benchmark,
    inflated_artifact_100kb: ExecutionArtifact,
) -> None:
    """Benchmark paxman.replay() on an inflated artifact (~100 KB).

    The artifact is inflated by padding normalized_data with 120
    synthetic fields.  The replay_hash is recomputed so the artifact
    remains valid.
    """
    size_bytes = len(encode_artifact(inflated_artifact_100kb).encode("utf-8"))
    assert size_bytes >= 100_000, (
        f"Inflated artifact is {size_bytes:,} bytes, expected >= 100,000. "
        "Increase padding in the inflated_artifact_100kb fixture."
    )
    benchmark.pedantic(
        paxman.replay,
        args=(inflated_artifact_100kb, DICT_DSL_INVOICE),
        rounds=10,
        warmup_rounds=3,
    )


def test_benchmark_replay_byte_equal_invariant(
    benchmark,
    invoice_artifact: ExecutionArtifact,
) -> None:
    """Benchmark the byte-equal invariant: replay(a, c) == a.

    Per REPLAY_AND_DETERMINISM.md, replay returns the same object
    when all integrity checks pass (identity, not just equality).
    """

    def _replay_and_assert_equality() -> None:
        result = paxman.replay(invoice_artifact, contract=DICT_DSL_INVOICE)
        assert result == invoice_artifact
        assert result is invoice_artifact

    benchmark.pedantic(
        _replay_and_assert_equality,
        rounds=10,
        warmup_rounds=3,
    )

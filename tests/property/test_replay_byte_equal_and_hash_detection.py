"""Property tests: Replay is byte-equal and hash modification is detected.

Per Sprint 7 D7.8 and D7.9, these tests verify that:

1. ``paxman.replay()`` reproduces an :class:`ExecutionArtifact` byte-for-byte
   (D7.8).
2. Any modification to a hash-relevant field changes the ``replay_hash``
   (D7.9).

The tests are property-based (Hypothesis) and run 100 examples by default
(``derandomize=True`` for determinism). They are also marked as
``replay`` for selection by ``-m replay``.
"""

from __future__ import annotations

import attrs
import hypothesis
import pytest
from hypothesis import given
from hypothesis import strategies as st

import paxman

# Trigger auto-registration of adapters used by some properties.
import paxman.contract.adapters.dict_dsl
from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact
from paxman.testing import artifacts

pytestmark = [pytest.mark.property, pytest.mark.replay]


# ---------------------------------------------------------------------------
# D7.8 — Replay is byte-equal
# ---------------------------------------------------------------------------


@st.composite
def _artifact_with_contract(draw: st.DrawFn) -> tuple[ExecutionArtifact, dict[str, object]]:
    """Generate an (artifact, dict DSL contract) pair for replay testing.

    ``paxman.replay()`` accepts an external contract (Pydantic, dict,
    or str) — not a :class:`CanonicalContract`. We use the Dict DSL
    form here because it is the simplest.
    """
    art = draw(artifacts())
    contract: dict[str, object] = {
        "id": art.contract_id or "replay-prop-test",
        "version": "1",
        "fields": [
            {
                "name": "replay_field",
                "type": "STRING",
                "required": True,
            },
        ],
    }
    return art, contract


def _inner_replay_is_byte_equal(
    pair: tuple[ExecutionArtifact, dict[str, object]],
) -> None:
    artifact, contract = pair
    replayed = paxman.replay(artifact, contract=contract)
    assert replayed == artifact
    assert replayed.replay_hash == artifact.replay_hash


test_replay_is_byte_equal = hypothesis.settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[
        hypothesis.HealthCheck.too_slow,
        hypothesis.HealthCheck.filter_too_much,
    ],
)(given(_artifact_with_contract())(_inner_replay_is_byte_equal))


# ---------------------------------------------------------------------------
# D7.9 — Hash modification detection
# ---------------------------------------------------------------------------


def _inner_hash_detects_modification(artifact: ExecutionArtifact) -> None:
    original_hash = artifact.replay_hash
    # The original ``replay_hash`` was set by the strategy; we
    # also need the *un-hashed* artifact (replay_hash="") so we
    # can recompute after ``attrs.evolve``.
    un_hashed = attrs.evolve(artifact, replay_hash="")

    candidates = [
        ("contract_id", attrs.evolve(un_hashed, contract_id="tampered")),
        ("paxman_version", attrs.evolve(un_hashed, paxman_version="99.99.99")),
        ("planner_version", attrs.evolve(un_hashed, planner_version="99")),
    ]
    for field_name, modified in candidates:
        # Recompute the hash for the modified artifact.
        new_hash = compute_replay_hash(modified)
        # Per ``REPLAY_AND_DETERMINISM.md`` §2.1, ``contract_id``,
        # ``paxman_version``, and ``planner_version`` are all
        # hash-relevant. Modifying them MUST change the hash.
        assert new_hash != original_hash, (
            f"Hash-relevant field {field_name!r} modification did not change the hash. "
            f"original={original_hash}, new={new_hash}. "
            f"This indicates a regression in compute_replay_hash or "
            f"hash relevance."
        )
        # The hash on the modified artifact should equal a fresh
        # computation (reproducibility).
        assert compute_replay_hash(modified) == new_hash


test_hash_detects_field_modification = hypothesis.settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[
        hypothesis.HealthCheck.too_slow,
        hypothesis.HealthCheck.filter_too_much,
    ],
)(given(artifacts())(_inner_hash_detects_modification))


# ---------------------------------------------------------------------------
# Sanity: artifact's replay_hash is computed via compute_replay_hash
# ---------------------------------------------------------------------------


def _inner_replay_hash_matches_compute(artifact: ExecutionArtifact) -> None:
    assert artifact.replay_hash == compute_replay_hash(artifact)


test_replay_hash_matches_compute = hypothesis.settings(
    derandomize=True,
    deadline=None,
    max_examples=20,
    suppress_health_check=[
        hypothesis.HealthCheck.too_slow,
        hypothesis.HealthCheck.filter_too_much,
    ],
)(given(artifacts())(_inner_replay_hash_matches_compute))

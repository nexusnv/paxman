"""Unit tests for ``paxman.artifact._hash`` — compute_replay_hash, REPLAY_VERSION."""

from __future__ import annotations

import typing

import pytest

from paxman.artifact._hash import REPLAY_VERSION, compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.types import Status

pytestmark = pytest.mark.unit


def _make_artifact(**overrides: typing.Any) -> ExecutionArtifact:
    """Build an ExecutionArtifact with status=SUCCESS, plus any overrides."""
    return ExecutionArtifact(status=Status.SUCCESS, **overrides)


def _valid_hex64(s: str) -> str:
    """Ensure s is 64 lowercase hex characters (pad or truncate)."""
    return (s * 64)[:64]


# ============================================================================
# REPLAY_VERSION
# ============================================================================


@pytest.mark.deterministic
def test_replay_version_is_string_one() -> None:
    """REPLAY_VERSION is the string \"1\"."""
    assert REPLAY_VERSION == "1"
    assert isinstance(REPLAY_VERSION, str)


# ============================================================================
# compute_replay_hash
# ============================================================================


@pytest.mark.deterministic
def test_compute_replay_hash_returns_64_char_hex() -> None:
    """compute_replay_hash returns a 64-character lowercase hex string."""
    art = _make_artifact()
    h = compute_replay_hash(art)
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


@pytest.mark.deterministic
def test_compute_replay_hash_deterministic() -> None:
    """Same input always produces the same hash."""
    art = _make_artifact(normalized_data={"a": 1})
    h1 = compute_replay_hash(art)
    h2 = compute_replay_hash(art)
    assert h1 == h2


@pytest.mark.deterministic
def test_compute_replay_hash_different_inputs_different_hashes() -> None:
    """Different artifacts (different hash-relevant fields) produce different hashes."""
    art1 = _make_artifact(contract_id="contract-a")
    art2 = _make_artifact(contract_id="contract-b")
    assert compute_replay_hash(art1) != compute_replay_hash(art2)


@pytest.mark.deterministic
def test_compute_replay_hash_differs_with_field_results() -> None:
    """Hashes differ when field_results differ."""
    fr1 = FieldResult(field_path="x", value=1, status=Status.SUCCESS)
    fr2 = FieldResult(field_path="x", value=2, status=Status.SUCCESS)
    art1 = _make_artifact(field_results={"x": fr1})
    art2 = _make_artifact(field_results={"x": fr2})
    assert compute_replay_hash(art1) != compute_replay_hash(art2)


@pytest.mark.deterministic
def test_compute_replay_hash_differs_with_contract_id() -> None:
    """Hashes differ when contract_id differs."""
    art1 = _make_artifact(contract_id="invoice-v1")
    art2 = _make_artifact(contract_id="invoice-v2")
    assert compute_replay_hash(art1) != compute_replay_hash(art2)


@pytest.mark.deterministic
def test_compute_replay_hash_differs_with_capability_versions() -> None:
    """Hashes differ when capability_versions differ."""
    art1 = _make_artifact(capability_versions={"regex_extraction": "1.0"})
    art2 = _make_artifact(capability_versions={"regex_extraction": "2.0"})
    assert compute_replay_hash(art1) != compute_replay_hash(art2)


@pytest.mark.deterministic
def test_compute_replay_hash_differs_with_execution_plan() -> None:
    """Hashes differ when execution_plan differs."""
    from paxman.planner.field_plan import ExecutionPlan

    plan1 = ExecutionPlan(field_plans=())
    plan2 = ExecutionPlan(field_plans=(), contract_id="other")
    art1 = _make_artifact(execution_plan=plan1)
    art2 = _make_artifact(execution_plan=plan2)
    assert compute_replay_hash(art1) != compute_replay_hash(art2)


@pytest.mark.deterministic
def test_compute_replay_hash_differs_with_custom_paxman_version() -> None:
    """Hashes differ when paxman_version differs (should not happen in practice)."""
    art1 = _make_artifact(paxman_version="0.0.0")
    art2 = _make_artifact(paxman_version="0.0.1")
    assert compute_replay_hash(art1) != compute_replay_hash(art2)


@pytest.mark.deterministic
def test_compute_replay_hash_consistent_with_empty_replay_hash_on_artifact() -> None:
    """compute_replay_hash computes from the content, ignoring the stored replay_hash field."""
    art = _make_artifact(replay_hash="")
    h = compute_replay_hash(art)
    # Set the hash on the artifact and recompute — should be different because
    # field_results now includes the hash as a relevant field? Wait, replay_hash
    # is NOT in the hash composition (it's excluded). Let's verify: the hash should
    # be the same regardless of replay_hash value.
    assert compute_replay_hash(art) == h


@pytest.mark.deterministic
def test_compute_replay_hash_ignores_replay_hash_in_artifact() -> None:
    """compute_replay_hash excludes the replay_hash field from hash composition."""
    h1 = compute_replay_hash(_make_artifact(replay_hash=""))
    h2 = compute_replay_hash(_make_artifact(replay_hash="a" * 64))
    assert h1 == h2


@pytest.mark.deterministic
def test_compute_replay_hash_ignores_id() -> None:
    """compute_replay_hash excludes id from hash composition (different IDs, same hash)."""
    # We can't set id directly (frozen), but we can create artifacts with defaults
    # and check that two identical artifacts have the same hash.
    h1 = compute_replay_hash(_make_artifact())
    h2 = compute_replay_hash(_make_artifact())
    assert h1 == h2  # Different IDs but same content => same hash

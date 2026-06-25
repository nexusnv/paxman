"""Unit tests for ``paxman.artifact.replay`` — replay_artifact."""

from __future__ import annotations

import typing

import attrs
import pytest

from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.artifact.replay import replay_artifact
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.errors import CapabilityNotFoundError, HashMismatchError, VersionMismatchError
from paxman.protocols import Capability
from paxman.types import FieldType, Status

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_contract() -> CanonicalContract:
    """Build a minimal CanonicalContract for replay tests."""
    return CanonicalContract(
        id="test-contract",
        fields=(
            CanonicalField(
                id="f1",
                path="name",
                name="name",
                type=FieldType.STRING,
                required=True,
            ),
        ),
    )


class _MockCapability:
    """A minimal stub that satisfies the Capability protocol."""

    def __init__(self, spec: object = None) -> None:
        self._spec = spec

    @property
    def spec(self) -> object:
        return self._spec

    def invoke(self, ctx: object) -> object:
        return None


class _MockRegistry:
    """A simple CapabilityRegistry implementation for testing."""

    def __init__(self, caps: dict[str, Capability] | None = None) -> None:
        self._caps: dict[str, Capability] = caps or {}

    def get(self, capability_id: str) -> Capability | None:
        return self._caps.get(capability_id)


def _make_artifact(**overrides: typing.Any) -> ExecutionArtifact:
    """Build an ExecutionArtifact with status=SUCCESS and compute its replay_hash."""
    art = ExecutionArtifact(status=Status.SUCCESS, **overrides)
    # If no replay_hash was explicitly provided, compute one
    if "replay_hash" not in overrides:
        h = compute_replay_hash(art)
        # Use attrs.evolve to set the computed hash
        art = attrs.evolve(art, replay_hash=h)
    return art


# ============================================================================
# Check 1: Type checks
# ============================================================================


@pytest.mark.deterministic
def test_replay_artifact_raises_type_error_on_none() -> None:
    """replay_artifact raises TypeError when artifact is None."""
    contract = _make_contract()
    registry = _MockRegistry()
    with pytest.raises(TypeError, match="replay_artifact requires a non-None artifact"):
        replay_artifact(None, contract, registry)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_replay_artifact_raises_type_error_on_wrong_type() -> None:
    """replay_artifact raises TypeError when artifact is not an ExecutionArtifact."""
    contract = _make_contract()
    registry = _MockRegistry()
    with pytest.raises(TypeError, match="replay_artifact requires an ExecutionArtifact"):
        replay_artifact("not_an_artifact", contract, registry)  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_replay_artifact_type_check_passes() -> None:
    """replay_artifact accepts a valid ExecutionArtifact."""
    art = _make_artifact()
    contract = _make_contract()
    registry = _MockRegistry()
    result = replay_artifact(art, contract, registry)
    assert result is art


# ============================================================================
# Check 2: Version checks
# ============================================================================


@pytest.mark.deterministic
def test_replay_artifact_raises_on_major_mismatch() -> None:
    """Different major version raises VersionMismatchError."""
    art = _make_artifact(paxman_version="1.0.0")
    contract = _make_contract()
    registry = _MockRegistry()
    with pytest.raises(VersionMismatchError, match="major version mismatch"):
        replay_artifact(art, contract, registry)


@pytest.mark.deterministic
def test_replay_artifact_raises_on_artifact_from_future() -> None:
    """Artifact from a newer minor/patch raises VersionMismatchError."""
    art = _make_artifact(paxman_version="0.0.1")  # newer than current 0.0.0
    contract = _make_contract()
    registry = _MockRegistry()
    with pytest.raises(VersionMismatchError, match="artifact is from a newer version"):
        replay_artifact(art, contract, registry)


@pytest.mark.deterministic
def test_replay_artifact_accepts_same_version() -> None:
    """Artifact with same version passes check."""
    art = _make_artifact(paxman_version="0.0.0")
    contract = _make_contract()
    registry = _MockRegistry()
    result = replay_artifact(art, contract, registry)
    assert result is art


# ============================================================================
# Check 3: Capability registration
# ============================================================================


@pytest.mark.deterministic
def test_replay_artifact_raises_on_unregistered_capability() -> None:
    """Unregistered capability raises CapabilityNotFoundError."""
    art = _make_artifact(capability_versions={"regex_extraction": "1.0"})
    contract = _make_contract()
    registry = _MockRegistry()  # empty registry
    with pytest.raises(
        CapabilityNotFoundError,
        match=r"Capability.*regex_extraction.*no longer registered",
    ):
        replay_artifact(art, contract, registry)


@pytest.mark.deterministic
def test_replay_artifact_accepts_registered_capability() -> None:
    """All capabilities registered passes check."""
    art = _make_artifact(capability_versions={"regex_extraction": "1.0"})
    contract = _make_contract()
    registry = _MockRegistry(caps={"regex_extraction": _MockCapability()})
    result = replay_artifact(art, contract, registry)
    assert result is art


@pytest.mark.deterministic
def test_replay_artifact_mixed_capabilities() -> None:
    """Mix of registered and unregistered capabilities raises error."""
    art = _make_artifact(
        capability_versions={
            "regex_extraction": "1.0",
            "missing_cap": "0.5",
        }
    )
    contract = _make_contract()
    registry = _MockRegistry(caps={"regex_extraction": _MockCapability()})
    with pytest.raises(
        CapabilityNotFoundError,
        match=r"Capability.*missing_cap.*no longer registered",
    ):
        replay_artifact(art, contract, registry)


# ============================================================================
# Check 4: Hash check
# ============================================================================


@pytest.mark.deterministic
def test_replay_artifact_passes_hash_check() -> None:
    """Valid artifact with correct replay_hash passes check."""
    art = _make_artifact()
    contract = _make_contract()
    registry = _MockRegistry()
    result = replay_artifact(art, contract, registry)
    assert result is art


@pytest.mark.deterministic
def test_replay_artifact_tampered_field_raises_hash_mismatch() -> None:
    """Tampering with a hash-relevant field raises HashMismatchError."""
    art = _make_artifact(contract_id="original")
    contract = _make_contract()
    registry = _MockRegistry()

    # Tamper with a hash-relevant field (contract_id is in hash composition)
    tampered = attrs.evolve(art, contract_id="tampered")

    with pytest.raises(HashMismatchError, match="Artifact hash mismatch"):
        replay_artifact(tampered, contract, registry)


@pytest.mark.deterministic
def test_replay_artifact_tampered_field_results_raises() -> None:
    """Tampering with field_results raises HashMismatchError."""
    fr1 = FieldResult(field_path="name", value="Alice", status=Status.SUCCESS)
    fr2 = FieldResult(field_path="name", value="Bob", status=Status.SUCCESS)
    art = _make_artifact(field_results={"name": fr1})
    contract = _make_contract()
    registry = _MockRegistry()

    tampered = attrs.evolve(art, field_results={"name": fr2})
    with pytest.raises(HashMismatchError, match="Artifact hash mismatch"):
        replay_artifact(tampered, contract, registry)


@pytest.mark.deterministic
def test_replay_artifact_tampered_contract_id_raises() -> None:
    """Tampering with contract_id raises HashMismatchError."""
    art = _make_artifact(contract_id="original")
    contract = _make_contract()
    registry = _MockRegistry()

    tampered = attrs.evolve(art, contract_id="tampered")
    with pytest.raises(HashMismatchError, match="Artifact hash mismatch"):
        replay_artifact(tampered, contract, registry)


@pytest.mark.deterministic
def test_replay_artifact_tampered_capability_versions_raises() -> None:
    """Tampering with capability_versions raises HashMismatchError."""
    art = _make_artifact(capability_versions={"rx": "1.0"})
    contract = _make_contract()
    registry = _MockRegistry(caps={"rx": _MockCapability(), "tx": _MockCapability()})

    tampered = attrs.evolve(art, capability_versions={"tx": "2.0"})
    with pytest.raises(HashMismatchError, match="Artifact hash mismatch"):
        replay_artifact(tampered, contract, registry)


# ============================================================================
# Full integration — complete replay cycle
# ============================================================================


@pytest.mark.deterministic
def test_replay_artifact_full_cycle() -> None:
    """Full replay cycle: build, hash, and replay successfully."""
    fr = FieldResult(field_path="name", value="ACME", status=Status.SUCCESS)
    art = _make_artifact(
        normalized_data={"name": "ACME"},
        field_results={"name": fr},
        contract_id="test-contract",
        capability_versions={"regex_extraction": "1.0"},
    )
    contract = _make_contract()
    registry = _MockRegistry(caps={"regex_extraction": _MockCapability()})

    result = replay_artifact(art, contract, registry)
    assert result is art


@pytest.mark.deterministic
def test_replay_artifact_hash_check_error_details() -> None:
    """HashMismatchError carries expected and actual hash in context."""
    art = _make_artifact(contract_id="contract-a")
    contract = _make_contract()
    registry = _MockRegistry()

    tampered = attrs.evolve(art, contract_id="contract-b")
    with pytest.raises(HashMismatchError) as exc_info:
        replay_artifact(tampered, contract, registry)

    ctx = exc_info.value.context
    assert "expected_hash" in ctx
    assert "actual_hash" in ctx
    assert ctx["expected_hash"] != ctx["actual_hash"]

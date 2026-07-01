"""Replay integrity tests — D6.20 replay equality, D6.21 tamper detection, D6.22 version mismatch.

These tests exercise the full replay pipeline via ``paxman.replay()``,
verifying that artifacts produced by ``paxman.normalize()`` can be
replayed successfully and that tampering is reliably detected.
"""

from __future__ import annotations

import attrs
import pytest

import paxman

# Trigger auto-registration for Dict DSL adapter.
import paxman.contract.adapters.dict_dsl
from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact
from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE

pytestmark = pytest.mark.replay


# ---------------------------------------------------------------------------
# Session-scoped fixture: produce one artifact for all replay tests.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def artifact() -> ExecutionArtifact:
    """Build a replayable artifact from the Dict DSL invoice contract.

    The artifact is produced once per test session and reused across
    all replay integrity tests.  Since ``normalize()`` is deterministic
    (same input + contract → same artifact), session-scoping is safe.
    """
    return paxman.normalize(
        input_data="ACME Corp\nInvoice #1234\nTotal: $1,234.56",
        contract=DICT_DSL_INVOICE,
    )


# ---------------------------------------------------------------------------
# D6.20 — Replay equality
# ---------------------------------------------------------------------------


class TestReplayEquality:
    """Replayed artifact must be byte-equal to the original."""

    def test_replay_returns_same_replay_hash(self, artifact: ExecutionArtifact) -> None:
        """``paxman.replay()`` produces an artifact with the identical ``replay_hash``."""
        replayed = paxman.replay(artifact, contract=DICT_DSL_INVOICE)
        assert replayed.replay_hash == artifact.replay_hash

    def test_replay_artifact_is_equal_to_original(self, artifact: ExecutionArtifact) -> None:
        """The replayed artifact compares equal to the original (``attrs`` equality)."""
        replayed = paxman.replay(artifact, contract=DICT_DSL_INVOICE)
        assert replayed == artifact

    def test_replay_artifact_is_same_object(self, artifact: ExecutionArtifact) -> None:
        """``replay()`` returns the same artifact object when checks pass."""
        replayed = paxman.replay(artifact, contract=DICT_DSL_INVOICE)
        # ``replay_artifact`` returns the unchanged input on success,
        # so ``replay`` should return the same object.
        assert replayed is artifact


# ---------------------------------------------------------------------------
# D6.21 — Tamper detection
# ---------------------------------------------------------------------------


class TestTamperDetection:
    """Any modification to a hash-relevant field must cause ``HashMismatchError``."""

    def test_tampered_contract_id_raises_hash_mismatch(self, artifact: ExecutionArtifact) -> None:
        """Changing ``contract_id`` (hash-relevant) raises ``HashMismatchError``."""
        tampered = attrs.evolve(artifact, contract_id="tampered")
        with pytest.raises(paxman.HashMismatchError, match="Artifact hash mismatch"):
            paxman.replay(tampered, contract=DICT_DSL_INVOICE)

    def test_tampered_field_results_raises_hash_mismatch(self, artifact: ExecutionArtifact) -> None:
        """Changing ``field_results`` (hash-relevant) raises ``HashMismatchError``."""
        modified = artifact.field_results.copy()
        # Add a bogus entry to trigger a hash difference.
        modified["bogus_field"] = artifact.field_results.get("supplier_name", "tampered")  # type: ignore[arg-type]
        tampered = attrs.evolve(artifact, field_results=modified)
        with pytest.raises(paxman.HashMismatchError, match="Artifact hash mismatch"):
            paxman.replay(tampered, contract=DICT_DSL_INVOICE)

    def test_tampered_evidence_raises_hash_mismatch(self, artifact: ExecutionArtifact) -> None:
        """Changing ``evidence`` (hash-relevant) raises ``HashMismatchError``."""
        tampered = attrs.evolve(artifact, evidence=("bogus_evidence",))
        with pytest.raises(paxman.HashMismatchError, match="Artifact hash mismatch"):
            paxman.replay(tampered, contract=DICT_DSL_INVOICE)

    def test_tampered_diagnostics_raises_hash_mismatch(self, artifact: ExecutionArtifact) -> None:
        """Changing ``diagnostics`` (hash-relevant) raises ``HashMismatchError``."""
        tampered = attrs.evolve(artifact, diagnostics=("bogus_diagnostic",))
        with pytest.raises(paxman.HashMismatchError, match="Artifact hash mismatch"):
            paxman.replay(tampered, contract=DICT_DSL_INVOICE)

    def test_unmodified_artifact_passes_replay(self, artifact: ExecutionArtifact) -> None:
        """An unmodified artifact passes replay without errors."""
        # This should not raise.
        paxman.replay(artifact, contract=DICT_DSL_INVOICE)


# ---------------------------------------------------------------------------
# D6.22 — Version mismatch
# ---------------------------------------------------------------------------


class TestVersionMismatch:
    """Replaying an artifact from an incompatible Paxman version must raise ``VersionMismatchError``."""

    def test_different_major_version_raises_version_mismatch(
        self, artifact: ExecutionArtifact
    ) -> None:
        """Artifact with a different major version raises ``VersionMismatchError``.

        Changing ``paxman_version`` to ``"2.0.0"`` (current is ``"1.0.0"``)
        triggers a major version mismatch.  The hash is recomputed so the
        hash check itself would pass — the version check happens first.
        """
        tampered = attrs.evolve(artifact, paxman_version="2.0.0")
        # Recompute the replay hash so that the hash remains internally
        # consistent.  The version check runs before the hash check, so
        # a consistent hash does not mask the version mismatch.
        tampered = attrs.evolve(tampered, replay_hash=compute_replay_hash(tampered))
        with pytest.raises(paxman.VersionMismatchError, match="major version mismatch"):
            paxman.replay(tampered, contract=DICT_DSL_INVOICE)

    def test_artifact_from_future_raises_version_mismatch(
        self, artifact: ExecutionArtifact
    ) -> None:
        """Artifact from a newer minor/patch version raises ``VersionMismatchError``."""
        tampered = attrs.evolve(artifact, paxman_version="1.1.0")
        tampered = attrs.evolve(tampered, replay_hash=compute_replay_hash(tampered))
        with pytest.raises(paxman.VersionMismatchError, match="artifact is from a newer version"):
            paxman.replay(tampered, contract=DICT_DSL_INVOICE)

    def test_same_version_passes_replay(self, artifact: ExecutionArtifact) -> None:
        """Artifact with the same version passes replay without issues."""
        # The fixture artifact already has the correct version.
        paxman.replay(artifact, contract=DICT_DSL_INVOICE)


# ---------------------------------------------------------------------------
# Mismatched contract ID (hash composition)
# ---------------------------------------------------------------------------


class TestContractIdMismatch:
    """Changing the artifact's ``contract_id`` without updating the hash causes ``HashMismatchError``."""

    def test_changed_contract_id_without_hash_update_raises_hash_mismatch(
        self, artifact: ExecutionArtifact
    ) -> None:
        """Changing ``contract_id`` without recomputing the hash raises ``HashMismatchError``."""
        tampered = attrs.evolve(artifact, contract_id="other-contract")
        with pytest.raises(paxman.HashMismatchError, match="Artifact hash mismatch"):
            paxman.replay(tampered, contract=DICT_DSL_INVOICE)

    def test_changed_contract_id_with_hash_update_passes_replay_if_version_ok(
        self, artifact: ExecutionArtifact
    ) -> None:
        """Changing ``contract_id`` and recomputing the hash allows replay to succeed.

        This confirms that ``contract_id`` is correctly included in the
        hash composition — updating the hash to match the new contract_id
        makes the artifact internally consistent again.
        """
        tampered = attrs.evolve(artifact, contract_id="other-contract")
        tampered = attrs.evolve(tampered, replay_hash=compute_replay_hash(tampered))
        # Should not raise, because the hash is consistent.
        result = paxman.replay(tampered, contract=DICT_DSL_INVOICE)
        assert result.replay_hash == tampered.replay_hash


# ---------------------------------------------------------------------------
# Issue #60 — capability_versions must be derived from the reconciled
# evidence set (single source of truth). Previously the field was built
# from pre-reconciliation evidence, which caused stale entries to leak
# into replay verification.
# ---------------------------------------------------------------------------


class TestCapabilityVersionsConsistency:
    """``ExecutionArtifact.capability_versions`` must be a subset of
    ``ExecutionArtifact.evidence`` capability_ids (single source of truth).

    This invariant was violated before the fix for #60, which built
    ``capability_versions`` from the raw pre-reconciliation evidence
    set (``cr.evidence``) while ``artifact.evidence`` was built from
    the reconciled set (``rr.evidence_refs``). The asymmetry could
    leave ``capability_versions`` with stale entries that triggered
    false ``CapabilityNotFoundError`` during replay.
    """

    def test_capability_versions_keys_subset_of_evidence(
        self, artifact: ExecutionArtifact
    ) -> None:
        """Every ``capability_id`` in ``capability_versions`` appears in ``evidence``."""
        evidence_cap_ids = {ev.capability_id for ev in artifact.evidence}
        version_cap_ids = set(artifact.capability_versions)
        assert version_cap_ids.issubset(evidence_cap_ids), (
            f"capability_versions has capability_ids not in evidence: "
            f"{version_cap_ids - evidence_cap_ids}"
        )

    def test_capability_versions_pairs_subset_of_evidence_pairs(
        self, artifact: ExecutionArtifact
    ) -> None:
        """Every ``(capability_id, capability_version)`` pair in ``capability_versions``
        appears in ``evidence``. Catches a regression where the same cap_id is
        recorded with a version that is not in the reconciled evidence."""
        evidence_pairs = {
            (ev.capability_id, ev.capability_version) for ev in artifact.evidence
        }
        version_pairs = set(artifact.capability_versions.items())
        assert version_pairs.issubset(evidence_pairs), (
            f"capability_versions has pairs not in evidence: "
            f"{version_pairs - evidence_pairs}"
        )

    def test_replay_succeeds_on_normal_artifact(
        self, artifact: ExecutionArtifact
    ) -> None:
        """End-to-end: a normal ``normalize()`` artifact must replay without
        ``CapabilityNotFoundError``. This is the original failure mode of #60 —
        stale ``capability_versions`` entries caused the replay check
        (artifact/replay.py:199) to fail."""
        # Should not raise. The fixture produces a normal artifact.
        result = paxman.replay(artifact, contract=DICT_DSL_INVOICE)
        # The replayed artifact has the same capability_versions as the original.
        assert result.capability_versions == artifact.capability_versions

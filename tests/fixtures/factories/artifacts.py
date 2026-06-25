"""``ExecutionArtifact`` factory for replay tests.

Per Sprint 7 D7.4, this factory generates realistic ``ExecutionArtifact``
instances for replay and golden-artifact tests.
"""

from __future__ import annotations

import attrs
import factory

from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.types import ConfidenceBand, Status


def _build_artifact(num_fields: int = 2) -> ExecutionArtifact:
    """Build a deterministic ``ExecutionArtifact`` with *num_fields* fields.

    Uses ``factory.Faker._get_faker()`` so the seed is set via the
    project-wide ``factory.random.reseed_random`` call.
    """
    f = factory.Faker._get_faker()
    field_results: dict[str, FieldResult] = {}
    normalized_data: dict[str, object] = {}
    unresolved_fields: list[str] = []

    for i in range(num_fields):
        path = f"field_{i}"
        if f.boolean():
            value = f.word()
            field_results[path] = FieldResult(
                field_path=path,
                value=value,
                confidence=ConfidenceBand.HIGH,
                candidates=(),
                evidence_refs=(),
                status=Status.SUCCESS,
            )
            normalized_data[path] = value
        else:
            field_results[path] = FieldResult(
                field_path=path,
                value=None,
                confidence=ConfidenceBand.UNTRUSTED,
                candidates=(),
                evidence_refs=(),
                status=Status.UNRESOLVED,
            )
            unresolved_fields.append(path)

    artifact = ExecutionArtifact(
        status=(
            Status.PARTIAL_SUCCESS
            if unresolved_fields and normalized_data
            else (Status.SUCCESS if not unresolved_fields else Status.UNRESOLVED)
        ),
        id=f"art_factory_{f.bothify('########').lower()}",
        normalized_data=normalized_data,
        field_results=field_results,
        unresolved_fields=unresolved_fields,
        evidence=(),
        diagnostics=(),
        execution_plan=None,
        replay_hash="",  # set below
        statistics=None,
        contract_id=f"contract_factory_{f.bothify('######').lower()}",
        capability_versions={},
    )
    return attrs.evolve(artifact, replay_hash=compute_replay_hash(artifact))


class ExecutionArtifactFactory(factory.Factory):
    """A deterministic ``ExecutionArtifact`` with a stable ``replay_hash``.

    The factory output is deterministic for a fixed seed: the same
    sequence of calls produces the same artifact, including the
    ``replay_hash``. Tests that need a stable artifact should
    ``reseed(SEED)`` before invoking.
    """

    class Meta:
        model = ExecutionArtifact

    @classmethod
    def _create(cls, *args: object, **kwargs: object) -> ExecutionArtifact:  # type: ignore[override]
        return _build_artifact(num_fields=2)

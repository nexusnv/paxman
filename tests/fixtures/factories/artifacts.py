"""``ExecutionArtifact`` factory for replay tests.

Per Sprint 7 D7.4, this factory generates realistic ``ExecutionArtifact``
instances for replay and golden-artifact tests.
"""

from __future__ import annotations

import attrs
import factory
import faker

from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.types import ConfidenceBand, Status

# Use the project-wide seed (imported for side-effect-free reference).
from tests.fixtures.factories import SEED  # noqa: F401


def _build_artifact(num_fields: int = 2) -> ExecutionArtifact:
    """Build a deterministic ``ExecutionArtifact`` with *num_fields* fields.

    Uses a public ``faker.Faker`` instance seeded via
    :func:`factory.random.reseed_random` (the public ``factory_boy``
    seeding entry point). This avoids the private
    ``factory.Faker._get_faker()`` attribute.
    """
    factory.random.reseed_random(SEED)
    f = faker.Faker()
    f.seed_instance(SEED)
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
    def _create(  # type: ignore[override]
        cls, *args: object, num_fields: int = 2, **kwargs: object
    ) -> ExecutionArtifact:
        return _build_artifact(num_fields=num_fields)

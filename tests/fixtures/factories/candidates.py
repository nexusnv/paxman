"""Candidate and ``CandidateResult`` factories for Reconciler property tests.

Per Sprint 7 D7.4 and ``docs/TEST_DATA.md`` §7.1, these factories
generate realistic ``Candidate`` and ``CandidateResult`` instances
for the Reconciler.
"""

from __future__ import annotations

import factory

from paxman.capabilities.result import Candidate, EvidenceRef
from paxman.executor.field_runner import CandidateResult


class EvidenceRefFactory(factory.Factory):
    """An ``EvidenceRef`` with random capability and field_path."""

    class Meta:
        model = EvidenceRef

    capability_id = factory.Faker("bothify", text="cap_???")
    capability_version = "1.0"
    field_path = factory.Faker("word")
    span = None
    model_id = None
    context = factory.LazyFunction(dict)


class CandidateFactory(factory.Factory):
    """A ``Candidate`` with random value and 1-3 evidence refs."""

    class Meta:
        model = Candidate

    value = factory.Faker("word")
    # Build a non-empty tuple of evidence refs so downstream tests
    # exercise ``Candidate.evidence_refs`` (the tuple type is preserved).
    evidence_refs = factory.LazyAttribute(
        lambda _o: tuple(EvidenceRefFactory() for _ in range(2))
    )


class CandidateResultFactory(factory.Factory):
    """A ``CandidateResult`` (frozen) with random field and 1-3 candidates."""

    class Meta:
        model = CandidateResult

    field_id = factory.Faker("word")
    field_path = factory.SelfAttribute("field_id")
    field_type_name = "STRING"
    # Build a non-empty tuple of candidates so downstream tests
    # exercise ``CandidateResult.candidates`` (the tuple type is preserved).
    candidates = factory.LazyAttribute(
        lambda _o: tuple(CandidateFactory() for _ in range(2))
    )
    status = "RESOLVED"

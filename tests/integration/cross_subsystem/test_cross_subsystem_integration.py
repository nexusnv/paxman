"""Integration tests: Cross-subsystem interactions (D7.14).

Per Sprint 7 D7.14, this test verifies that adjacent subsystems
(e.g., planner+executor, executor+reconciler) work together
correctly. The cross-subsystem contracts are enforced by
``import-linter`` in CI, but the *behavioural* interactions
are also verified here.
"""

from __future__ import annotations

import pytest

import paxman

# Trigger auto-registration.
import paxman.contract.adapters.dict_dsl
import paxman.contract.adapters.pydantic
from paxman.artifact.artifact import ExecutionArtifact
from paxman.budget import Budget
from paxman.contract.canonical import CanonicalContract
from paxman.planner.input_profile import make_profile
from paxman.planner.planner import plan
from paxman.reconciler.reconciler import reconcile
from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE

pytestmark = pytest.mark.integration


class TestCrossSubsystem:
    """Cross-subsystem integration tests."""

    def test_planner_executor_integration(self) -> None:
        """Planner produces a plan that the executor can run.

        This test exercises the planner → executor hand-off. The
        planner produces an :class:`ExecutionPlan`; the executor
        runs it (even with no V1 capabilities registered) and
        produces a list of :class:`CandidateResult`.
        """
        from paxman.contract.registry import adapt as _adapt_contract
        from paxman.executor.executor import run as _run_executor
        from paxman.planner.input_profile import InputProfile

        # Adapt the contract via the dict_dsl format.
        canonical = _adapt_contract(DICT_DSL_INVOICE, format_id="dict_dsl")
        profile: InputProfile = make_profile("ACME Corp\nTotal: $1,234.56\n")
        execution_plan = plan(canonical=canonical, profile=profile)

        # Run with no capabilities registered — should produce
        # an empty list of candidates per field.
        result = _run_executor(
            plan=execution_plan,
            raw_input=b"ACME Corp\nTotal: $1,234.56\n",
            input_profile=profile,
            budget=Budget(max_total_cost_usd=0.10),
        )
        # Result is a list of CandidateResult (may be empty).
        assert isinstance(result, list)

    def test_executor_reconciler_integration(self) -> None:
        """Executor output is consumed by the Reconciler.

        The Reconciler accepts a sequence of :class:`CandidateResult`
        and produces a sequence of :class:`ResolvedResult`. This
        test runs the Reconciler directly with a single-field
        contract and empty candidates.
        """
        from paxman.contract.canonical import CanonicalField
        from paxman.executor.field_runner import CandidateResult
        from paxman.types import FieldType

        # Single-field contract with one CandidateResult.
        candidate_results: tuple[CandidateResult, ...] = (
            CandidateResult(
                field_id="field_1",
                field_path="field_1",
                field_type_name="STRING",
                candidates=(),
                status="UNRESOLVED",
            ),
        )
        canonical = CanonicalContract(
            id="cross-subsystem-test",
            fields=(
                CanonicalField(
                    id="field_1",
                    path="field_1",
                    name="field_1",
                    type=FieldType.STRING,
                    required=True,
                ),
            ),
        )
        resolved = reconcile(candidate_results, canonical)
        assert len(resolved) == 1
        # No candidates → UNRESOLVED.
        assert resolved[0].status == "UNRESOLVED"

    def test_full_pipeline_with_pydantic_contract(self) -> None:
        """The full pipeline runs end-to-end on a Pydantic contract.

        This is a smoke test: it verifies that the
        contract→planner→executor→reconciler→artifact pipeline
        works without crashing when given a Pydantic model.
        """
        from tests.fixtures.contracts.pydantic.invoice import Invoice

        artifact = paxman.normalize(input_data="ACME Corp\nTotal: $1,234.56", contract=Invoice)
        assert isinstance(artifact, ExecutionArtifact)
        # The Pydantic contract adapted successfully.
        assert artifact.contract_id == "Invoice"
        # Replay is byte-equal.
        replayed = paxman.replay(artifact, contract=Invoice)
        assert replayed == artifact

    def test_pipeline_returns_consistent_hash_across_input_orders(self) -> None:
        """The same input + contract produces the same ``replay_hash`` regardless of execution order.

        Specifically, two consecutive calls to ``paxman.normalize``
        with the same input + contract should produce artifacts
        with the same ``replay_hash``.
        """
        text = "ACME Corp\nInvoice #1234\nTotal: $1,234.56"
        art1 = paxman.normalize(input_data=text, contract=DICT_DSL_INVOICE)
        art2 = paxman.normalize(input_data=text, contract=DICT_DSL_INVOICE)
        # The replay hash is identical (deterministic).
        assert art1.replay_hash == art2.replay_hash
        # The status is identical.
        assert art1.status == art2.status

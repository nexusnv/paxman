"""Tests for the public ``paxman.testing`` Hypothesis strategies module.

Per Sprint 7 D7.1, ``paxman.testing`` exposes 7 public strategies:

- :func:`contracts` — :class:`CanonicalContract` instances.
- :func:`inputs` — raw input bytes/str.
- :func:`budgets` — :class:`Budget` instances.
- :func:`policies` — :class:`Policy` instances.
- :func:`registries` — :class:`Capability` registries.
- :func:`candidate_sets` — ``CandidateResult[]`` for the Reconciler.
- :func:`artifacts` — :class:`ExecutionArtifact` instances.

Exit criterion #10: ``from paxman.testing import contracts, inputs,
budgets, policies, registries`` works.
"""

from __future__ import annotations

import hypothesis
import pytest
from hypothesis import given

# Marker: this is a public API test, not a property test.
pytestmark = pytest.mark.unit


def test_testing_module_is_importable() -> None:
    """The ``paxman.testing`` module is importable."""
    import paxman.testing

    assert paxman.testing is not None


def test_contracts_strategy_is_importable() -> None:
    """The ``contracts`` strategy is importable from ``paxman.testing``."""
    from paxman.testing import contracts

    assert contracts is not None


def test_inputs_strategy_is_importable() -> None:
    """The ``inputs`` strategy is importable from ``paxman.testing``."""
    from paxman.testing import inputs

    assert inputs is not None


def test_budgets_strategy_is_importable() -> None:
    """The ``budgets`` strategy is importable from ``paxman.testing``."""
    from paxman.testing import budgets

    assert budgets is not None


def test_policies_strategy_is_importable() -> None:
    """The ``policies`` strategy is importable from ``paxman.testing``."""
    from paxman.testing import policies

    assert policies is not None


def test_registries_strategy_is_importable() -> None:
    """The ``registries`` strategy is importable from ``paxman.testing``."""
    from paxman.testing import registries

    assert registries is not None


def test_candidate_sets_strategy_is_importable() -> None:
    """The ``candidate_sets`` strategy is importable from ``paxman.testing``."""
    from paxman.testing import candidate_sets

    assert candidate_sets is not None


def test_artifacts_strategy_is_importable() -> None:
    """The ``artifacts`` strategy is importable from ``paxman.testing``."""
    from paxman.testing import artifacts

    assert artifacts is not None


def test_all_seven_strategies_are_callable() -> None:
    """All 7 strategies are callable and return Hypothesis ``SearchStrategy`` instances."""
    from hypothesis.strategies import SearchStrategy

    from paxman import testing

    # All 7 strategies must be callable and return SearchStrategy instances.
    for name in (
        "contracts",
        "inputs",
        "budgets",
        "policies",
        "registries",
        "candidate_sets",
        "artifacts",
    ):
        strategy_factory = getattr(testing, name)
        assert callable(strategy_factory), f"{name} is not callable"
        strategy = strategy_factory()
        assert isinstance(strategy, SearchStrategy), f"{name}() did not return a SearchStrategy"


def test_contracts_strategy_generates_canonical_contracts() -> None:
    """The ``contracts`` strategy generates ``CanonicalContract`` instances."""
    from paxman.contract.canonical import CanonicalContract
    from paxman.testing import contracts

    @given(contract=contracts())
    @hypothesis.settings(max_examples=10, derandomize=True, deadline=None)
    def _inner(contract: object) -> None:
        assert isinstance(contract, CanonicalContract)
        # All generated contracts have at least 1 field.
        assert len(contract.fields) >= 1

    _inner()


def test_budgets_strategy_generates_budgets() -> None:
    """The ``budgets`` strategy generates ``Budget`` instances."""
    from paxman.budget import Budget
    from paxman.testing import budgets

    @given(budget=budgets())
    @hypothesis.settings(max_examples=10, derandomize=True, deadline=None)
    def _inner(budget: object) -> None:
        assert isinstance(budget, Budget)

    _inner()


def test_policies_strategy_generates_policies() -> None:
    """The ``policies`` strategy generates ``Policy`` instances."""
    from paxman.budget import Policy
    from paxman.testing import policies

    @given(policy=policies())
    @hypothesis.settings(max_examples=10, derandomize=True, deadline=None)
    def _inner(policy: object) -> None:
        assert isinstance(policy, Policy)
        # All confidence_floor values are in [0.0, 1.0].
        assert 0.0 <= policy.confidence_floor <= 1.0

    _inner()


def test_inputs_strategy_generates_inputs() -> None:
    """The ``inputs`` strategy generates ``bytes`` instances."""
    from paxman.testing import inputs

    @given(raw=inputs())
    @hypothesis.settings(max_examples=10, derandomize=True, deadline=None)
    def _inner(raw: object) -> None:
        assert isinstance(raw, bytes)

    _inner()


def test_candidate_sets_strategy_generates_lists() -> None:
    """The ``candidate_sets`` strategy generates ``list[dict]`` candidate sets.

    Note: this strategy returns a ``list[dict[str, Any]]`` representation
    rather than ``list[CandidateResult]`` because ``CandidateResult``
    construction is complex and varies by use case. The downstream
    Reconciler tests build ``CandidateResult`` instances from these dicts.
    """
    from paxman.testing import candidate_sets

    @given(candidates=candidate_sets())
    @hypothesis.settings(max_examples=10, derandomize=True, deadline=None)
    def _inner(candidates: object) -> None:
        assert isinstance(candidates, list)
        for item in candidates:
            assert isinstance(item, dict)

    _inner()


def test_artifacts_strategy_generates_artifacts() -> None:
    """The ``artifacts`` strategy generates ``ExecutionArtifact`` instances."""
    from paxman.artifact.artifact import ExecutionArtifact
    from paxman.testing import artifacts

    @given(artifact=artifacts())
    @hypothesis.settings(max_examples=10, derandomize=True, deadline=None)
    def _inner(artifact: object) -> None:
        assert isinstance(artifact, ExecutionArtifact)
        # Replay hash is non-empty.
        assert len(artifact.replay_hash) == 64

    _inner()


def test_registries_strategy_generates_dicts() -> None:
    """The ``registries`` strategy generates ``dict`` registries."""
    from paxman.testing import registries

    @given(registry=registries())
    @hypothesis.settings(max_examples=10, derandomize=True, deadline=None)
    def _inner(registry: object) -> None:
        assert isinstance(registry, dict)
        for key in registry:
            assert isinstance(key, tuple)
            assert len(key) == 2

    _inner()


def test_install_registry_context_manager() -> None:
    """``install_registry`` correctly installs and removes capabilities."""
    from paxman.capabilities.registry import all_capabilities
    from paxman.testing import install_registry, registries

    @given(registry=registries())
    @hypothesis.settings(max_examples=5, derandomize=True, deadline=None)
    def _inner(registry: object) -> None:
        assert isinstance(registry, dict)
        with install_registry(registry):
            # Inside the context, all capabilities are present.
            inside = all_capabilities()
            for key in registry:
                assert key in inside
        # Outside the context, the registry is reset.
        outside = all_capabilities()
        for key in registry:
            assert key not in outside

    _inner()


def test_strategies_can_be_used_with_given() -> None:
    """The strategies are usable as ``@given`` parameters in downstream tests.

    This is the canonical usage pattern documented in ``TESTING_STRATEGY.md``
    §3.2. We confirm all 7 strategies work as ``@given`` parameters.
    """
    from paxman.testing import (
        artifacts,
        budgets,
        candidate_sets,
        contracts,
        inputs,
        policies,
        registries,
    )

    @given(
        contract=contracts(),
        raw=inputs(),
        budget=budgets(),
        policy=policies(),
        registry=registries(),
        candidates=candidate_sets(),
        artifact=artifacts(),
    )
    @hypothesis.settings(max_examples=3, derandomize=True, deadline=None)
    def _inner(
        contract: object,
        raw: object,
        budget: object,
        policy: object,
        registry: object,
        candidates: object,
        artifact: object,
    ) -> None:
        # All arguments are non-None.
        assert contract is not None
        assert raw is not None
        assert budget is not None
        assert policy is not None
        assert registry is not None
        assert candidates is not None
        assert artifact is not None

    _inner()

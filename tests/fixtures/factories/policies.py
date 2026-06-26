"""Policy and Budget factories.

Per Sprint 7 D7.4, this module provides ``factory_boy`` factories for
:class:`~paxman.budget.Budget` and :class:`~paxman.budget.Policy`.
"""

from __future__ import annotations

import decimal

import factory

from paxman.budget import Budget, Policy
from tests.fixtures.factories.inputs import _get_faker


class BudgetFactory(factory.Factory):
    """A :class:`Budget` with random caps."""

    class Meta:
        model = Budget

    max_total_cost_usd = factory.LazyAttribute(
        lambda _o: _get_faker().pydecimal(min_value=0, max_value=10, right_digits=4)
    )
    max_total_latency_ms = factory.LazyAttribute(
        lambda _o: _get_faker().random_int(min=100, max=60_000)
    )
    max_remote_inference_calls = factory.LazyAttribute(
        lambda _o: _get_faker().random_int(min=0, max=10)
    )
    max_capability_invocations = factory.LazyAttribute(
        lambda _o: _get_faker().random_int(min=1, max=100)
    )


class PolicyFactory(factory.Factory):
    """A :class:`Policy` with random boolean and numeric settings."""

    class Meta:
        model = Policy

    allow_remote_inference = factory.Faker("boolean")
    allow_local_inference = factory.Faker("boolean")
    confidence_floor = factory.LazyAttribute(
        lambda _o: float(
            _get_faker().pydecimal(
                min_value=decimal.Decimal("0.5"),
                max_value=decimal.Decimal("1.0"),
                right_digits=2,
            )
        )
    )
    unresolved_acceptable = factory.Faker("boolean")

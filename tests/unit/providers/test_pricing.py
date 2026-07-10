"""Tests for PricingResolver + StaticPricingResolver (V1.2.0 design spec #50 §8).

Per design spec #50 §8 (D12): pricing is pluggable. The default
implementation, ``StaticPricingResolver``, reads from a frozen
``dict[ModelRef, PricingTuple]`` shipped in the provider's
``__init__.py``. Future ``LivePricingResolver`` and
``UserPricingResolver`` are extension shapes; not in V1.2.0.

Per ADR-0004: money is Decimal-only. The ``compute_cost_usd``
helper returns ``Decimal``; no ``float`` math anywhere in this
module.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.capabilities.v1.inference import Usage
from paxman.providers._model import ModelRef
from paxman.providers._pricing import (
    PricingResolver,
    PricingTuple,
    StaticPricingResolver,
    compute_cost_usd,
)


class TestPricingTuple:
    """``PricingTuple`` is a frozen attrs dataclass; both fields are
    ``Decimal`` per ADR-0004 (money is Decimal-only)."""

    def test_basic_construction(self) -> None:
        t = PricingTuple(
            prompt_usd_per_token=Decimal("0.0000025"),
            completion_usd_per_token=Decimal("0.00001"),
        )
        assert t.prompt_usd_per_token == Decimal("0.0000025")
        assert t.completion_usd_per_token == Decimal("0.00001")

    def test_rejects_float(self) -> None:
        """ADR-0004: pricing is Decimal-only, not float."""
        with pytest.raises(TypeError):
            PricingTuple(
                prompt_usd_per_token=0.0000025,  # type: ignore[arg-type]
                completion_usd_per_token=Decimal("0.00001"),
            )

    def test_rejects_int(self) -> None:
        with pytest.raises(TypeError):
            PricingTuple(
                prompt_usd_per_token=1,  # type: ignore[arg-type]
                completion_usd_per_token=Decimal("0.00001"),
            )

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            PricingTuple(
                prompt_usd_per_token=Decimal("-0.0001"),
                completion_usd_per_token=Decimal("0.00001"),
            )

    def test_zero_pricing_is_allowed(self) -> None:
        """Free models (e.g. local stubs) are valid; zero is non-negative."""
        t = PricingTuple(
            prompt_usd_per_token=Decimal("0"),
            completion_usd_per_token=Decimal("0"),
        )
        assert t.prompt_usd_per_token == Decimal("0")
        assert t.completion_usd_per_token == Decimal("0")


class TestComputeCostUsd:
    """``compute_cost_usd`` is a pure function returning ``Decimal``."""

    def test_basic(self) -> None:
        pricing = PricingTuple(
            prompt_usd_per_token=Decimal("0.0000025"),
            completion_usd_per_token=Decimal("0.00001"),
        )
        usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = compute_cost_usd(usage, pricing)
        # 1000 * 0.0000025 + 500 * 0.00001 = 0.0025 + 0.005 = 0.0075
        assert cost == Decimal("0.0075")

    def test_zero_usage(self) -> None:
        pricing = PricingTuple(
            prompt_usd_per_token=Decimal("0.0000025"),
            completion_usd_per_token=Decimal("0.00001"),
        )
        usage = Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        assert compute_cost_usd(usage, pricing) == Decimal("0")

    def test_returns_decimal_not_float(self) -> None:
        """Per ADR-0004: money is Decimal-only."""
        pricing = PricingTuple(
            prompt_usd_per_token=Decimal("0.0000025"),
            completion_usd_per_token=Decimal("0.00001"),
        )
        usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        cost = compute_cost_usd(usage, pricing)
        assert isinstance(cost, Decimal)

    def test_zero_pricing_returns_zero(self) -> None:
        """Free models produce zero cost."""
        pricing = PricingTuple(
            prompt_usd_per_token=Decimal("0"),
            completion_usd_per_token=Decimal("0"),
        )
        usage = Usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        assert compute_cost_usd(usage, pricing) == Decimal("0")

    def test_precision_preserved(self) -> None:
        """The math is exact (Decimal) — no float rounding noise."""
        pricing = PricingTuple(
            prompt_usd_per_token=Decimal("0.00000001"),  # 1/100M USD
            completion_usd_per_token=Decimal("0.00000003"),  # 3/100M USD
        )
        usage = Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        cost = compute_cost_usd(usage, pricing)
        # 1 * 0.00000001 + 1 * 0.00000003 = 0.00000004
        assert cost == Decimal("0.00000004")


class TestStaticPricingResolver:
    """``StaticPricingResolver`` reads from a frozen
    ``dict[ModelRef, PricingTuple]``. The constructor takes a
    defensive copy of the supplied table; the resolver does not hold
    a reference to the caller's dict, so later mutations of the
    caller's dict do not affect the resolver."""

    def test_price_known_model(self) -> None:
        ref = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        table = {
            ref: PricingTuple(
                prompt_usd_per_token=Decimal("0.0000025"),
                completion_usd_per_token=Decimal("0.00001"),
            ),
        }
        resolver = StaticPricingResolver(table)
        result = resolver.price(ref)
        assert result is not None
        assert result.prompt_usd_per_token == Decimal("0.0000025")

    def test_price_unknown_model_returns_none(self) -> None:
        resolver = StaticPricingResolver({})
        ref = ModelRef(provider="openai", model="unknown")
        assert resolver.price(ref) is None

    def test_empty_table(self) -> None:
        resolver = StaticPricingResolver()
        ref = ModelRef(provider="anthropic", model="claude-3-5-sonnet-20241022")
        assert resolver.price(ref) is None

    def test_table_immutable_at_construction(self) -> None:
        """The resolver must not allow mutation of the underlying
        table after construction (defensive copy)."""
        ref = ModelRef(provider="openai", model="x")
        original_table = {
            ref: PricingTuple(
                prompt_usd_per_token=Decimal("0.0000025"),
                completion_usd_per_token=Decimal("0.00001"),
            ),
        }
        resolver = StaticPricingResolver(original_table)
        # Mutate the original dict; the resolver must not see the change.
        original_table.clear()
        assert resolver.price(ref) is not None  # still has the original entry

    def test_explicit_none_table(self) -> None:
        """Passing None is equivalent to passing an empty dict."""
        resolver = StaticPricingResolver(None)  # type: ignore[arg-type]
        ref = ModelRef(provider="openai", model="x")
        assert resolver.price(ref) is None


class TestPricingResolverProtocol:
    """The ``PricingResolver`` Protocol is structural."""

    def test_static_satisfies_protocol(self) -> None:
        resolver: PricingResolver = StaticPricingResolver()
        assert hasattr(resolver, "price")
        assert callable(resolver.price)

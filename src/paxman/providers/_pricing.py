"""``_pricing`` — PricingResolver SPI and StaticPricingResolver (V1.2.0, spec §8).

Per design spec #50 §8 (D12): pricing is pluggable. The default
implementation, :class:`StaticPricingResolver`, reads from a frozen
``dict[ModelRef, PricingTuple]`` shipped in the provider's
``__init__.py``. Future ``LivePricingResolver`` and
``UserPricingResolver`` are extension shapes; not in V1.2.0.

Per ADR-0004: money is Decimal-only. The :func:`compute_cost_usd`
helper returns ``Decimal``; no ``float`` math anywhere in this
module.
"""

from __future__ import annotations

import typing
from decimal import Decimal

import attrs

from paxman.capabilities.v1.inference import Usage
from paxman.providers._model import ModelRef

__all__ = [
    "PricingResolver",
    "PricingTuple",
    "StaticPricingResolver",
    "compute_cost_usd",
]


# ---------------------------------------------------------------------------
# PricingTuple
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class PricingTuple:
    """Per-token USD pricing for a :class:`ModelRef`.

    Attributes:
        prompt_usd_per_token: USD cost per prompt token.
        completion_usd_per_token: USD cost per completion token.

    Note:
        Per ADR-0004, these are :class:`decimal.Decimal` values, not
        ``float``. Negative values are rejected at construction.
    """

    prompt_usd_per_token: Decimal = attrs.field()
    completion_usd_per_token: Decimal = attrs.field()

    def __attrs_post_init__(self) -> None:
        for f in (self.prompt_usd_per_token, self.completion_usd_per_token):
            if not isinstance(f, Decimal):
                raise TypeError(f"pricing must be a Decimal, got {type(f).__name__}: {f!r}")
            if not f.is_finite():
                raise ValueError(f"pricing must be finite (no NaN/Infinity), got {f}")
            if f < 0:
                raise ValueError(f"pricing must be non-negative, got {f}")


# ---------------------------------------------------------------------------
# compute_cost_usd
# ---------------------------------------------------------------------------


def compute_cost_usd(usage: Usage, pricing: PricingTuple) -> Decimal:
    """Compute the USD cost of a :class:`Usage` against a :class:`PricingTuple`.

    Formula:
        cost = usage.prompt_tokens * pricing.prompt_usd_per_token
             + usage.completion_tokens * pricing.completion_usd_per_token

    Args:
        usage: The :class:`Usage` token counts.
        pricing: The :class:`PricingTuple` per-token pricing.

    Returns:
        The total cost in USD as a :class:`decimal.Decimal`. Returns
        ``Decimal("0")`` for zero-token usage.
    """
    return (
        Decimal(usage.prompt_tokens) * pricing.prompt_usd_per_token
        + Decimal(usage.completion_tokens) * pricing.completion_usd_per_token
    )


# ---------------------------------------------------------------------------
# PricingResolver
# ---------------------------------------------------------------------------


class PricingResolver(typing.Protocol):
    """SPI: a resolver for the price of a given :class:`ModelRef`.

    Implementations return a :class:`PricingTuple` (per-token USD
    pricing) for a given :class:`ModelRef`, or ``None`` if the
    model is not priced.

    Per spec §8: the recorded ``Usage`` is the source of truth for
    exact recomputation. The :class:`StaticPricingResolver` is a
    sensible default; enterprise users can plug in a custom
    :class:`PricingResolver` (e.g. one that reads from a
    tenant-specific contract table).
    """

    def price(self, model_ref: ModelRef) -> PricingTuple | None:
        """Return the :class:`PricingTuple` for ``model_ref``, or ``None``."""
        ...


# ---------------------------------------------------------------------------
# StaticPricingResolver
# ---------------------------------------------------------------------------


class StaticPricingResolver:
    """Default :class:`PricingResolver` backed by a defensive dict copy.

    The constructor takes a defensive copy of the supplied table;
    the resolver does not hold a reference to the caller's dict, so
    later mutations of the caller's dict do not affect the resolver.

    Thread-safety: instances are stateless after construction (the
    table is frozen at construction time via the defensive copy).
    Concurrent ``price()`` calls from multiple threads are safe.
    """

    def __init__(
        self,
        table: dict[ModelRef, PricingTuple] | None = None,
    ) -> None:
        """Build a resolver over a defensive copy of ``table``.

        Args:
            table: The pricing table. Defaults to ``None`` (empty
                resolver). The constructor copies the dict; the
                resolver does not share state with the caller.
        """
        self._table: dict[ModelRef, PricingTuple] = dict(table or {})

    def price(self, model_ref: ModelRef) -> PricingTuple | None:
        """Return the :class:`PricingTuple` for ``model_ref``, or ``None``."""
        return self._table.get(model_ref)

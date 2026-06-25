"""Execution statistics — duration, cost, and capability-level metrics.

The :class:`Statistics` data model captures measurements from a
:func:`paxman.normalize` call, including wall-clock duration,
monotonic execution time, total cost in USD, and per-capability
breakdowns.
"""

from __future__ import annotations

from decimal import Decimal

import attrs

from paxman.types import Status

__all__ = [
    "CapabilityStats",
    "Statistics",
]


@attrs.frozen(slots=True)
class CapabilityStats:
    """Per-capability execution statistics.

    Attributes:
        capability_id: The capability's id (e.g., ``"regex_extraction"``).
        capability_version: The capability's version.
        invocation_count: Number of times the capability was invoked.
        total_duration_ms: Total wall-clock time in milliseconds.
        total_cost_usd: Total cost in USD (Decimal).
        total_tokens: Total tokens consumed (0 for non-inference caps).
    """

    capability_id: str = attrs.field()
    capability_version: str = attrs.field()
    invocation_count: int = 0
    total_duration_ms: float = 0.0
    total_cost_usd: Decimal = Decimal("0")
    total_tokens: int = 0

    def __attrs_post_init__(self) -> None:
        """Validate invariants."""
        if not isinstance(self.capability_id, str) or not self.capability_id:
            raise ValueError(
                f"capability_id must be a non-empty string, got {self.capability_id!r}"
            )
        if not isinstance(self.capability_version, str) or not self.capability_version:
            raise ValueError(
                f"capability_version must be a non-empty string, got {self.capability_version!r}"
            )
        if not isinstance(self.invocation_count, int) or self.invocation_count < 0:
            raise ValueError(
                f"invocation_count must be a non-negative int, got {self.invocation_count!r}"
            )
        if not isinstance(self.total_duration_ms, (int, float)) or isinstance(
            self.total_duration_ms, bool
        ):
            raise TypeError(
                f"total_duration_ms must be a number, got {type(self.total_duration_ms).__name__}"
            )
        if self.total_duration_ms < 0:
            raise ValueError(
                f"total_duration_ms must be non-negative, got {self.total_duration_ms}"
            )
        if not isinstance(self.total_cost_usd, Decimal):
            raise TypeError(
                f"total_cost_usd must be a Decimal, got {type(self.total_cost_usd).__name__}"
            )
        if self.total_cost_usd < 0:
            raise ValueError(
                f"total_cost_usd must be non-negative, got {self.total_cost_usd}"
            )
        if not isinstance(self.total_tokens, int) or isinstance(self.total_tokens, bool):
            raise TypeError(
                f"total_tokens must be an int, got {type(self.total_tokens).__name__}"
            )
        if self.total_tokens < 0:
            raise ValueError(
                f"total_tokens must be non-negative, got {self.total_tokens}"
            )


@attrs.frozen(slots=True)
class Statistics:
    """Aggregate execution statistics for a normalize call.

    Attributes:
        status: The overall :class:`Status` of the normalize call.
        wall_clock_ms: Wall-clock duration in milliseconds.
        monotonic_ms: Monotonic execution time in milliseconds.
        total_cost_usd: Total cost across all capabilities in USD.
        total_fields: Total number of fields in the contract.
        resolved_fields: Number of fields resolved successfully.
        unresolved_fields: Number of fields left unresolved.
        capability_stats: Tuple of per-capability :class:`CapabilityStats`.
    """

    status: Status = Status.UNRESOLVED
    wall_clock_ms: float = 0.0
    monotonic_ms: float = 0.0
    total_cost_usd: Decimal = Decimal("0")
    total_fields: int = 0
    resolved_fields: int = 0
    unresolved_fields: int = 0
    capability_stats: tuple[CapabilityStats, ...] = ()

    def __attrs_post_init__(self) -> None:
        """Validate invariants."""
        if not isinstance(self.status, Status):
            raise TypeError(f"status must be a Status enum, got {type(self.status).__name__}")
        for attr_name in (
            "wall_clock_ms",
            "monotonic_ms",
        ):
            val = getattr(self, attr_name)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise TypeError(f"{attr_name} must be a number, got {type(val).__name__}")
            if val < 0:
                raise ValueError(f"{attr_name} must be non-negative, got {val}")
        if not isinstance(self.total_cost_usd, Decimal):
            raise TypeError(
                f"total_cost_usd must be a Decimal, got {type(self.total_cost_usd).__name__}"
            )
        if self.total_cost_usd < 0:
            raise ValueError(
                f"total_cost_usd must be non-negative, got {self.total_cost_usd}"
            )
        for attr_name in ("total_fields", "resolved_fields", "unresolved_fields"):
            val = getattr(self, attr_name)
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"{attr_name} must be a non-negative int, got {val!r}")
        if not isinstance(self.capability_stats, tuple):
            raise TypeError(
                f"capability_stats must be a tuple, got {type(self.capability_stats).__name__}"
            )

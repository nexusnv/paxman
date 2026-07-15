"""Contract kind -> builder dispatch.

Replaces the former `_KIND_DISPATCH` dict and the per-kind `if` branches
in `parse_contract`. Each capability domain registers a builder at import
time (see `paxman._capabilities.<domain>.contract`). The DSL parser asks
this registry; it never names a concrete contract class.

This module is domain-free: it imports only the generic `Contract`
Protocol (structural) from `_core.contracts` and the error hierarchy. The
public `Contract` union of concrete contracts lives in `paxman.__init__`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from paxman._errors import ContractError

if TYPE_CHECKING:
    from paxman._capabilities.date.contract import CanonicalDateContract
    from paxman._capabilities.email.contract import CanonicalEmailContract
    from paxman._capabilities.uuid.contract import CanonicalUUIDContract

# The builder returns a concrete contract value object; the union is
# imported under TYPE_CHECKING only so the registry stays domain-free at
# runtime (the domain contract modules import this registry, so a runtime
# import here would be a cycle).
Builder = Callable[
    [dict[str, Any]],
    "CanonicalEmailContract | CanonicalUUIDContract | CanonicalDateContract",
]

_REGISTRY: dict[str, Builder] = {}


def register_contract(kind: str, builder: Builder) -> None:
    """Register a builder for contract `kind`. Raises on duplicate kind."""
    if kind in _REGISTRY:
        raise ContractError(f"contract kind already registered: {kind!r}")
    _REGISTRY[kind] = builder


def get_builder(kind: str) -> Builder:
    """Return the builder for `kind`, or raise ContractError if unknown."""
    if kind not in _REGISTRY:
        raise ContractError(
            f"unknown contract kind: {kind!r}; supported kinds: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[kind]


def known_kinds() -> list[str]:
    """Return the sorted list of registered contract kinds."""
    return sorted(_REGISTRY)

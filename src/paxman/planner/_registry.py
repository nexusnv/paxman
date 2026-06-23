"""Internal handle to the global capability registry from the planner.

The planner reads capabilities via the
:mod:`paxman.capabilities.registry` module. This thin wrapper
exists so the planner can pass a registry argument to its
heuristic functions without importing
:mod:`paxman.capabilities.registry` everywhere.

Currently this is a 1:1 alias; if V2 ever introduces per-call
registries (e.g., for multi-tenant scenarios), this is the seam.
"""

from __future__ import annotations

import typing

from paxman.capabilities.base import Capability
from paxman.capabilities.registry import all_capabilities

__all__ = ["get_global_registry"]


def get_global_registry() -> typing.Mapping[tuple[str, str], Capability]:
    """Return the global capability registry as a read-only mapping.

    Returns:
        The :func:`paxman.capabilities.registry.all_capabilities`
        read-only snapshot.
    """
    return all_capabilities()

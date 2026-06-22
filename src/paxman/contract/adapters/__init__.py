"""Adapters subpackage — concrete :class:`ContractAdapter` implementations.

The V1 adapter set per ``ADR-0007``:

- :mod:`paxman.contract.adapters.dict_dsl` — Dict DSL (required, test source of truth).
- :mod:`paxman.contract.adapters.pydantic` — Pydantic v2 (required).
- :mod:`paxman.contract.adapters.json_schema` — JSON Schema draft 2020-12 (required).
- :mod:`paxman.contract.adapters.openapi` — OpenAPI 3.x (Sprint 4, best-effort).

Each adapter exposes a concrete class that satisfies the
:class:`ContractAdapter` Protocol (in :mod:`paxman.contract.adapters.base`).
Adapters self-register with the :mod:`paxman.contract.registry` on import.
"""

from __future__ import annotations

from paxman.contract.adapters.base import ContractAdapter

__all__ = ["ContractAdapter"]

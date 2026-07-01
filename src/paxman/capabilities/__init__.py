"""Capabilities subsystem — atomic, reusable operations.

This subsystem provides the **8 V1 capabilities** plus the runtime
machinery that makes them first-class:

- :mod:`paxman.capabilities.base` — :class:`Capability` Protocol
  (the SPI for adding new capabilities).
- :mod:`paxman.capabilities.spec` — :class:`CapabilitySpec` and
  :class:`CostHint` metadata.
- :mod:`paxman.capabilities.result` — :class:`CapabilityResult`,
  :class:`Candidate`, :class:`EvidenceRef`, :class:`Diagnostic`.
- :mod:`paxman.capabilities.registry` — versioned capability registry.
- :mod:`paxman.capabilities.v1` — concrete V1 capability implementations:
  the five V1.0.0 originals (``text_extraction``, ``regex_extraction``,
  ``validation``, ``lookup``, ``inference``) plus the three V1.1.0
  format-aware extraction additions (``json_path_extraction``,
  ``csv_extraction``, ``xpath_extraction``).

Boundary rules (per ``PACKAGE_STRUCTURE.md`` §5.4):

1. Capabilities **never** assign confidence (ADR-0005).
2. Capabilities are stateless and side-effect-free except for declared
   external effects (which MUST be captured in evidence).
3. Capabilities never read the canonical contract directly — they
   receive a :class:`~paxman.capabilities.base.CapabilityContext` built
   by the Executor.
4. Capabilities may NOT import from :mod:`paxman.planner`,
   :mod:`paxman.executor`, :mod:`paxman.reconciler`,
   :mod:`paxman.artifact`, or :mod:`paxman.api`.
"""

from __future__ import annotations

# Public surface of the capabilities subsystem (per PACKAGE_STRUCTURE.md §5.3).
# The actual re-exports are populated as the V1 capabilities land.

__all__: list[str] = []

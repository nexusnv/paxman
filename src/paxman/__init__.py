"""Paxman — contract-driven deterministic normalization engine for Python.

This is the public package entry point. The :mod:`paxman` module exposes a
small, stable surface:

- :data:`__version__` — the package version (PEP 440 / semver).
- Top-level functions ``normalize()`` and ``replay()`` land in Sprint 6.

Subsystems live in their own submodules and are **not** re-exported here:

- :mod:`paxman.contract` — adapter + validation boundary
- :mod:`paxman.planner` — field-centric plan synthesis
- :mod:`paxman.capabilities` — atomic operations (V1: ``text_extraction``,
  ``regex_extraction``, ``lookup``, ``inference``, ``validation``)
- :mod:`paxman.executor` — deterministic plan runner
- :mod:`paxman.reconciler` — sole confidence authority (ADR-0005)
- :mod:`paxman.artifact` — execution artifact + replay hash
- :mod:`paxman.api` — public surface (Sprint 6+)

Cross-cutting modules sit at the package root:

- :mod:`paxman.errors` — ``PaxmanError`` hierarchy
- :mod:`paxman.types` — shared enums (``Status``, ``ConfidenceBand``, ``FieldType``)
- :mod:`paxman.protocols` — internal ``Protocol`` definitions
- :mod:`paxman.versioning` — version constants and helpers
- :mod:`paxman.logging` — structlog factory
- :mod:`paxman.budget` — ``Budget`` / ``Policy`` / ``CurrencyPolicy``
- :mod:`paxman.clock` — injectable ``Clock`` + ``FakeClock``
- :mod:`paxman.ids` — prefixed ID helpers
- :mod:`paxman.serialization` — stable JSON encoder
"""

from paxman.versioning import __version__

__all__ = ["__version__"]

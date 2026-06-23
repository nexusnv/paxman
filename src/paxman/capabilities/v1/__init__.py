"""V1 capabilities package — concrete implementations of the 5 V1 capabilities.

V1 ships exactly these capabilities (per ``PACKAGE_STRUCTURE.md`` §12
and ``ARCHITECTURE.md`` §4.3):

- :mod:`paxman.capabilities.v1.text_extraction` — pull text from
  ``text/plain`` and ``text/html`` input.
- :mod:`paxman.capabilities.v1.regex_extraction` — pattern-based
  local extraction (deterministic).
- :mod:`paxman.capabilities.v1.lookup` — deterministic in-memory
  table lookup (Sprint 4).
- :mod:`paxman.capabilities.v1.inference` — model-backed extraction
  (LLM is a provider; Sprint 4 wires the lookup & inference real
  providers; this sprint ships only the SPI + stub).
- :mod:`paxman.capabilities.v1.validation` — verify a candidate
  value against a constraint (deterministic).

In Sprint 3 we ship the first three (text_extraction, regex_extraction,
validation) plus the inference SPI + stub provider. ``lookup`` is
Sprint 4 work.

Boundary rules
--------------

Per ``PACKAGE_STRUCTURE.md`` §2, no subsystem may import
``paxman.capabilities.v1.*`` directly — the
:mod:`paxman.capabilities.registry` is the only entry point. This
keeps the planner decoupled from the concrete implementations.
"""

from __future__ import annotations

__all__: list[str] = []

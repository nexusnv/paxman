"""V1 capabilities package — concrete implementations of the 5 V1 capabilities.

V1 ships exactly these capabilities (per ``PACKAGE_STRUCTURE.md`` §12
and ``ARCHITECTURE.md`` §4.3):

- :mod:`paxman.capabilities.v1.text_extraction` — pull text from
  ``text/plain`` and ``text/html`` input.
- :mod:`paxman.capabilities.v1.regex_extraction` — pattern-based
  local extraction (deterministic).
- :mod:`paxman.capabilities.v1.lookup` — deterministic in-memory
  table lookup.
- :mod:`paxman.capabilities.v1.inference` — model-backed extraction
  (LLM is a provider; includes the SPI, a stub provider, and the
  ``CyclingStubInferenceProvider`` for non-determinism testing).
- :mod:`paxman.capabilities.v1.validation` — verify a candidate
  value against a constraint (deterministic).

The first three capabilities (text_extraction, regex_extraction,
validation) plus the inference SPI and stub provider ship initially;
``lookup`` follows.

Boundary rules
--------------

Per ``PACKAGE_STRUCTURE.md`` §2, no subsystem may import
``paxman.capabilities.v1.*`` directly — the
:mod:`paxman.capabilities.registry` is the only entry point. This
keeps the planner decoupled from the concrete implementations.
"""

from __future__ import annotations

# Importing the v1 modules triggers their ``_register_on_import``
# hooks, which register the capabilities with the global
# capability registry. This is the V1 convention: capabilities
# self-register on import.
from paxman.capabilities.v1 import (
    inference,
    lookup,
    regex_extraction,
    text_extraction,
    validation,
)

__all__: list[str] = [
    "inference",
    "lookup",
    "regex_extraction",
    "text_extraction",
    "validation",
]

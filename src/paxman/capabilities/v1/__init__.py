"""V1 capabilities package — concrete implementations of the V1 capabilities.

V1 ships these capabilities (per ``PACKAGE_STRUCTURE.md`` §12
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

V1.1.0 additions (sub-issues of #67; see #68, #69, and #70):

- :mod:`paxman.capabilities.v1.json_path_extraction` — extract
  values from a JSON document via JSON-Pointer or a limited
  JSONPath subset.
- :mod:`paxman.capabilities.v1.csv_extraction` — extract values
  from a CSV document for a named or indexed column.
- :mod:`paxman.capabilities.v1.xpath_extraction` — extract values
  from an XML/HTML document via a documented subset of XPath.
- :mod:`paxman.capabilities.v1.case_normalization` — case-transform
  a pre-resolved string value (``lower`` / ``upper`` / ``title`` /
  ``preserve``).
- :mod:`paxman.capabilities.v1.trim_extraction` — strip leading
  and trailing whitespace + common punctuation from a pre-resolved
  string value.

Registration contract (per ADR-0012)
-----------------------------------

**All V1 built-in capabilities self-register on import.** Each V1
module ends with a ``_register_on_import()`` hook that calls
``paxman.capabilities.registry.register(<Capability>(), replace=True)``
at module load time, so importing this package populates the global
capability registry with the V1 built-in surface (the **ten** V1
capabilities: the five V1.0.0 originals — ``text_extraction``,
``regex_extraction``, ``lookup``, ``inference``, ``validation`` —
plus the three V1.1.0 format-aware extraction additions —
``json_path_extraction``, ``csv_extraction``, ``xpath_extraction`` —
plus the two V1.1.0 post-extraction cleanup transforms —
``case_normalization``, ``trim_extraction``).

This is symmetric with the contract adapter side: the four built-in
adapters (``pydantic``, ``json_schema``, ``dict_dsl``, ``openapi``)
also self-register on import (see the corresponding
``_register_on_import()`` hooks in
``src/paxman/contract/adapters/*.py``).

Third-party capabilities — anything outside the V1 built-in set —
use :func:`paxman.register_capability` (the public SPI in
``src/paxman/api/registry.py``). See ``docs/reference/extending.md``
§2.3 for the extension guide.

The :func:`~paxman.capabilities.registry._bootstrap_v1_capabilities`
helper re-registers the V1 capabilities after a
:func:`~paxman.capabilities.registry.reset` call (used by test
fixtures).

Boundary rules
--------------

Per ``PACKAGE_STRUCTURE.md`` §2, no subsystem may import
``paxman.capabilities.v1.*`` directly — the
:mod:`paxman.capabilities.registry` is the only entry point. This
keeps the planner decoupled from the concrete implementations.
"""

from __future__ import annotations

# Importing the v1 modules triggers their ``_register_on_import``
# hooks, which register all V1 built-in capabilities with the global
# capability registry (per ADR-0012). This is the V1 convention:
# built-in capabilities self-register on import, symmetric with
# the contract adapter side. Third-party capabilities use
# ``paxman.register_capability()``.
from paxman.capabilities.v1 import (
    case_normalization,
    csv_extraction,
    inference,
    json_path_extraction,
    lookup,
    regex_extraction,
    text_extraction,
    trim_extraction,
    validation,
    xpath_extraction,
)

__all__: list[str] = [
    "case_normalization",
    "csv_extraction",
    "inference",
    "json_path_extraction",
    "lookup",
    "regex_extraction",
    "text_extraction",
    "trim_extraction",
    "validation",
    "xpath_extraction",
]

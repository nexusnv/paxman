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

V1.1.0 additions (sub-issues of #67; see #68 and #70):

- :mod:`paxman.capabilities.v1.json_path_extraction` — extract
  values from a JSON document via JSON-Pointer or a limited
  JSONPath subset.
- :mod:`paxman.capabilities.v1.csv_extraction` — extract values
  from a CSV document for a named or indexed column.
- :mod:`paxman.capabilities.v1.xpath_extraction` — extract values
  from an XML/HTML document via a documented subset of XPath.

Registration
------------

Per the V1 registry contract (see :mod:`paxman.capabilities.registry`),
**only** ``lookup`` self-registers on import (its module invokes
``registry.register`` at the bottom of the file). All other v1
capabilities — including the V1.1.0 additions — are **not**
self-registering; callers register them explicitly via
:func:`paxman.capabilities.registry.register` or
:func:`paxman.register_capability`. The :mod:`paxman.capabilities.v1`
package imports the modules for **type resolution / importability
only**, not for registration. This is documented in the
``_bootstrap_v1_capabilities`` docstring at
``registry.py:246-251``.

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

# Importing the v1 modules makes the capability classes importable
# via ``paxman.capabilities.v1.<name>``. Registration with the global
# registry is *not* triggered by these imports for any module other
# than ``lookup`` (which self-registers at the bottom of its file).
# See the module docstring above for the full registration contract.
from paxman.capabilities.v1 import (
    csv_extraction,
    inference,
    json_path_extraction,
    lookup,
    regex_extraction,
    text_extraction,
    validation,
    xpath_extraction,
)

__all__: list[str] = [
    "csv_extraction",
    "inference",
    "json_path_extraction",
    "lookup",
    "regex_extraction",
    "text_extraction",
    "validation",
    "xpath_extraction",
]

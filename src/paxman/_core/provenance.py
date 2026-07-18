"""Re-export shim for the legacy ``paxman._core.provenance`` path.

The structured-provenance model now lives in ``paxman._provenance``
(mandate Law 14: ``Authority`` + ``Evidence.authority``). This module
re-exports ``Evidence`` and the shared ``_evidence`` helper so existing
imports from ``paxman._core.provenance`` keep working through the
transition. New code should import from ``paxman._provenance`` directly.
"""

from __future__ import annotations

from paxman._provenance import Evidence, _evidence

__all__ = ["Evidence", "_evidence"]

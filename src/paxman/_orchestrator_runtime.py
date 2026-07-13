"""The module-level default registry used by paxman.canonicalize.

Held in a dedicated module to avoid a circular import between the
orchestrator (which uses the registry) and `paxman/__init__.py` (which
calls the orchestrator and exposes the user-facing
`register_capability`).
"""

from __future__ import annotations

from paxman._capabilities.registry import CapabilityRegistry

# The default, module-level registry. Frozen implicitly on the first
# canonicalize call (see _core/orchestrator.py).
default_registry: CapabilityRegistry = CapabilityRegistry()

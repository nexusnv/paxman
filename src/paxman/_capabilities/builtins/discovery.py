"""Built-in capability discovery for Paxman v2.

MANDATE §4.3: built-in capabilities stay in core (like Carbon ships
with all parsers in one package). This module is the single source of
truth for "what built-ins does this version ship?"

Law 8a: importing this module has NO side effect. The built-ins are
NOT registered at import time. The orchestrator calls
builtin_capabilities() + registry.load_builtins() lazily on the first
canonicalize call, never at 'import paxman' time.

This module lives in `discovery.py` rather than `__init__.py` to keep
`paxman._capabilities.builtins` an empty package marker (per
PROPOSED_STRUCTURE.md). The `__init__.py` is the package's public
import path; `discovery.py` is the implementation.
"""

from __future__ import annotations

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.protocol import Capability


def builtin_capabilities() -> list[Capability]:
    """Return the list of built-in capability instances Paxman ships with.

    MANDATE §4.3: built-ins stay in core. This list is the single
    source of truth for "what built-ins does this version ship?" The
    orchestrator loads them lazily on the first canonicalize call
    (Law 8a: no import-time side effects).

    Returns:
        A fresh list of fresh capability instances on every call. No
        shared mutable state (Law 1, Law 8a).
    """
    return [EmailCapability()]

"""Built-in capabilities subpackage.

This subpackage ships the built-in capabilities Paxman v2 provides out
of the box (mandate §4.3). The discovery helper that lists them lives
in `paxman._capabilities.builtins.discovery`; the actual capability
implementations live in their own submodules (e.g. `paxman._capabilities
.builtins.email`).

Per PROPOSED_STRUCTURE.md, this `__init__.py` is intentionally empty so
that the package is just a namespace marker; nothing is exported at
import time (Law 8a: no import-time side effects).
"""

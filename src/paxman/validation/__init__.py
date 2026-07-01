"""Paxman validation helpers (subsystem-internal).

This package is **not** part of the public API. It exists to break the
historical layering violation in which the reconciler imported a private
helper (``_check_constraint``) from :mod:`paxman.capabilities.v1.validation`.

The boundary rule in :mod:`paxman.capabilities.v1.__init__` (per
``PACKAGE_STRUCTURE.md`` §2) states that no subsystem may import from
``paxman.capabilities.v1.*`` directly. Both the capability and the
reconciler now depend on :func:`paxman.validation.constraints.check_constraint`,
which is a thin wrapper around the original helper.
"""
from __future__ import annotations

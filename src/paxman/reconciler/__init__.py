"""Reconciler subsystem — truth resolution.

The Reconciler is the **sole confidence authority** (`ADR-0005`). It takes
:class:`~paxman.executor.field_runner.CandidateResult` records from the
Executor and a :class:`~paxman.contract.canonical.CanonicalContract`, and
produces one :class:`~paxman.reconciler.truth.ResolvedResult` per field.

This is the V1 surface; the full set of internal modules is documented
in ``PACKAGE_STRUCTURE.md`` §7.2.
"""

from paxman.reconciler.reconciler import reconcile
from paxman.reconciler.truth import ResolvedResult, TruthLayer

__all__ = ["ResolvedResult", "TruthLayer", "reconcile"]

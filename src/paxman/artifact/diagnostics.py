"""Artifact-level diagnostic collection.

This module defines the :class:`DiagnosticStore` that aggregates
diagnostics from the planner, capabilities, executor, and reconciler
into a single ordered collection embedded in the artifact.

The :class:`Diagnostic` and :class:`DiagnosticCode` types themselves
live in :mod:`paxman.capabilities.result`; this module provides
the aggregation layer and higher-level artifact diagnostics.
"""

from __future__ import annotations

import attrs

from paxman.capabilities.result import Diagnostic, DiagnosticCode, DiagnosticSeverity

__all__ = [
    "DiagnosticStore",
]


@attrs.frozen(slots=True)
class DiagnosticStore:
    """A frozen collection of :class:`Diagnostic` notes.

    Aggregates diagnostics from all pipeline stages (planner, capabilities,
    executor, reconciler) in chronological order.

    Attributes:
        notes: Tuple of :class:`Diagnostic` records.
    """

    notes: tuple[Diagnostic, ...] = ()

    def by_severity(self, severity: DiagnosticSeverity) -> tuple[Diagnostic, ...]:
        """Return all diagnostics with a given severity.

        Args:
            severity: The :class:`DiagnosticSeverity` to filter by.

        Returns:
            Tuple of matching :class:`Diagnostic` records.
        """
        return tuple(d for d in self.notes if d.severity == severity)

    def by_code(self, code: DiagnosticCode) -> tuple[Diagnostic, ...]:
        """Return all diagnostics with a given code.

        Args:
            code: The :class:`DiagnosticCode` to filter by.

        Returns:
            Tuple of matching :class:`Diagnostic` records.
        """
        return tuple(d for d in self.notes if d.code == code)

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        """Return only ERROR-severity diagnostics.

        Returns:
            Tuple of ERROR :class:`Diagnostic` records.
        """
        return self.by_severity(DiagnosticSeverity.ERROR)

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        """Return only WARNING-severity diagnostics.

        Returns:
            Tuple of WARNING :class:`Diagnostic` records.
        """
        return self.by_severity(DiagnosticSeverity.WARNING)

"""Evidence storage — frozen collection of provenance from capability invocations.

This module defines the :class:`EvidenceStore`, a frozen container
of :class:`EvidenceRef` records collected during execution and
surfaced in the artifact.

The :class:`EvidenceRef` type itself lives in
:mod:`paxman.capabilities.result`; this module provides the
aggregation and querying layer.
"""

from __future__ import annotations

import attrs

from paxman.capabilities.result import EvidenceRef

__all__ = [
    "EvidenceStore",
]


@attrs.frozen(slots=True)
class EvidenceStore:
    """A frozen collection of :class:`EvidenceRef` provenance records.

    The :class:`EvidenceStore` is built during execution by collecting
    :class:`EvidenceRef` records from each capability invocation. It is
    frozen after execution completes and embedded in the artifact.

    Attributes:
        records: Tuple of :class:`EvidenceRef` provenance records,
            in insertion order.
    """

    records: tuple[EvidenceRef, ...] = ()

    def by_field(self, field_path: str) -> tuple[EvidenceRef, ...]:
        """Return all evidence references for a given field path.

        Args:
            field_path: The canonical field path to filter by.

        Returns:
            Tuple of :class:`EvidenceRef` matching the field path.
        """
        return tuple(r for r in self.records if r.field_path == field_path)

    def by_capability(self, capability_id: str) -> tuple[EvidenceRef, ...]:
        """Return all evidence references from a given capability.

        Args:
            capability_id: The capability id (e.g., ``"regex_extraction"``).

        Returns:
            Tuple of :class:`EvidenceRef` from that capability.
        """
        return tuple(r for r in self.records if r.capability_id == capability_id)

    @property
    def field_paths(self) -> tuple[str, ...]:
        """Return the distinct field paths referenced in this store.

        Returns:
            Sorted tuple of unique field paths.
        """
        return tuple(sorted({r.field_path for r in self.records}))

    @property
    def capability_ids(self) -> tuple[str, ...]:
        """Return the distinct capability IDs referenced in this store.

        Returns:
            Sorted tuple of unique capability ids.
        """
        return tuple(sorted({r.capability_id for r in self.records}))

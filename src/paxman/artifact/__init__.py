"""Execution artifact subsystem — the product + replay source.

The artifact subsystem builds the :class:`ExecutionArtifact` that
:func:`paxman.normalize` returns and that :func:`paxman.replay`
rehydrates from.
"""

from paxman.artifact.artifact import ExecutionArtifact, FieldResult

__all__ = [
    "ExecutionArtifact",
    "FieldResult",
]

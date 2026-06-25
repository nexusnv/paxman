"""SHA-256 replay hash computation for :class:`ExecutionArtifact`.

Per ``REPLAY_AND_DETERMINISM.md`` §2.1, the replay hash is a deterministic
SHA-256 digest computed over the artifact's hash-relevant fields:

- ``paxman_version``
- ``planner_version``
- ``replay_version`` (constant ``"1"``)
- ``execution_plan`` (serialised)
- ``field_results`` (sorted by ``field_path``, serialised)
- ``evidence`` (serialised)
- ``diagnostics`` (serialised)
- ``statistics`` (serialised)
- ``contract_id``
- ``capability_versions`` (keys sorted, then serialised)

The hash is **not** a signature over the entire serialised artifact —
only the fields that capture the resolved truth.  Fields such as ``id``,
``created_at``, and ``metadata`` are excluded because they may
legitimately differ across rehydrations.
"""

from __future__ import annotations

import hashlib
import typing

from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.serialization import stable_dumps
from paxman.versioning import REPLAY_VERSION

__all__: list[str] = [
    "REPLAY_VERSION",
    "compute_replay_hash",
]


def compute_replay_hash(artifact: ExecutionArtifact) -> str:
    """Compute the SHA-256 replay hash for an artifact.

    The hash is computed by:

    1. Serialising each hash-relevant field with :func:`stable_dumps`.
    2. Concatenating the results with ``|`` separator.
    3. Taking the SHA-256 digest of the UTF-8 encoded bytes.

    Hash-relevant fields (per ``REPLAY_AND_DETERMINISM.md`` §2.1):

    - ``paxman_version``
    - ``planner_version``
    - ``replay_version`` (constant ``"1"``)
    - ``execution_plan`` (serialised; ``"null"`` if ``None``)
    - ``field_results`` (sorted by field path, serialised)
    - ``evidence`` (serialised)
    - ``diagnostics`` (serialised)
    - ``statistics`` (serialised)
    - ``contract_id``
    - ``capability_versions`` (keys sorted, then serialised)

    Args:
        artifact: The :class:`ExecutionArtifact` to hash.

    Returns:
        A 64-character lowercase hex string (SHA-256 digest).

    Examples:
        >>> from paxman.artifact.artifact import ExecutionArtifact
        >>> from paxman.types import Status
        >>> art = ExecutionArtifact(status=Status.UNRESOLVED)
        >>> h = compute_replay_hash(art)
        >>> len(h)
        64
        >>> all(c in "0123456789abcdef" for c in h)
        True
    """
    parts: list[str] = [
        # 1. paxman_version
        stable_dumps(artifact.paxman_version),
        # 2. planner_version
        stable_dumps(artifact.planner_version),
        # 3. replay_version (constant)
        stable_dumps(REPLAY_VERSION),
        # 4. execution_plan (serialised; "null" if None)
        stable_dumps(artifact.execution_plan),
        # 5. field_results (sorted by field_path)
        _serialize_field_results(artifact.field_results),
        # 6. evidence
        stable_dumps(artifact.evidence),
        # 7. diagnostics
        stable_dumps(artifact.diagnostics),
        # 8. statistics
        stable_dumps(artifact.statistics),
        # 9. contract_id
        stable_dumps(artifact.contract_id),
        # 10. capability_versions (keys sorted, then serialised)
        stable_dumps(_sorted_dict(artifact.capability_versions)),
    ]

    raw: str = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


_VT = typing.TypeVar("_VT")


def _sorted_dict(data: dict[str, _VT]) -> dict[str, _VT]:
    """Return a new dict with keys sorted alphabetically.

    Args:
        data: The input dictionary.

    Returns:
        A new dictionary with the same items but sorted keys.
    """
    return dict(sorted(data.items()))


def _serialize_field_results(
    field_results: dict[str, FieldResult],
) -> str:
    """Serialise ``field_results`` with keys sorted by ``field_path``.

    Sorting is performed on the dict keys (which are field paths), ensuring
    deterministic serialisation regardless of insertion order.

    Args:
        field_results: The artifact's ``field_results`` mapping.

    Returns:
        A deterministic JSON string with keys sorted alphabetically.
    """
    return stable_dumps(_sorted_dict(field_results))

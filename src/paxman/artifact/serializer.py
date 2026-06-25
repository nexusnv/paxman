"""Stable JSON encoding/decoding for :class:`ExecutionArtifact`.

This module provides deterministic serialisation and deserialisation
of :class:`ExecutionArtifact` instances using the cross-cutting
:mod:`paxman.serialization` module (RFC 8785-style JSON).

Per the sprint risk register, all JSON encoding **must** delegate to
:func:`paxman.serialization.stable_dumps` and
:func:`paxman.serialization.stable_loads` — no alternative JSON
implementation is permitted.
"""

from __future__ import annotations

import typing

import attrs

from paxman.artifact.artifact import ExecutionArtifact
from paxman.serialization import stable_dumps, stable_loads

__all__: list[str] = [
    "decode_artifact",
    "encode_artifact",
]


def encode_artifact(artifact: ExecutionArtifact) -> str:
    """Serialize an :class:`ExecutionArtifact` to a deterministic JSON string.

    Delegates to :func:`paxman.serialization.stable_dumps` on the artifact's
    attrs-as-dict representation.  The resulting JSON is deterministic (sorted
    keys, compact encoding) and suitable for hash computation and replay.

    Args:
        artifact: The :class:`ExecutionArtifact` to serialize.

    Returns:
        An RFC 8785-style JSON string with sorted keys and compact encoding.

    Examples:
        >>> from paxman.artifact.artifact import ExecutionArtifact
        >>> from paxman.types import Status
        >>> art = ExecutionArtifact(status=Status.UNRESOLVED)
        >>> isinstance(encode_artifact(art), str)
        True
    """
    raw: dict[str, typing.Any] = attrs.asdict(artifact)
    return stable_dumps(raw)


def decode_artifact(json_str: str) -> dict[str, typing.Any]:
    """Deserialize a JSON string back to a Python dictionary.

    Calls :func:`paxman.serialization.stable_loads` on the input string.
    The returned dictionary can be used to reconstruct an
    :class:`ExecutionArtifact` via the attrs constructor.

    Args:
        json_str: A JSON string produced by :func:`encode_artifact`.

    Returns:
        A dictionary representing the artifact's fields and values.  The
        caller may pass this as ``**kwargs`` to the
        :class:`ExecutionArtifact` constructor.

    Raises:
        json.JSONDecodeError: If *json_str* is malformed.
        TypeError: If the decoded JSON is not a dictionary
            (e.g. a JSON array or primitive).

    Examples:
        >>> from paxman.artifact.artifact import ExecutionArtifact
        >>> from paxman.types import Status
        >>> art = ExecutionArtifact(status=Status.UNRESOLVED)
        >>> json_str = encode_artifact(art)
        >>> decoded = decode_artifact(json_str)
        >>> isinstance(decoded, dict)
        True
    """
    result: object = stable_loads(json_str)
    if not isinstance(result, dict):
        raise TypeError(
            f"decode_artifact expected a JSON object (dict), got {type(result).__name__}"
        )
    return typing.cast(dict[str, typing.Any], result)

"""Stable JSON encoder (RFC 8785-style).

Provides deterministic JSON serialization with sorted keys and compact
encoding. Used for replay hash computation and artifact serialization.
"""

from __future__ import annotations

import datetime
import decimal
import enum
import json
import types
import typing
import uuid
from typing import IO

import attrs

__all__: list[str] = [
    "stable_dump",
    "stable_dumps",
    "stable_load",
    "stable_loads",
]


def _default(obj: object) -> object:
    """Convert non-JSON-serializable types to JSON-compatible representations.

    Args:
        obj: Object to convert.

    Returns:
        JSON-serializable representation of the object.

    Raises:
        TypeError: If the object type is not supported.
    """
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return obj.hex
    if isinstance(obj, (bytes, bytearray)):
        return "0x" + obj.hex()
    if isinstance(obj, enum.Enum):
        return obj.value
    if attrs.has(type(obj)):
        return attrs.asdict(typing.cast(attrs.AttrsInstance, obj))
    if isinstance(obj, (set, frozenset)):
        return sorted(obj, key=repr)
    if isinstance(obj, types.MappingProxyType):
        return dict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def stable_dumps(obj: object) -> str:
    """Serialize an object to a deterministic JSON string.

    Produces byte-identical output for identical input: sorted keys at every
    nesting level, compact encoding (no whitespace), and custom handling for
    Decimal, datetime, UUID, bytes, Enum, attrs, and set types.

    Args:
        obj: Object to serialize.

    Returns:
        Deterministic JSON string.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default)


def stable_loads(s: str) -> object:
    """Deserialize a JSON string.

    Standard ``json.loads`` wrapper for symmetry with :func:`stable_dumps`.

    Args:
        s: JSON string to deserialize.

    Returns:
        Deserialized Python object.
    """
    return json.loads(s)


def stable_dump(obj: object, fp: IO[str]) -> None:
    """Serialize an object to a deterministic JSON stream.

    Args:
        obj: Object to serialize.
        fp: Writable file-like object.
    """
    fp.write(stable_dumps(obj))


def stable_load(fp: IO[str]) -> object:
    """Deserialize a JSON stream.

    Args:
        fp: Readable file-like object.

    Returns:
        Deserialized Python object.
    """
    return json.load(fp)

"""Prefixed ID helpers for paxman's internal identifiers.

Each subsystem uses a distinct prefix so that IDs are self-describing
at a glance and sortable by prefix in logs and artifacts.

This module is a **leaf** in the import DAG — it imports nothing from
``paxman.*`` submodules.

Prefixes
--------
- ``field_`` — :class:`~paxman.contract.CanonicalField` IDs.
- ``cap_``   — Capability IDs.
- ``art_``   — :class:`~paxman.artifact.ExecutionArtifact` IDs.
- ``plan_``  — :class:`~paxman.planner.ExecutionPlan` IDs.

The prefix scheme is part of the public artifact format, so it **must**
remain stable across minor versions.
"""

from __future__ import annotations

import typing
import uuid

# ---------------------------------------------------------------------------
# Prefix constants
# ---------------------------------------------------------------------------

FIELD_PREFIX: typing.Final[str] = "field_"
"""Prefix for :class:`~paxman.contract.CanonicalField` IDs."""

CAPABILITY_PREFIX: typing.Final[str] = "cap_"
"""Prefix for capability IDs."""

ARTIFACT_PREFIX: typing.Final[str] = "art_"
"""Prefix for :class:`~paxman.artifact.ExecutionArtifact` IDs."""

PLAN_PREFIX: typing.Final[str] = "plan_"
"""Prefix for :class:`~paxman.planner.ExecutionPlan` IDs."""

_SUFFIX_LENGTH: typing.Final[int] = 12
"""Number of hex characters in the random suffix (48 bits of entropy)."""

# ---------------------------------------------------------------------------
# Generation functions
# ---------------------------------------------------------------------------


def generate_field_id() -> str:
    """Generate a new FieldId.

    Returns:
        A prefixed ID such as ``field_a1b2c3d4e5f6``.

    Example::

        >>> fid = generate_field_id()
        >>> fid.startswith(FIELD_PREFIX)
        True
    """
    return f"{FIELD_PREFIX}{uuid.uuid4().hex[:_SUFFIX_LENGTH]}"


def generate_capability_id() -> str:
    """Generate a new CapabilityId.

    Returns:
        A prefixed ID such as ``cap_a1b2c3d4e5f6``.

    Example::

        >>> cid = generate_capability_id()
        >>> cid.startswith(CAPABILITY_PREFIX)
        True
    """
    return f"{CAPABILITY_PREFIX}{uuid.uuid4().hex[:_SUFFIX_LENGTH]}"


def generate_artifact_id() -> str:
    """Generate a new ArtifactId.

    Returns:
        A prefixed ID such as ``art_a1b2c3d4e5f6``.

    Example::

        >>> aid = generate_artifact_id()
        >>> aid.startswith(ARTIFACT_PREFIX)
        True
    """
    return f"{ARTIFACT_PREFIX}{uuid.uuid4().hex[:_SUFFIX_LENGTH]}"


def generate_plan_id() -> str:
    """Generate a new PlanId.

    Returns:
        A prefixed ID such as ``plan_a1b2c3d4e5f6``.

    Example::

        >>> pid = generate_plan_id()
        >>> pid.startswith(PLAN_PREFIX)
        True
    """
    return f"{PLAN_PREFIX}{uuid.uuid4().hex[:_SUFFIX_LENGTH]}"


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


def is_field_id(value: str) -> bool:
    """Return ``True`` if *value* matches the FieldId prefix pattern.

    Args:
        value: The string to test.

    Returns:
        Whether *value* has the ``field_`` prefix and correct total length.

    Example::

        >>> is_field_id("field_a1b2c3d4e5f6")
        True
        >>> is_field_id("cap_a1b2c3d4e5f6")
        False
    """
    return value.startswith(FIELD_PREFIX) and len(value) == len(FIELD_PREFIX) + _SUFFIX_LENGTH


def is_capability_id(value: str) -> bool:
    """Return ``True`` if *value* matches the CapabilityId prefix pattern.

    Args:
        value: The string to test.

    Returns:
        Whether *value* has the ``cap_`` prefix and correct total length.

    Example::

        >>> is_capability_id("cap_a1b2c3d4e5f6")
        True
    """
    return (
        value.startswith(CAPABILITY_PREFIX)
        and len(value) == len(CAPABILITY_PREFIX) + _SUFFIX_LENGTH
    )


def is_artifact_id(value: str) -> bool:
    """Return ``True`` if *value* matches the ArtifactId prefix pattern.

    Args:
        value: The string to test.

    Returns:
        Whether *value* has the ``art_`` prefix and correct total length.

    Example::

        >>> is_artifact_id("art_a1b2c3d4e5f6")
        True
    """
    return value.startswith(ARTIFACT_PREFIX) and len(value) == len(ARTIFACT_PREFIX) + _SUFFIX_LENGTH


def is_plan_id(value: str) -> bool:
    """Return ``True`` if *value* matches the PlanId prefix pattern.

    Args:
        value: The string to test.

    Returns:
        Whether *value* has the ``plan_`` prefix and correct total length.

    Example::

        >>> is_plan_id("plan_a1b2c3d4e5f6")
        True
    """
    return value.startswith(PLAN_PREFIX) and len(value) == len(PLAN_PREFIX) + _SUFFIX_LENGTH


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_ALL_PREFIXES: tuple[str, ...] = (
    FIELD_PREFIX,
    CAPABILITY_PREFIX,
    ARTIFACT_PREFIX,
    PLAN_PREFIX,
)


def parse_id(value: str) -> tuple[str, str]:
    """Parse a prefixed ID into ``(prefix, suffix)``.

    Args:
        value: A prefixed ID string (e.g., ``field_a1b2c3d4e5f6``).

    Returns:
        A ``(prefix, suffix)`` tuple where *prefix* is one of the four
        known prefixes and *suffix* is the 12-hex-character random part.

    Raises:
        ValueError: If *value* does not match any known prefix.

    Example::

        >>> parse_id("field_a1b2c3d4e5f6")
        ('field_', 'a1b2c3d4e5f6')
    """
    for prefix in _ALL_PREFIXES:
        if value.startswith(prefix):
            suffix = value[len(prefix) :]
            if len(suffix) == _SUFFIX_LENGTH:
                return prefix, suffix
    msg = f"Unrecognised ID format: {value!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "ARTIFACT_PREFIX",
    "CAPABILITY_PREFIX",
    "FIELD_PREFIX",
    "PLAN_PREFIX",
    # Generation
    "generate_artifact_id",
    "generate_capability_id",
    "generate_field_id",
    "generate_plan_id",
    # Validation
    "is_artifact_id",
    "is_capability_id",
    "is_field_id",
    "is_plan_id",
    # Parsing
    "parse_id",
]

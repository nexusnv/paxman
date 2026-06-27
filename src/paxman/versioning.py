"""Version constants and helpers.

This module provides:

- Library version constants that mirror ``pyproject.toml``.
- Internal format-version constants for the planner, replay, and contract
  subsystems (bumped independently when their wire formats change).
- Utility functions to parse, format, compare, and bump semver strings.

Design constraints
------------------
- Leaf module: no imports from any ``paxman.*`` submodule.
- Every public symbol is listed in ``__all__``.
- 100 % line-coverage target.
- Deterministic: no I/O, no clock, no random, no global mutable state.
"""

from __future__ import annotations

import typing

# ---------------------------------------------------------------------------
# Version constants (all strings, all Final)
# ---------------------------------------------------------------------------

#: Library version — mirrors ``pyproject.toml [project].version``.
__version__: str = "1.0.0"

#: Canonical library version constant for internal use and artifact metadata.
PAXMAN_VERSION: typing.Final[str] = __version__

#: Planner algorithm version. Bumped when the planner algorithm changes in a
#: way that affects produced ``FieldPlan`` objects.
PLANNER_VERSION: typing.Final[str] = "1"

#: Replay (de)hydration format version. Bumped when the artifact wire format
#: changes in a way that breaks backward compatibility.
REPLAY_VERSION: typing.Final[str] = "1"

#: Contract schema format version (the ``CanonicalContract`` format itself).
CONTRACT_FORMAT_VERSION: typing.Final[str] = "1"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "CONTRACT_FORMAT_VERSION",
    "PAXMAN_VERSION",
    "PLANNER_VERSION",
    "REPLAY_VERSION",
    "__version__",
    "bump_version",
    "check_version_compatibility",
    "format_version",
    "parse_version",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse a semver string into a 3-tuple of ints.

    Accepts strings of the form ``"MAJOR.MINOR.PATCH"`` with an optional
    leading ``v`` prefix (e.g. ``"v1.2.3"``).  Pre-release suffixes and
    build metadata are **not** supported in V1 and will cause a
    :class:`ValueError`.

    Args:
        version: A semver string such as ``"1.2.3"`` or ``"v0.1.0"``.

    Returns:
        A ``(major, minor, patch)`` tuple of non-negative integers.

    Raises:
        ValueError: If *version* does not match the expected format —
            wrong number of parts, non-integer segments, negative values,
            leading-zero padding (e.g. ``"01"``), or pre-release suffixes.

    Examples:
        >>> parse_version("0.0.0")
        (0, 0, 0)
        >>> parse_version("v1.2.3")
        (1, 2, 3)
    """
    # Strip an optional leading "v" / "V".
    cleaned = version.strip()
    if cleaned.startswith(("v", "V")):
        cleaned = cleaned[1:]

    parts = cleaned.split(".")
    if len(parts) != 3:
        raise ValueError(
            f"Expected exactly 3 dot-separated parts (MAJOR.MINOR.PATCH), "
            f"got {len(parts)}: {version!r}"
        )

    result: list[int] = []
    for part in parts:
        # Reject empty segments, leading zeros (except "0" itself), and
        # anything that isn't purely digits.
        if not part:
            raise ValueError(f"Empty segment in version string: {version!r}")
        if not part.isdigit():
            raise ValueError(f"Non-integer segment {part!r} in version string: {version!r}")
        if len(part) > 1 and part.startswith("0"):
            raise ValueError(f"Leading zero in segment {part!r} of version string: {version!r}")
        result.append(int(part))

    return (result[0], result[1], result[2])


def format_version(major: int, minor: int, patch: int) -> str:
    """Format a ``(major, minor, patch)`` triple into a semver string.

    Each component must be a non-negative integer.

    Args:
        major: Major version number (≥ 0).
        minor: Minor version number (≥ 0).
        patch: Patch version number (≥ 0).

    Returns:
        A string of the form ``"MAJOR.MINOR.PATCH"``.

    Raises:
        ValueError: If any component is not an ``int`` (e.g., ``bool``,
            ``float``, ``str``) or is a negative integer.

    Examples:
        >>> format_version(1, 2, 3)
        '1.2.3'
        >>> format_version(0, 0, 0)
        '0.0.0'
    """
    for name, value in [("major", major), ("minor", minor), ("patch", patch)]:
        if type(value) is not int:  # explicit type check rejects bool
            raise ValueError(f"{name} must be an int, got {type(value).__name__}: {value!r}")
        if value < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {value}")
    return f"{major}.{minor}.{patch}"


def check_version_compatibility(
    artifact_version: str,
    current_version: str = PAXMAN_VERSION,
) -> bool:
    """Check whether an artifact can be replayed on the current version.

    The compatibility rule follows ARCHITECTURE.md §16.1:

    1. Same major version **and** current ≥ artifact → compatible.
    2. Different major version → incompatible.
    3. Same major but artifact is newer than current → incompatible
       (forward compatibility is not guaranteed in V1).

    Args:
        artifact_version: The semver string recorded in the artifact.
        current_version: The running library version.  Defaults to
            :data:`PAXMAN_VERSION`.

    Returns:
        ``True`` if the artifact is compatible, ``False`` otherwise.

    Examples:
        >>> check_version_compatibility("0.0.0", "0.0.0")
        True
        >>> check_version_compatibility("0.0.0", "0.1.0")
        True
        >>> check_version_compatibility("0.1.0", "0.0.0")
        False
    """
    art = parse_version(artifact_version)
    cur = parse_version(current_version)

    # Different major → incompatible.
    if art[0] != cur[0]:
        return False

    # Artifact is from the future → incompatible.
    if art > cur:
        return False

    return True


def bump_version(
    version: str,
    level: typing.Literal["major", "minor", "patch"],
) -> str:
    """Bump a semver string at the specified level.

    Args:
        version: The current semver string (e.g. ``"1.2.3"``).
        level: Which component to increment — ``"major"``, ``"minor"``, or
            ``"patch"``.

    Returns:
        The new version string with the appropriate component incremented
        and lower components reset to zero.

    Raises:
        ValueError: If *level* is not one of the three accepted literals,
            or if *version* cannot be parsed.

    Examples:
        >>> bump_version("0.0.0", "patch")
        '0.0.1'
        >>> bump_version("0.0.0", "minor")
        '0.1.0'
        >>> bump_version("0.0.0", "major")
        '1.0.0'
        >>> bump_version("1.2.3", "patch")
        '1.2.4'
    """
    major, minor, patch = parse_version(version)

    if level == "major":
        return format_version(major + 1, 0, 0)
    if level == "minor":
        return format_version(major, minor + 1, 0)
    if level == "patch":
        return format_version(major, minor, patch + 1)

    # Exhaustive check — the Literal type makes this unreachable at type-check
    # time, but we guard at runtime for callers using plain strings.
    raise ValueError(f"level must be 'major', 'minor', or 'patch', got {level!r}")

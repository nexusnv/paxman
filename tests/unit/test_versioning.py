"""Unit tests for ``paxman.versioning`` — version constants and helpers.

Per V1_ACCEPTANCE_CRITERIA.md §2.2 and sprint-01-foundation.md exit criterion
#11, ``versioning.py`` must have 100% line coverage. These tests exercise
every code path: every error branch, every version comparison outcome, every
bump direction.
"""

from __future__ import annotations

import pytest

from paxman.versioning import (
    CONTRACT_FORMAT_VERSION,
    PAXMAN_VERSION,
    PLANNER_VERSION,
    REPLAY_VERSION,
    __version__,
    bump_version,
    check_version_compatibility,
    format_version,
    parse_version,
)

# --- Constants --------------------------------------------------------------


def test_paxman_version_is_string() -> None:
    assert isinstance(PAXMAN_VERSION, str)


def test_dunder_version_matches_paxman_version() -> None:
    """The ``__version__`` dunder equals the public ``PAXMAN_VERSION`` constant."""
    assert __version__ == PAXMAN_VERSION


def test_planner_version_is_string() -> None:
    assert isinstance(PLANNER_VERSION, str)
    assert PLANNER_VERSION  # non-empty


def test_replay_version_is_string() -> None:
    assert isinstance(REPLAY_VERSION, str)
    assert REPLAY_VERSION  # non-empty


def test_contract_format_version_is_string() -> None:
    assert isinstance(CONTRACT_FORMAT_VERSION, str)
    assert CONTRACT_FORMAT_VERSION  # non-empty


# --- parse_version ----------------------------------------------------------


def test_parse_version_simple() -> None:
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_zeros() -> None:
    assert parse_version("0.0.0") == (0, 0, 0)


def test_parse_version_strips_v_prefix() -> None:
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("v0.1.0") == (0, 1, 0)


def test_parse_version_invalid_too_few_parts() -> None:
    with pytest.raises(ValueError):
        parse_version("1.2")


def test_parse_version_invalid_too_many_parts() -> None:
    with pytest.raises(ValueError):
        parse_version("1.2.3.4")


def test_parse_version_invalid_non_numeric() -> None:
    with pytest.raises(ValueError):
        parse_version("a.b.c")


def test_parse_version_invalid_empty() -> None:
    with pytest.raises(ValueError):
        parse_version("")


def test_parse_version_invalid_prerelease_rejected() -> None:
    """V1 does not support pre-release suffixes like ``1.0.0-rc.1``."""
    with pytest.raises(ValueError):
        parse_version("1.0.0-rc.1")


# --- format_version ---------------------------------------------------------


def test_format_version_simple() -> None:
    assert format_version(1, 2, 3) == "1.2.3"


def test_format_version_zeros() -> None:
    assert format_version(0, 0, 0) == "0.0.0"


def test_format_version_negative_rejected() -> None:
    with pytest.raises(ValueError):
        format_version(-1, 0, 0)


def test_format_version_roundtrip_with_parse() -> None:
    """``format_version(parse_version(s)) == s`` for valid semver strings."""
    for s in ["1.2.3", "0.0.0", "10.20.30", "v1.2.3"]:
        # ``v`` prefix is stripped by parse_version, so re-formatting drops it.
        parsed = parse_version(s)
        assert format_version(*parsed) == s.lstrip("v")


# --- check_version_compatibility --------------------------------------------


def test_compat_same_version() -> None:
    assert check_version_compatibility("0.0.0", "0.0.0") is True


def test_compat_artifact_older_minor_compatible() -> None:
    """An artifact from an older minor version is replayable on a newer minor (per §16.1)."""
    assert check_version_compatibility("0.0.0", "0.1.0") is True


def test_compat_artifact_newer_minor_incompatible() -> None:
    """An artifact from a future minor version is NOT replayable."""
    assert check_version_compatibility("0.1.0", "0.0.0") is False


def test_compat_different_major_incompatible() -> None:
    """Different major versions are never compatible."""
    assert check_version_compatibility("1.0.0", "0.9.0") is False
    assert check_version_compatibility("0.9.0", "1.0.0") is False


def test_compat_same_major_same_minor() -> None:
    """Same major + same minor + current ≥ artifact is compatible (lower patch on current)."""
    assert check_version_compatibility("1.2.3", "1.2.5") is True
    # Note: artifact with HIGHER patch than current is NOT compatible
    # (V1 has no forward-compatibility guarantee; per ARCHITECTURE §16.1).


def test_compat_uses_paxman_version_default() -> None:
    """Calling without the second arg uses ``PAXMAN_VERSION``."""
    assert check_version_compatibility(PAXMAN_VERSION) is True


# --- bump_version ------------------------------------------------------------


def test_bump_patch() -> None:
    assert bump_version("0.0.0", "patch") == "0.0.1"
    assert bump_version("1.2.3", "patch") == "1.2.4"


def test_bump_minor_resets_patch() -> None:
    assert bump_version("0.0.0", "minor") == "0.1.0"
    assert bump_version("1.2.3", "minor") == "1.3.0"


def test_bump_major_resets_minor_and_patch() -> None:
    assert bump_version("0.0.0", "major") == "1.0.0"
    assert bump_version("1.2.3", "major") == "2.0.0"


def test_bump_invalid_level() -> None:
    with pytest.raises(ValueError):
        bump_version("1.0.0", "feature")  # type: ignore[arg-type]


def test_bump_invalid_version() -> None:
    with pytest.raises(ValueError):
        bump_version("not-a-version", "patch")


def test_bump_round_trip_with_parse_format() -> None:
    """``bump_version`` output is round-trippable through ``parse_version`` and ``format_version``."""
    for level in ("major", "minor", "patch"):
        bumped = bump_version("1.2.3", level)  # type: ignore[arg-type]
        # Re-parse and re-format to confirm the format is stable.
        assert format_version(*parse_version(bumped)) == bumped

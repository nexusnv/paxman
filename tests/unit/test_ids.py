"""Unit tests for ``paxman.ids`` — prefixed ID helpers."""

from __future__ import annotations

import re

import pytest

from paxman.ids import (
    ARTIFACT_PREFIX,
    CAPABILITY_PREFIX,
    FIELD_PREFIX,
    PLAN_PREFIX,
    generate_artifact_id,
    generate_capability_id,
    generate_field_id,
    generate_plan_id,
    is_artifact_id,
    is_capability_id,
    is_field_id,
    is_plan_id,
    parse_id,
)

# --- Prefix constants -------------------------------------------------------


def test_field_prefix() -> None:
    assert FIELD_PREFIX == "field_"


def test_capability_prefix() -> None:
    assert CAPABILITY_PREFIX == "cap_"


def test_artifact_prefix() -> None:
    assert ARTIFACT_PREFIX == "art_"


def test_plan_prefix() -> None:
    assert PLAN_PREFIX == "plan_"


# --- ID generation ----------------------------------------------------------


@pytest.mark.parametrize(
    "generator,prefix",
    [
        (generate_field_id, "field_"),
        (generate_capability_id, "cap_"),
        (generate_artifact_id, "art_"),
        (generate_plan_id, "plan_"),
    ],
)
def test_generated_id_has_correct_prefix(generator, prefix: str) -> None:
    """Each generated ID has the correct prefix."""
    value = generator()
    assert value.startswith(prefix)
    assert len(value) == len(prefix) + 12  # 12 hex chars


@pytest.mark.parametrize(
    "generator",
    [generate_field_id, generate_capability_id, generate_artifact_id, generate_plan_id],
)
def test_generated_id_is_unique(generator) -> None:
    """Two consecutive calls produce different IDs."""
    ids = {generator() for _ in range(100)}
    assert len(ids) == 100  # all unique


@pytest.mark.parametrize(
    "generator",
    [generate_field_id, generate_capability_id, generate_artifact_id, generate_plan_id],
)
def test_generated_id_matches_uuid4_pattern(generator) -> None:
    """The suffix is a 12-char lowercase hex string (48 bits of UUID4)."""
    value = generator()
    suffix = value.split("_", 1)[1]
    assert re.fullmatch(r"[0-9a-f]{12}", suffix), f"{value!r} suffix is not 12 lowercase hex chars"


# --- Validation -------------------------------------------------------------


@pytest.mark.parametrize(
    "validator,prefix,generator",
    [
        (is_field_id, "field_", generate_field_id),
        (is_capability_id, "cap_", generate_capability_id),
        (is_artifact_id, "art_", generate_artifact_id),
        (is_plan_id, "plan_", generate_plan_id),
    ],
)
def test_valid_id_passes_validation(validator, prefix: str, generator) -> None:
    """A freshly generated ID passes its own validator."""
    assert validator(generator()) is True


@pytest.mark.parametrize(
    "validator,prefix",
    [
        (is_field_id, "field_"),
        (is_capability_id, "cap_"),
        (is_artifact_id, "art_"),
        (is_plan_id, "plan_"),
    ],
)
def test_wrong_prefix_fails_validation(validator, prefix: str) -> None:
    """A wrong-prefixed ID fails the validator."""
    wrong = prefix + "wrongprefix_" + "abc123"
    # Just call the other prefix
    if prefix == "field_":
        assert is_field_id(wrong) is False  # wrong prefix
    # Each validator should reject a string that doesn't start with its prefix
    other_prefix = "zzz_"
    assert validator(other_prefix + "abc123456789") is False


@pytest.mark.parametrize(
    "validator,prefix",
    [
        (is_field_id, "field_"),
        (is_capability_id, "cap_"),
        (is_artifact_id, "art_"),
        (is_plan_id, "plan_"),
    ],
)
def test_too_short_id_fails_validation(validator, prefix: str) -> None:
    """An ID with the right prefix but wrong length fails."""
    assert validator(prefix + "abc") is False


@pytest.mark.parametrize(
    "validator,prefix",
    [
        (is_field_id, "field_"),
        (is_capability_id, "cap_"),
        (is_artifact_id, "art_"),
        (is_plan_id, "plan_"),
    ],
)
def test_too_long_id_fails_validation(validator, prefix: str) -> None:
    """An ID with the right prefix but too long fails."""
    assert validator(prefix + "a" * 13) is False


# --- parse_id ---------------------------------------------------------------


def test_parse_field_id() -> None:
    """``parse_id`` recognizes a field ID and returns ``("field", suffix)``."""
    prefix, _suffix = parse_id(generate_field_id())
    assert prefix == "field_"


def test_parse_capability_id() -> None:
    prefix, _suffix = parse_id(generate_capability_id())
    assert prefix == "cap_"


def test_parse_artifact_id() -> None:
    prefix, _suffix = parse_id(generate_artifact_id())
    assert prefix == "art_"


def test_parse_plan_id() -> None:
    prefix, _suffix = parse_id(generate_plan_id())
    assert prefix == "plan_"


def test_parse_id_unknown_prefix_raises() -> None:
    """``parse_id`` raises ValueError on an unknown prefix."""
    with pytest.raises(ValueError, match="Unrecognised ID format"):
        parse_id("unknown_abc123456789")

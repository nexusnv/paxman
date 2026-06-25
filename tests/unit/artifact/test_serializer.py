"""Unit tests for ``paxman.artifact.serializer`` — encode_artifact, decode_artifact."""

from __future__ import annotations

import json
import typing

import pytest

from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.artifact.serializer import decode_artifact, encode_artifact
from paxman.types import Status

pytestmark = pytest.mark.unit


def _make_artifact(**overrides: typing.Any) -> ExecutionArtifact:
    """Build an ExecutionArtifact with status=SUCCESS, plus any overrides."""
    return ExecutionArtifact(status=Status.SUCCESS, **overrides)


# ============================================================================
# encode_artifact
# ============================================================================


@pytest.mark.deterministic
def test_encode_artifact_returns_string() -> None:
    """encode_artifact returns a string."""
    art = _make_artifact()
    encoded = encode_artifact(art)
    assert isinstance(encoded, str)


@pytest.mark.deterministic
def test_encode_artifact_is_deterministic() -> None:
    """encode_artifact produces the same output for the same artifact."""
    art = _make_artifact(normalized_data={"a": 1})
    result1 = encode_artifact(art)
    result2 = encode_artifact(art)
    assert result1 == result2


@pytest.mark.deterministic
def test_encode_artifact_requires_attrs_instance() -> None:
    """encode_artifact raises when not given an attrs instance."""
    with pytest.raises((TypeError, ValueError)):
        encode_artifact(object())  # type: ignore[arg-type]


@pytest.mark.deterministic
def test_encode_artifact_sorted_keys() -> None:
    """encode_artifact produces JSON with sorted keys (no whitespace, compact)."""
    art = _make_artifact(normalized_data={"z": 1, "a": 2, "m": 3})
    encoded = encode_artifact(art)
    # Parse back to check keys in normalized_data are sorted
    parsed: dict[str, typing.Any] = json.loads(encoded)
    nd = parsed["normalized_data"]
    assert isinstance(nd, dict)
    assert list(nd.keys()) == ["a", "m", "z"]


@pytest.mark.deterministic
def test_encode_artifact_compact_no_whitespace() -> None:
    """encode_artifact produces compact JSON with no whitespace outside strings."""
    art = _make_artifact()
    encoded = encode_artifact(art)
    assert " " not in encoded
    assert "\n" not in encoded
    assert "\t" not in encoded


@pytest.mark.deterministic
def test_encode_artifact_key_order_across_fields() -> None:
    """The top-level keys in the JSON should also be sorted."""
    art = _make_artifact()
    encoded = encode_artifact(art)
    parsed: dict[str, typing.Any] = json.loads(encoded)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


# ============================================================================
# decode_artifact
# ============================================================================


@pytest.mark.deterministic
def test_decode_artifact_round_trip() -> None:
    """encode -> decode -> dict preserves all data from the original."""
    fr = FieldResult(field_path="name", value="Alice", status=Status.SUCCESS)
    art = _make_artifact(
        normalized_data={"name": "Alice"},
        field_results={"name": fr},
    )
    encoded = encode_artifact(art)
    decoded = decode_artifact(encoded)

    assert isinstance(decoded, dict)
    assert decoded["status"] == "SUCCESS"
    assert decoded["normalized_data"] == {"name": "Alice"}
    # Check field_results was serialized (it's an attrs->dict conversion)
    fr_dict = decoded["field_results"]["name"]
    assert isinstance(fr_dict, dict)
    assert fr_dict["field_path"] == "name"
    assert fr_dict["value"] == "Alice"


@pytest.mark.deterministic
def test_decode_artifact_returns_dict() -> None:
    """decode_artifact always returns a dict when given valid JSON."""
    art = _make_artifact()
    encoded = encode_artifact(art)
    decoded = decode_artifact(encoded)
    assert isinstance(decoded, dict)


@pytest.mark.deterministic
def test_decode_artifact_rejects_non_dict_json() -> None:
    """decode_artifact raises TypeError if JSON root is not an object."""
    with pytest.raises(TypeError, match="decode_artifact expected a JSON object"):
        decode_artifact('"string_value"')


@pytest.mark.deterministic
def test_decode_artifact_rejects_json_array() -> None:
    """decode_artifact raises TypeError for JSON arrays."""
    with pytest.raises(TypeError, match="decode_artifact expected a JSON object"):
        decode_artifact("[1, 2, 3]")


@pytest.mark.deterministic
def test_decode_artifact_rejects_primitive_json() -> None:
    """decode_artifact raises TypeError for JSON primitives."""
    with pytest.raises(TypeError, match="decode_artifact expected a JSON object"):
        decode_artifact("42")


@pytest.mark.deterministic
def test_decode_artifact_rejects_malformed_json() -> None:
    """decode_artifact raises JSONDecodeError for malformed JSON."""
    with pytest.raises(json.JSONDecodeError):
        decode_artifact("{invalid json}")

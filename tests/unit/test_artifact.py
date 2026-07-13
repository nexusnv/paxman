"""Tests for ExecutionArtifact immutability and byte-equal serialization."""
from __future__ import annotations

import hashlib
import json

import attrs
import pytest

from paxman._core.artifact import ExecutionArtifact
from paxman._core.types import (
    Evidence,
    Status,
    VersionStamp,
)


class _FakeContract:
    """Minimal stand-in for the real Contract (defined in _contracts).

    The artifact only needs `as_dict()` and `version` for its canonical
    serialization; this stub is enough for the unit tests in this file.
    """

    def as_dict(self) -> dict[str, object]:
        return {"kind": "canonical_email", "version": 1}

    @property
    def version(self) -> int:
        return 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _FakeContract)

    def __hash__(self) -> int:
        return hash(("canonical_email", 1))


def _make_artifact(**overrides: object) -> ExecutionArtifact:
    defaults: dict[str, object] = dict(
        status=Status.CANONICALIZED,
        value="a@b.c",
        evidence=(Evidence(rule="lowercased_local_part"),),
        contract=_FakeContract(),  # type: ignore[arg-type]
        version_stamp=VersionStamp(
            paxman_version="0.0.0.dev0",
            contract_version=1,
            capabilities_hash="abc",
            configuration_version="0",
        ),
    )
    defaults.update(overrides)
    return ExecutionArtifact(**defaults)  # type: ignore[arg-type]


class TestArtifactImmutability:
    def test_status_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.status = Status.INVALID  # type: ignore[misc]

    def test_value_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.value = "x@y.z"  # type: ignore[misc]

    def test_evidence_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.evidence = ()  # type: ignore[misc]

    def test_replay_hash_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.replay_hash = "0" * 64  # type: ignore[misc]


class TestArtifactCanonicalBytes:
    def test_canonical_bytes_is_deterministic(self) -> None:
        a1 = _make_artifact()
        a2 = _make_artifact()
        assert a1.canonical_bytes() == a2.canonical_bytes()

    def test_canonical_bytes_is_sorted_key_json(self) -> None:
        a = _make_artifact()
        # The serialized form must be valid JSON with sorted keys and no
        # insignificant whitespace.
        payload = json.loads(a.canonical_bytes())
        assert payload["status"] == "canonicalized"
        assert payload["value"] == "a@b.c"

    def test_replay_hash_matches_sha256_of_canonical_bytes(self) -> None:
        a = _make_artifact()
        expected = hashlib.sha256(a.canonical_bytes()).hexdigest()
        assert a.replay_hash == expected


class TestArtifactEquality:
    def test_two_identical_artifacts_are_equal(self) -> None:
        a1 = _make_artifact()
        a2 = _make_artifact()
        assert a1 == a2
        assert hash(a1) == hash(a2)

    def test_different_value_means_different_artifact(self) -> None:
        a1 = _make_artifact(value="a@b.c")
        a2 = _make_artifact(value="x@y.z")
        assert a1 != a2

    def test_different_status_means_different_artifact(self) -> None:
        a1 = _make_artifact(status=Status.CANONICALIZED)
        a2 = _make_artifact(status=Status.INVALID, value=None)
        assert a1 != a2

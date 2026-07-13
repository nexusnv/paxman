"""Tests for the leaf value types in paxman._core.types."""
from __future__ import annotations

import enum
import hashlib

import attrs

from paxman._core.types import (
    CapabilityResult,
    Evidence,
    Status,
    VersionStamp,
)


class TestStatus:
    def test_status_has_five_values(self) -> None:
        assert {s.name for s in Status} == {
            "CANONICALIZED",
            "INVALID",
            "MISSING",
            "AMBIGUOUS",
            "UNSUPPORTED",
        }

    def test_status_is_an_enum(self) -> None:
        assert issubclass(Status, enum.Enum)

    def test_status_values_are_lowercase_strings(self) -> None:
        # Mandate §3.1 wording: the wire form is a lowercase string.
        for s in Status:
            assert s.value == s.name.lower()


class TestEvidence:
    def test_evidence_is_frozen(self) -> None:
        e = Evidence(rule="lowercased_local_part", detail="")
        with_attrs = attrs.fields(Evidence)
        assert with_attrs[0].name == "rule"
        assert with_attrs[1].name == "detail"
        # FrozenInstanceError on assignment
        import pytest as _pt
        with _pt.raises(attrs.exceptions.FrozenInstanceError):
            e.rule = "x"  # type: ignore[misc]

    def test_evidence_default_detail_is_empty_string(self) -> None:
        assert Evidence(rule="r").detail == ""


class TestVersionStamp:
    def test_version_stamp_is_frozen(self) -> None:
        v = VersionStamp(
            paxman_version="0.0.0.dev0",
            contract_version=1,
            capabilities_hash="abc",
            configuration_version="0",
        )
        import pytest as _pt
        with _pt.raises(attrs.exceptions.FrozenInstanceError):
            v.contract_version = 2  # type: ignore[misc]

    def test_version_stamp_equality(self) -> None:
        a = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        b = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        assert a == b

    def test_version_stamp_hash(self) -> None:
        a = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        b = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        assert {a, b} == {a}


class TestCapabilityResult:
    def test_canonicalized_carries_value(self) -> None:
        r = CapabilityResult(status=Status.CANONICALIZED, value="x@y.z")
        assert r.status is Status.CANONICALIZED
        assert r.value == "x@y.z"
        assert r.evidence == ()

    def test_invalid_carries_no_value(self) -> None:
        r = CapabilityResult(status=Status.INVALID)
        assert r.value is None

    def test_evidence_default_is_empty_tuple(self) -> None:
        r = CapabilityResult(status=Status.CANONICALIZED, value="x")
        assert r.evidence == ()
        assert isinstance(r.evidence, tuple)

    def test_capability_result_is_frozen(self) -> None:
        r = CapabilityResult(status=Status.CANONICALIZED, value="x")
        import pytest as _pt
        with _pt.raises(attrs.exceptions.FrozenInstanceError):
            r.status = Status.INVALID  # type: ignore[misc]

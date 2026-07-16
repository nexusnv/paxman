"""End-to-end exercise of the BooleanCapability via the public API."""

from __future__ import annotations

import attrs
import pytest

from paxman import Boolean, canonicalize, replay
from paxman._core.status import Status


@pytest.mark.integration
def test_yes_canonicalizes() -> None:
    r = canonicalize("Yes", Boolean())
    assert r.status is Status.CANONICALIZED
    assert r.value == "true"


@pytest.mark.integration
def test_numeric_zero_canonicalizes() -> None:
    r = canonicalize("0", Boolean())
    assert r.status is Status.CANONICALIZED
    assert r.value == "false"


@pytest.mark.integration
def test_policy_disabled_numeric_is_invalid() -> None:
    r = canonicalize("1", Boolean(accept_numeric=False))
    assert r.status is Status.INVALID


@pytest.mark.integration
def test_missing_for_empty() -> None:
    assert canonicalize("", Boolean()).status is Status.MISSING


@pytest.mark.integration
def test_unknown_kind_is_unsupported() -> None:
    r = canonicalize("true", {"kind": "canonical_bogus"})
    assert r.status is Status.UNSUPPORTED


@pytest.mark.integration
def test_replay_byte_equal() -> None:
    r = canonicalize("ENABLED", Boolean())
    assert r.status is Status.CANONICALIZED
    rehydrated = replay(r, Boolean())
    assert rehydrated == r


@pytest.mark.integration
def test_artifact_is_immutable() -> None:
    r = canonicalize("no", Boolean())
    for field in attrs.fields(type(r)):
        try:
            setattr(r, field.name, "x")  # type: ignore[arg-type]
            raise AssertionError(f"{field.name} was mutable")
        except attrs.exceptions.FrozenInstanceError:
            pass

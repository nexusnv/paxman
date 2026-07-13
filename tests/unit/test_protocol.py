"""Tests for the Capability Protocol (mandate §5.1)."""
from __future__ import annotations

import pytest

from paxman._capabilities.protocol import Capability
from paxman._core.types import CapabilityResult
from paxman._contracts.contract import CanonicalEmailContract


class _Good:
    name = "good"

    def can_handle(self, contract, value):  # type: ignore[no-untyped-def]
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(self, value, contract):  # type: ignore[no-untyped-def]
        return CapabilityResult(status=__import__("paxman._core.types", fromlist=["Status"]).Status.CANONICALIZED, value=value)


class _MissingName:
    def can_handle(self, contract, value): ...  # type: ignore[no-untyped-def]
    def canonicalize(self, value, contract): ...  # type: ignore[no-untyped-def]


class _MissingMethods:
    name = "x"


class TestProtocol:
    def test_good_capability_isinstance(self) -> None:
        assert isinstance(_Good(), Capability)

    def test_missing_name_is_not_capability(self) -> None:
        assert not isinstance(_MissingName(), Capability)

    def test_missing_methods_is_not_capability(self) -> None:
        assert not isinstance(_MissingMethods(), Capability)

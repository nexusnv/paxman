"""Tests for the Capability Protocol (mandate §5.1)."""

from __future__ import annotations

from typing import Any

from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._capabilities.protocol import Capability
from paxman._core.contracts import Contract
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


class _Good:
    name: str = "good"
    supported_output_formats: frozenset[str] = frozenset()

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        return CapabilityResult(status=Status.CANONICALIZED, value=str(value))


class _MissingName:
    def can_handle(self, contract: Any, value: Any) -> bool:
        return False

    def canonicalize(self, value: Any, contract: Any) -> CapabilityResult:
        return CapabilityResult(status=Status.INVALID)


class _MissingMethods:
    name: str = "x"


class TestProtocol:
    def test_good_capability_isinstance(self) -> None:
        assert isinstance(_Good(), Capability)

    def test_missing_name_is_not_capability(self) -> None:
        assert not isinstance(_MissingName(), Capability)

    def test_missing_methods_is_not_capability(self) -> None:
        assert not isinstance(_MissingMethods(), Capability)

"""Tests for the shared CapabilityBase (Finding D, narrow)."""

from __future__ import annotations

from typing import Any, cast

from paxman._capabilities._shared.base import CapabilityBase
from paxman._core.classification import ValidationResult
from paxman._core.contracts import Contract


class _StubCap(CapabilityBase):
    name = "stub"

    def can_handle(self, contract: Contract, value: Any) -> bool:
        return isinstance(value, str) and value.startswith("x")

    def canonicalize(self, value: Any, contract: Contract, engine: Any | None = None) -> object:
        return f"canon:{value}"


def test_base_default_validate_passes() -> None:
    cap = _StubCap()
    assert cap.validate("anything", cast(Contract, object())).is_valid is True


def test_base_subclass_canonicalize_is_used_directly() -> None:
    cap = _StubCap()
    assert cap.canonicalize("x42", cast(Contract, object())) == "canon:x42"


def test_base_validate_is_the_dispatched_hook() -> None:
    class _Strict(CapabilityBase):
        name = "strict"

        def can_handle(self, contract: Contract, value: Any) -> bool:
            return True

        def canonicalize(self, value: Any, contract: Contract, engine: Any | None = None) -> object:
            return value

        def validate(self, value: str, contract: Contract) -> ValidationResult:
            return ValidationResult(is_valid="@" in value)

    assert _Strict().validate("a@b", cast(Contract, object())).is_valid is True
    assert _Strict().validate("ab", cast(Contract, object())).is_valid is False

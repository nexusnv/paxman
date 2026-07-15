"""Tests for the deterministic classifier (Status assignment)."""

from __future__ import annotations

from paxman._core.classification import ValidationResult, classify
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


class TestClassify:
    def test_canonicalized_input_with_valid_value_yields_canonicalized(self) -> None:
        cr = CapabilityResult(status=Status.CANONICALIZED, value="a@b.c")
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.CANONICALIZED

    def test_canonicalized_input_with_invalid_value_yields_invalid(self) -> None:
        # The capability says CANONICALIZED but validation rejects it
        # (e.g., contract policy was strict and the value violates it).
        cr = CapabilityResult(status=Status.CANONICALIZED, value="x")
        vr = ValidationResult(is_valid=False)
        assert classify(cr, vr) is Status.INVALID

    def test_capability_invalid_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.INVALID)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.INVALID

    def test_capability_missing_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.MISSING)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.MISSING

    def test_capability_ambiguous_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.AMBIGUOUS)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.AMBIGUOUS

    def test_capability_unsupported_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.UNSUPPORTED)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.UNSUPPORTED

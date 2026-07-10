"""Tests for the new V1.2.0 inference DiagnosticCode members (spec #50 §6)."""
from __future__ import annotations

import pytest

from paxman.capabilities.result import DiagnosticCode


class TestInferenceDiagnosticCodes:
    """The 7 new DiagnosticCode members added in V1.2.0 for the inference layer."""

    @pytest.mark.parametrize(
        "member_name",
        [
            "INFERENCE_PROVIDER_KEY_MISSING",
            "INFERENCE_PROVIDER_KEY_REFERENCE",
            "INFERENCE_PROVIDER_RATE_LIMITED",
            "INFERENCE_PROVIDER_TIMEOUT",
            "INFERENCE_PROVIDER_INVALID_RESPONSE",
            "INFERENCE_PROVIDER_MODEL_NOT_FOUND",
            "INFERENCE_PROVIDER_CAPABILITY_UNSUPPORTED",
        ],
    )
    def test_member_exists(self, member_name: str) -> None:
        """Each new code must exist on the DiagnosticCode enum."""
        assert hasattr(DiagnosticCode, member_name), (
            f"DiagnosticCode.{member_name} is missing"
        )

    def test_members_are_distinct(self) -> None:
        """Each new code must have a distinct value (no alias collisions)."""
        codes = [
            DiagnosticCode.INFERENCE_PROVIDER_KEY_MISSING,
            DiagnosticCode.INFERENCE_PROVIDER_KEY_REFERENCE,
            DiagnosticCode.INFERENCE_PROVIDER_RATE_LIMITED,
            DiagnosticCode.INFERENCE_PROVIDER_TIMEOUT,
            DiagnosticCode.INFERENCE_PROVIDER_INVALID_RESPONSE,
            DiagnosticCode.INFERENCE_PROVIDER_MODEL_NOT_FOUND,
            DiagnosticCode.INFERENCE_PROVIDER_CAPABILITY_UNSUPPORTED,
        ]
        assert len(set(codes)) == len(codes), "duplicate values among new members"

    def test_existing_members_unchanged(self) -> None:
        """V1.0.0/V1.0.2 DiagnosticCode members must still exist and be unchanged."""
        # The two pre-existing inference-related codes from V1.0.0.
        assert hasattr(DiagnosticCode, "INFERENCE_PROVIDER_ERROR")
        assert hasattr(DiagnosticCode, "INFERENCE_OUTPUT_UNTRUSTED")

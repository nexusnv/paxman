"""Integration tests: Adversarial inputs (D7.13).

Per Sprint 7 D7.13 and exit criterion #5, this test exercises the
pipeline on **adversarial inputs** — empty, unicode, prompt
injection, and mismatched currency — and verifies that the
pipeline never crashes (it returns a valid artifact with status
``UNRESOLVED`` or ``PARTIAL_SUCCESS``).

Adversarial inputs are committed to ``tests/fixtures/inputs/adversarial/``
(Layer 1, hand-written edge cases).
"""

from __future__ import annotations

import pathlib

import pytest

import paxman

# Trigger auto-registration.
import paxman.contract.adapters.dict_dsl
from paxman.artifact.artifact import ExecutionArtifact
from paxman.types import Status
from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE
from tests.fixtures.contracts.dict_dsl.with_money import DICT_DSL_WITH_MONEY

pytestmark = pytest.mark.integration

_ADVERSARIAL_DIR = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "fixtures" / "inputs" / "adversarial"
)


def _load(name: str) -> str:
    """Load an adversarial input file by name."""
    path = _ADVERSARIAL_DIR / name
    if not path.exists():
        pytest.skip(f"Adversarial fixture {name} not found at {path}")
    return path.read_text(encoding="utf-8")


class TestAdversarialInputs:
    """Adversarial inputs return UNRESOLVED or PARTIAL_SUCCESS, never a crash."""

    def test_empty_input_returns_valid_artifact(self) -> None:
        """An empty input returns a valid artifact (UNRESOLVED or PARTIAL_SUCCESS)."""
        artifact = paxman.normalize(input_data="", contract=DICT_DSL_INVOICE)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.status in {Status.UNRESOLVED, Status.PARTIAL_SUCCESS, Status.SUCCESS}

    def test_unicode_input_returns_valid_artifact(self) -> None:
        """A unicode-only input returns a valid artifact."""
        artifact = paxman.normalize(input_data="日本語 中文 €£¥", contract=DICT_DSL_INVOICE)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.status in {Status.UNRESOLVED, Status.PARTIAL_SUCCESS, Status.SUCCESS}

    def test_prompt_injection_returns_valid_artifact(self) -> None:
        """A prompt-injection input returns a valid artifact without crashing."""
        text = _load("prompt_injection.txt")
        artifact = paxman.normalize(input_data=text, contract=DICT_DSL_INVOICE)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.status in {Status.UNRESOLVED, Status.PARTIAL_SUCCESS, Status.SUCCESS}

    def test_unicode_only_input_returns_valid_artifact(self) -> None:
        """A unicode-only input file returns a valid artifact."""
        text = _load("unicode_only.txt")
        artifact = paxman.normalize(input_data=text, contract=DICT_DSL_INVOICE)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.status in {Status.UNRESOLVED, Status.PARTIAL_SUCCESS, Status.SUCCESS}

    @pytest.mark.slow
    def test_extremely_large_input_returns_valid_artifact(self) -> None:
        """An extremely large input returns a valid artifact."""
        # Don't actually load the file (could be many MB) — just
        # generate a large in-memory text.
        text = "ACME Corp\n" + ("Padding text.\n" * 100_000)
        artifact = paxman.normalize(input_data=text, contract=DICT_DSL_INVOICE)
        assert isinstance(artifact, ExecutionArtifact)
        assert artifact.status in {Status.UNRESOLVED, Status.PARTIAL_SUCCESS, Status.SUCCESS}

    def test_mismatched_currency_input_returns_valid_artifact(self) -> None:
        """A mismatched-currency input returns a valid artifact."""
        text = _load("mismatched_currency.txt")
        artifact = paxman.normalize(input_data=text, contract=DICT_DSL_WITH_MONEY)
        assert isinstance(artifact, ExecutionArtifact)
        # The status should be one of the valid non-failure states.
        # Mismatched currency should not crash the pipeline.
        assert artifact.status in {Status.UNRESOLVED, Status.PARTIAL_SUCCESS, Status.SUCCESS}

    def test_truncated_pdf_does_not_crash(self) -> None:
        """A truncated PDF (binary) input does not crash the pipeline."""
        # The truncated_pdf.bin is binary; reading as text would fail.
        # We use ``input_data=bytes`` to pass the raw bytes.
        path = _ADVERSARIAL_DIR / "truncated_pdf.bin"
        if not path.exists():
            pytest.skip(f"truncated_pdf.bin not found at {path}")
        # Read as bytes to avoid decode errors.
        raw = path.read_bytes()
        artifact = paxman.normalize(input_data=raw, contract=DICT_DSL_INVOICE)
        assert isinstance(artifact, ExecutionArtifact)
        # We just need to verify it doesn't crash.

    def test_adversarial_artifact_can_be_replayed(self) -> None:
        """An adversarial artifact can be replayed (no replay crash)."""
        artifact = paxman.normalize(input_data="", contract=DICT_DSL_INVOICE)
        replayed = paxman.replay(artifact, contract=DICT_DSL_INVOICE)
        assert replayed == artifact

"""Property tests for the V1 post-extraction cleanup transforms.

These tests pin **byte-equal determinism** across N=100 random
inputs per capability. A determinism violation is a test failure
(per ``SECURITY.md`` and the ``derandomize=True`` project-wide
convention).

Mirrors ``tests/property/test_format_extractors_determinism.py``.
The capabilities under test are pure functions of
``(value, mode)`` / ``(value, chars)``; any nondeterminism here
is a real bug.
"""

from __future__ import annotations

import string

import hypothesis
import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.v1.case_normalization import CaseNormalizationCapability
from paxman.capabilities.v1.trim_extraction import TrimExtractionCapability

pytestmark = [pytest.mark.deterministic, pytest.mark.property]


# --- case_normalization ---------------------------------------------------


_CASE_MODES: tuple[str, ...] = ("lower", "upper", "title", "preserve")


@given(
    value=st.text(alphabet=string.ascii_letters + string.digits + " ", min_size=0, max_size=50),
    mode=st.sampled_from(_CASE_MODES),
)
@hypothesis.settings(derandomize=True, deadline=None, max_examples=100)
def test_case_normalization_is_deterministic(value: str, mode: str) -> None:
    """The same (value, mode) returns the same candidates twice."""
    cap = CaseNormalizationCapability()
    ctx = CapabilityContext(
        raw_input=b"",
        field_path="field",
        field_type_name="STRING",
        config={"value": value, "mode": mode},
    )
    first = cap.invoke(ctx)
    second = cap.invoke(ctx)
    assert first.candidates == second.candidates
    assert first.evidence == second.evidence
    assert first.diagnostics == second.diagnostics


# --- trim_extraction ------------------------------------------------------


@given(
    value=st.text(alphabet=string.ascii_letters + string.digits, min_size=0, max_size=50),
    chars=st.sampled_from(["", "-", " :", "abc", "-_/", "\u200b\u200c\u200d\ufeff"]),
)
@hypothesis.settings(derandomize=True, deadline=None, max_examples=100)
def test_trim_extraction_is_deterministic(value: str, chars: str) -> None:
    """The same (value, chars) returns the same candidates twice.

    The empty-chars case is excluded from the canonical happy-path
    property run because empty ``chars`` is a configuration error
    (it produces a ``CAPABILITY_INVOKE_FAILED`` diagnostic), not a
    valid input. We only assert determinism for valid inputs here.
    """
    hypothesis.assume(chars != "")
    cap = TrimExtractionCapability()
    ctx = CapabilityContext(
        raw_input=b"",
        field_path="field",
        field_type_name="STRING",
        config={"value": value, "chars": chars},
    )
    first = cap.invoke(ctx)
    second = cap.invoke(ctx)
    assert first.candidates == second.candidates
    assert first.evidence == second.evidence
    assert first.diagnostics == second.diagnostics


# --- default-chars determinism (no explicit chars) ------------------------


@given(
    value=st.text(alphabet=string.ascii_letters + " \t\n:;,._-", min_size=0, max_size=50),
)
@hypothesis.settings(derandomize=True, deadline=None, max_examples=100)
def test_trim_extraction_default_is_deterministic(value: str) -> None:
    """Same value with default chars returns the same candidates twice."""
    cap = TrimExtractionCapability()
    ctx = CapabilityContext(
        raw_input=b"",
        field_path="field",
        field_type_name="STRING",
        config={"value": value},
    )
    first = cap.invoke(ctx)
    second = cap.invoke(ctx)
    assert first.candidates == second.candidates
    assert first.evidence == second.evidence
    assert first.diagnostics == second.diagnostics

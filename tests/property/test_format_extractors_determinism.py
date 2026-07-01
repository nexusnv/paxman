"""Property tests for the V1 format-aware extraction capabilities.

These tests pin **byte-equal determinism** across N=100 random
inputs per capability. A determinism violation is a test failure
(per ``SECURITY.md`` and the ``derandomize=True`` project-wide
convention).

Mirrors ``tests/property/test_planner_determinism.py``. The
capabilities under test are pure functions of
``(raw_input, config)``; any nondeterminism here is a real bug.
"""

from __future__ import annotations

import json
import string

import hypothesis
import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.v1.csv_extraction import CsvExtractionCapability
from paxman.capabilities.v1.json_path_extraction import JsonPathExtractionCapability
from paxman.capabilities.v1.xpath_extraction import XPathExtractionCapability

pytestmark = [pytest.mark.deterministic, pytest.mark.property]


# --- JSON path extraction --------------------------------------------------


@given(
    data=st.dictionaries(
        keys=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=5),
        values=st.one_of(
            st.text(max_size=20),
            st.integers(min_value=0, max_value=1000),
            st.booleans(),
        ),
        min_size=1,
        max_size=5,
    )
)
@hypothesis.settings(derandomize=True, deadline=None, max_examples=100)
def test_json_path_extraction_is_deterministic(data: dict) -> None:
    """The same JSON input + pointer returns the same candidates twice."""
    cap = JsonPathExtractionCapability()
    raw = json.dumps(data).encode("utf-8")
    first_key = next(iter(data))
    ctx = CapabilityContext(
        raw_input=raw,
        field_path="field",
        field_type_name="STRING",
        config={"pointer": f"/{first_key}"},
    )
    first = cap.invoke(ctx)
    second = cap.invoke(ctx)
    assert first.candidates == second.candidates
    assert first.evidence == second.evidence
    assert first.diagnostics == second.diagnostics


# --- CSV extraction --------------------------------------------------------


@given(
    rows=st.lists(
        st.lists(
            st.text(alphabet=string.ascii_letters + " ", min_size=0, max_size=10),
            min_size=2,
            max_size=2,
        ),
        min_size=1,
        max_size=10,
    )
)
@hypothesis.settings(derandomize=True, deadline=None, max_examples=100)
def test_csv_extraction_is_deterministic(rows: list[list[str]]) -> None:
    """The same CSV input + column returns the same candidates twice."""
    cap = CsvExtractionCapability()
    raw = "\n".join(",".join(row) for row in rows).encode("utf-8")
    ctx = CapabilityContext(
        raw_input=raw,
        field_path="field",
        field_type_name="STRING",
        config={"column": 0},
    )
    first = cap.invoke(ctx)
    second = cap.invoke(ctx)
    assert first.candidates == second.candidates
    assert first.evidence == second.evidence
    assert first.diagnostics == second.diagnostics


# --- XPath extraction ------------------------------------------------------


@given(
    values=st.lists(
        st.text(alphabet=string.ascii_letters, min_size=1, max_size=5),
        min_size=1,
        max_size=5,
    )
)
@hypothesis.settings(derandomize=True, deadline=None, max_examples=100)
def test_xpath_extraction_is_deterministic(values: list[str]) -> None:
    """The same XML input + xpath returns the same candidates twice."""
    cap = XPathExtractionCapability()
    items = "".join(f"<item>{v}</item>" for v in values)
    raw = f"<root>{items}</root>".encode()
    ctx = CapabilityContext(
        raw_input=raw,
        field_path="field",
        field_type_name="STRING",
        config={"xpath": "/root/item"},
    )
    first = cap.invoke(ctx)
    second = cap.invoke(ctx)
    assert first.candidates == second.candidates
    assert first.evidence == second.evidence
    assert first.diagnostics == second.diagnostics

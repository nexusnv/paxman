"""Unit tests for ``planner.heuristics.select_format_aware``."""

from __future__ import annotations

import pytest

from paxman.budget import Policy
from paxman.capabilities.registry import register, reset
from paxman.capabilities.v1.csv_extraction import CsvExtractionCapability
from paxman.capabilities.v1.json_path_extraction import JsonPathExtractionCapability
from paxman.capabilities.v1.regex_extraction import RegexExtractionCapability
from paxman.capabilities.v1.xpath_extraction import XPathExtractionCapability
from paxman.contract._cleanup import CleanupStep
from paxman.contract._extraction import ExtractionStep
from paxman.contract._format_hint import FormatHint
from paxman.contract.canonical import CanonicalField
from paxman.planner.heuristics import build_capability_chain, select_format_aware
from paxman.planner.input_profile import make_profile
from paxman.types import FieldType


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Reset the registry before AND after each test so the global
    capability registry does not leak between tests."""
    reset()
    yield
    reset()


def _field(**overrides: object) -> CanonicalField:
    base: dict[str, object] = {
        "id": "field_test_x",
        "path": "x",
        "name": "x",
        "type": FieldType.STRING,
        "required": True,
    }
    base.update(overrides)
    return CanonicalField(**base)  # type: ignore[arg-type]


def _register_default_format_extractors() -> None:
    register(CsvExtractionCapability(), replace=True)
    register(JsonPathExtractionCapability(), replace=True)
    register(XPathExtractionCapability(), replace=True)
    register(RegexExtractionCapability(), replace=True)


def test_returns_empty_when_field_has_no_format_hints() -> None:
    _register_default_format_extractors()
    field = _field()
    assert select_format_aware(field) == []


def test_returns_matching_step_for_csv() -> None:
    _register_default_format_extractors()
    field = _field(format_hints=(FormatHint.CSV,))
    steps = select_format_aware(field)
    assert len(steps) == 1
    assert steps[0].capability_id == "csv_extraction"
    assert steps[0].capability_version == "1.0"
    # The CSV extractor consumes ``config["column"]``.
    assert dict(steps[0].config) == {"column": "x"}


def test_returns_matching_step_for_json() -> None:
    _register_default_format_extractors()
    field = _field(format_hints=(FormatHint.JSON,))
    steps = select_format_aware(field)
    assert len(steps) == 1
    assert steps[0].capability_id == "json_path_extraction"
    # The JSON extractor consumes ``config["pointer"]`` (a
    # JSON-Pointer into the input), not ``config["column"]``.
    assert dict(steps[0].config) == {"pointer": "/x"}, (
        f"json_path_extraction must receive a 'pointer' config; got {dict(steps[0].config)}"
    )


def test_returns_matching_step_for_xml() -> None:
    _register_default_format_extractors()
    field = _field(format_hints=(FormatHint.XML,))
    steps = select_format_aware(field)
    assert len(steps) == 1
    assert steps[0].capability_id == "xpath_extraction"
    # The XML extractor consumes ``config["xpath"]`` (an XPath
    # expression), not ``config["column"]``.
    assert dict(steps[0].config) == {"xpath": "//x"}, (
        f"xpath_extraction must receive an 'xpath' config; got {dict(steps[0].config)}"
    )


def test_returns_steps_for_all_matching_hints() -> None:
    _register_default_format_extractors()
    field = _field(format_hints=(FormatHint.JSON, FormatHint.XML))
    steps = select_format_aware(field)
    ids = [s.capability_id for s in steps]
    assert ids == ["json_path_extraction", "xpath_extraction"]


def test_build_chain_appends_configured_cleanup_after_matching_extractor() -> None:
    """Cleanup is a candidate hand-off only after CSV extraction is selected."""
    _register_default_format_extractors()
    field = _field(
        format_hints=(FormatHint.CSV,),
        cleanup_steps=(
            CleanupStep("case_normalization", {"mode": "lower"}),
            CleanupStep("trim_extraction"),
        ),
    )

    steps = build_capability_chain(field, make_profile(b"a,b"), Policy(), None)

    assert [step.capability_id for step in steps] == [
        "csv_extraction",
        "case_normalization",
        "trim_extraction",
    ]
    assert dict(steps[1].config) == {"mode": "lower", "input_from_candidate": True}
    assert dict(steps[2].config) == {"input_from_candidate": True}


def test_build_chain_does_not_plan_cleanup_without_matching_extractor() -> None:
    """Cleanup metadata cannot create a candidate on its own."""
    field = _field(cleanup_steps=(CleanupStep("trim_extraction"),))

    assert build_capability_chain(field, make_profile(b"supplier"), Policy(), None) == ()


def test_build_chain_uses_declared_regex_before_cleanup() -> None:
    """A contract-declared regex is the only non-format extraction path."""
    field = _field(
        extraction_step=ExtractionStep("regex_extraction", {"pattern": r"ID:\s*(?P<value>\S+)"}),
        cleanup_steps=(CleanupStep("trim_extraction"),),
    )

    steps = build_capability_chain(field, make_profile(b"ID: A-1"), Policy(), None)

    assert [step.capability_id for step in steps] == ["regex_extraction", "trim_extraction"]
    assert dict(steps[0].config) == {"pattern": r"ID:\s*(?P<value>\S+)"}
    assert dict(steps[1].config) == {"input_from_candidate": True}


def test_member_agnostic_dispatch() -> None:
    """The function is member-agnostic: it uses
    ``spec.format_hint in field.format_hints``, NOT a hard-coded
    list of the V1.1.0 members. This test pins the contract by
    inspecting the source of ``select_format_aware`` and asserting
    that no hard-coded ``FormatHint.<MEMBER>`` references appear in
    the dispatch logic. Adding a new FormatHint member must not
    require any change to this function's body."""
    import inspect

    src = inspect.getsource(select_format_aware)
    for member_name in ("CSV", "JSON", "XML"):
        assert f"FormatHint.{member_name}" not in src, (
            f"select_format_aware must not hard-code FormatHint.{member_name}; "
            f"the dispatch is supposed to be member-agnostic"
        )
    assert "in field.format_hints" in src


def test_step_note_carries_format_hint_value() -> None:
    _register_default_format_extractors()
    field = _field(format_hints=(FormatHint.CSV,))
    steps = select_format_aware(field)
    assert "format-aware" in steps[0].note
    assert "csv" in steps[0].note


def test_skips_capability_when_field_type_not_accepted() -> None:
    """A capability declares ``input_types=("STRING", ...)``. If the
    field's type is not in that set, the capability is skipped —
    even if the format hint matches. This pins the tier-1
    input-type filter invariant."""
    _register_default_format_extractors()
    field = _field(  # type: ignore[arg-type]
        type=FieldType.INTEGER, format_hints=(FormatHint.CSV,)
    )
    assert select_format_aware(field) == []

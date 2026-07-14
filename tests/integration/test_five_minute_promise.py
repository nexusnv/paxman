"""CI gate for the 5-Minute Promise (spec §4.1).

Extracts the fenced python block from README.md's Quickstart section,
asserts it is byte-equal to quickstart.py (modulo docstring), exec()s
it, and asserts the output shape contains the expected lines. A fresh
empty registry is monkeypatched in to prove the novice-did-nothing path
works.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

import paxman
from paxman import _orchestrator_runtime
from paxman._capabilities.registry import CapabilityRegistry


@pytest.fixture(autouse=True)
def _fresh_empty_registry(monkeypatch: pytest.MonkeyPatch):
    """Fresh empty registry for the novice-did-nothing path.

    monkeypatch.setattr (NOT a hypothetical reset()/clear() method —
    none exists on CapabilityRegistry; spec §4.1).
    """
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", CapabilityRegistry())
    yield


def _extract_readme_quickstart_block() -> str:
    readme = pathlib.Path("README.md").read_text(encoding="utf-8")
    # Match the fenced ```python block in the Quickstart section.
    # The Quickstart heading is '## Quickstart'. We grab everything in
    # the first ```python ... ``` block after that heading.
    quickstart_start = readme.find("## Quickstart")
    assert quickstart_start != -1, "README.md has no '## Quickstart' section"
    block_start = readme.find("```python", quickstart_start)
    assert block_start != -1, "no ```python block in Quickstart"
    block_end = readme.find("```", block_start + len("```python"))
    assert block_end != -1, "no closing ``` for the Quickstart code block"
    block_content = readme[block_start + len("```python"):block_end]
    return block_content.strip("\n")


def _read_quickstart_file() -> str:
    """Return quickstart.py with the docstring stripped (so the README
    fenced block, which has no docstring, can be byte-equal to it)."""
    qs = pathlib.Path("quickstart.py").read_text(encoding="utf-8")
    # Strip the leading docstring (the first string literal at module
    # top level). The README fenced block has no docstring; the file
    # does. Removing the docstring lets the two be byte-equal.
    tree = ast.parse(qs)
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            segment = ast.get_source_segment(qs, node)
            if segment is not None:
                qs_no_doc = qs.replace(segment, "", 1).strip("\n")
                return qs_no_doc
    return qs.strip("\n")


class TestFiveMinutePromise:
    def test_readme_block_byte_equals_quickstart_py(self) -> None:
        readme_block = _extract_readme_quickstart_block()
        quickstart = _read_quickstart_file()
        # The README fenced block should be byte-equal to quickstart.py
        # (modulo the docstring the file has and the block doesn't —
        # spec §3.2). Single source of truth.
        assert readme_block == quickstart, (
            f"README Quickstart block and quickstart.py drifted:\n"
            f"--- README ---\n{readme_block}\n--- quickstart.py ---\n{quickstart}\n"
        )

    def test_quickstart_runs_and_outputs_expected_shape(self, capsys) -> None:
        # exec() the README Quickstart block (== quickstart.py).
        block = _extract_readme_quickstart_block()
        exec(compile(block, "<readme-quickstart>", "exec"), {})
        captured = capsys.readouterr()
        assert "CANONICALIZED ->" in captured.out, (
            f"expected 'CANONICALIZED ->' in output; got:\n{captured.out}"
        )
        assert "evidence:" in captured.out, (
            f"expected 'evidence:' in output; got:\n{captured.out}"
        )
        assert "replay ok" in captured.out, (
            f"expected 'replay ok' in output; got:\n{captured.out}"
        )

    def test_quickstart_artifact_round_trips_byte_equal(self) -> None:
        # Re-run the quickstart by import, then assert replay equality.
        from paxman import Email

        result = paxman.canonicalize(
            "  John.Doe@Gmail.COM  ",
            Email(provider_aliases="gmail"),
        )
        rehydrated = paxman.replay(result, Email(provider_aliases="gmail"))
        assert rehydrated == result
        assert rehydrated.canonical_bytes() == result.canonical_bytes()

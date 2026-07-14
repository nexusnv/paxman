"""Grep-zero gate for the substring 'paxman.normalize'.

Spec §4.7 + §1.1: the substring 'paxman.normalize' must appear ZERO
times in src/paxman/. This includes the teaching error message
string in src/paxman/__init__.py (phrased to avoid the substring).
The §1.1 identity boundary is mechanically enforced.

Note: the substring DOES appear in tests/ — specifically, in
tests/unit/test_normalize_teaching_error.py, where the assertion
'paxman.normalize' not in str(exc_info.value) necessarily contains
the substring as a string literal. That is the only legitimate use
of the substring in the repo.
"""

from __future__ import annotations

import pathlib


def _iter_python_files(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def test_paxman_normalize_substring_absent_from_src() -> None:
    src = pathlib.Path("src/paxman")
    offenders: list[str] = []
    for path in _iter_python_files(src):
        text = path.read_text(encoding="utf-8")
        if "paxman.normalize" in text:
            offenders.append(str(path))
    assert not offenders, (
        "the substring 'paxman.normalize' appears in these src files: " + ", ".join(offenders)
    )

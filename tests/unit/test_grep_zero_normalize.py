"""Thin pytest gate: the substring 'paxman.normalize' is absent from
src/paxman/.

The actual grep-zero check lives in scripts/check_paxman_normalize_substring.py
— per the path instructions, tests under tests/ must not read files
from outside tests/, and the src/ tree lives at the repo root, not
under tests/. This thin pytest module just invokes the script via
subprocess.run and asserts the exit code is 0.

The substring IS allowed to appear in tests/ — specifically, in
tests/unit/test_normalize_teaching_error.py, where the assertion
'paxman.normalize' not in str(exc_info.value) necessarily contains
the substring as a string literal. That is the only legitimate use
of the substring in the repo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_paxman_normalize_substring.py"


def test_paxman_normalize_substring_absent_from_src() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"scripts/check_paxman_normalize_substring.py failed:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK:" in result.stdout

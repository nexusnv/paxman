"""Thin pytest gate: README's Quickstart code block is byte-equal to
quickstart.py (modulo the docstring the file has and the block doesn't).

The actual byte-equal comparison lives in scripts/check_readme_quickstart.py
— per the path instructions, tests under tests/ must not read files
from outside tests/, and the README lives at the repo root, not under
tests/. This thin pytest module just invokes the script via
subprocess.run and asserts the exit code is 0.

The script's existence + the subprocess invocation in this test
together form the CI gate: a failure of either is a test failure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_readme_quickstart.py"


def test_readme_quickstart_block_matches_quickstart_py() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"scripts/check_readme_quickstart.py failed:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK:" in result.stdout

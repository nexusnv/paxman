"""Thin pytest gate: 'Capability' appears in README only under
'## Extending Paxman'.

The actual check lives in scripts/check_capability_section_isolation.py
— per the path instructions, tests under tests/ must not read files
from outside tests/, and the README lives at the repo root, not under
tests/. This thin pytest module just invokes the script via
subprocess.run and asserts the exit code is 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_capability_section_isolation.py"


def test_capability_appears_only_in_extending_section() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"scripts/check_capability_section_isolation.py failed:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK:" in result.stdout

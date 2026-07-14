"""CI gate: the substring 'paxman.normalize' does not appear in any
src/paxman/ Python file.

The teaching AttributeError in src/paxman/__init__.py is phrased with
'the normalize name' and 'canonicalize()' precisely to slip through this
gate without losing its teaching power.

Per path instructions, the substring IS allowed to appear in tests/ —
specifically, in tests/unit/test_normalize_teaching_error.py, where the
assertion 'paxman.normalize' not in str(exc_info.value) necessarily
contains the substring as a string literal. That is the only legitimate
use of the substring in the repo.

Per path instructions, tests under tests/ must not read files from
outside tests/. The src/ check therefore lives in this script (run from
the repo root), not as a pytest test.

Exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import pathlib
import sys


def main() -> int:
    src = pathlib.Path("src/paxman")
    offenders: list[str] = []
    for path in src.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "paxman.normalize" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    if offenders:
        sys.exit(
            "FAIL: the substring 'paxman.normalize' appears in these src files: "
            + ", ".join(offenders)
        )
    print("OK: 'paxman.normalize' is absent from src/paxman/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

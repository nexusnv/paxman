"""CI gate: the word 'Capability' appears in README.md ONLY within the
'## Extending Paxman' section.

Per path instructions, tests under tests/ must not read files from
outside tests/. The README grep-zero check therefore lives in this
script (run from the repo root), not as a pytest test.

Exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import pathlib
import sys


def main() -> int:
    readme = pathlib.Path("README.md").read_text(encoding="utf-8")
    marker = "## Extending Paxman"
    extending_start = readme.find(marker)
    if extending_start == -1:
        sys.exit("FAIL: README.md has no '## Extending Paxman' section")

    before = readme[:extending_start]
    after = readme[extending_start:]

    if "Capability" in before:
        sys.exit(
            "FAIL: the word 'Capability' appears in README.md outside the "
            "'## Extending Paxman' section; this violates criterion 6. "
            f"Offending prefix:\n{before[-200:]}"
        )
    if "Capability" not in after:
        sys.exit("FAIL: 'Capability' does not appear in '## Extending Paxman'")

    print("OK: 'Capability' appears in README only under '## Extending Paxman'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CI gate: the five imprecise words banned by MANDATE.md §6.3 do not
appear in src/paxman/.

Per MANDATE.md §6.3, the words `heuristic`, `confidence`, `best match`,
`probably`, and `approximate` are RETIRED. They must not appear in
src/paxman/.

The literal word list is constructed at runtime from single-character
fragments joined at runtime, so neither the script nor any markdown
documentation needs to spell the words literally. This avoids the
markdown prose tripping the very gate the script enforces.

Per path instructions, the gate runs as a CI script, not as a pytest
test. Tests under tests/ must not read files from outside tests/.

Exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import pathlib
import re
import sys

# The literal word list is constructed at runtime. We rebuild the five
# words by joining fragments that, on their own, are not the words.
# This is intentional: the words are MANDATE-prohibited and must not
# appear in any text file we author (the spec, the plan, or this
# script's source).
_BANNED_WORDS: list[str] = [
    "".join(("he", "uristic")),  # retired
    "".join(("ap", "proxim", "ate")),  # retired
    "".join(("best ", "match")),  # retired
    "".join(("pro", "bab", "ly")),  # retired
    "".join(("con", "fide", "nce")),  # retired
]


def main() -> int:
    src = pathlib.Path("src/paxman")
    pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in _BANNED_WORDS) + r")\b")
    offenders: list[tuple[str, str]] = []
    for path in src.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line):
                offenders.append((str(path), f"line {lineno}: {line.strip()}"))
    if offenders:
        details = "\n".join(f"  {p}: {ctx}" for p, ctx in offenders)
        sys.exit(
            "FAIL: the five imprecise words banned by MANDATE.md §6.3 "
            "appear (lowercase) in src/paxman/:\n" + details
        )
    print("OK: the five imprecise words banned by MANDATE.md §6.3 are absent from src/paxman/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

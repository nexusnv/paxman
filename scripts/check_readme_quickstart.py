"""CI gate: README's Quickstart code block is byte-equal to quickstart.py.

Per path instructions, tests under tests/ must not read files from
outside tests/. The README↔quickstart.py sync check therefore lives in
this script (run from the repo root), not as a pytest test.

The script:
1. Extracts the fenced python block from README.md's Quickstart section.
2. Strips the leading docstring from quickstart.py (the README fenced
   block has no docstring; the file does).
3. Asserts the two are byte-equal.
4. Optionally exec()s the README block to assert the output shape.

Exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import ast
import pathlib
import sys


def _extract_readme_quickstart_block(readme: str) -> str:
    quickstart_start = readme.find("## Quickstart")
    if quickstart_start == -1:
        sys.exit("FAIL: README.md has no '## Quickstart' section")
    block_start = readme.find("```python", quickstart_start)
    if block_start == -1:
        sys.exit("FAIL: no ```python block in Quickstart")
    block_end = readme.find("```", block_start + len("```python"))
    if block_end == -1:
        sys.exit("FAIL: no closing ``` for the Quickstart code block")
    return readme[block_start + len("```python") : block_end].strip("\n")


def _read_quickstart_without_docstring(quickstart: str) -> str:
    tree = ast.parse(quickstart)
    for node in tree.body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            segment = ast.get_source_segment(quickstart, node)
            if segment is not None:
                return quickstart.replace(segment, "", 1).strip("\n")
    return quickstart.strip("\n")


def main() -> int:
    readme_text = pathlib.Path("README.md").read_text(encoding="utf-8")
    quickstart_text = pathlib.Path("quickstart.py").read_text(encoding="utf-8")

    readme_block = _extract_readme_quickstart_block(readme_text)
    quickstart_block = _read_quickstart_without_docstring(quickstart_text)

    if readme_block != quickstart_block:
        sys.exit(
            "FAIL: README Quickstart block and quickstart.py drifted:\n"
            f"--- README ---\n{readme_block}\n--- quickstart.py ---\n{quickstart_block}\n"
        )
    print("OK: README Quickstart block == quickstart.py (modulo docstring)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

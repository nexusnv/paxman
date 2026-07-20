from __future__ import annotations

import ast
import pathlib

from paxman._core import validation as validation_module
from paxman._core.validation import validate


def test_core_validation_does_not_import_capabilities() -> None:
    src = pathlib.Path(validation_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not node.module or "paxman._capabilities." not in (node.module or ""), (
                f"validation.py imports from _capabilities: {node.module}"
            )


def test_validate_dispatches_without_core_importing_contracts() -> None:
    from paxman import Email

    result = validate("johndoe@gmail.com", Email())
    assert result.is_valid is True

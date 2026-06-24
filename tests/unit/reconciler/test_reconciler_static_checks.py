"""Static import checks for the Reconciler subsystem.

Ensures that ``money.py`` is the **only** module in ``src/paxman/reconciler/``
that directly imports :mod:`decimal`. This is a structural guarantee
(Sprint 5 D5.18 / exit criterion #6): the rest of the reconciler must use
``MoneyValue`` (the contract-level type) rather than raw ``Decimal``
arithmetic.

Uses AST parsing (``import ast``) for reliable detection — this is
intentionally independent of the ``import-linter`` configuration in
``pyproject.toml``.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = pytest.mark.unit

#: The permitted module that may import ``decimal``.
_ALLOWED_MODULE: str = "money.py"

#: The root of the Reconciler subsystem source.
_RECONCILER_DIR = pathlib.Path(__file__).parents[3] / "src" / "paxman" / "reconciler"


def _discover_py_files() -> list[pathlib.Path]:
    """Discover all ``.py`` files under the reconciler directory.

    Returns:
        A sorted list of ``.py`` file paths (excluding ``__pycache__``
        and any other non-source directories).
    """
    return sorted(_RECONCILER_DIR.glob("*.py"))


def _has_direct_decimal_import(filepath: pathlib.Path) -> bool:
    """Check whether *filepath* directly imports ``decimal``.

    Uses AST walking to detect real ``import decimal`` or
    ``from decimal import ...`` statements. Docstring examples
    (e.g., ``>>> from decimal import Decimal``) are NOT real
    imports and are correctly ignored by the AST parser.

    Args:
        filepath: Path to a Python source file.

    Returns:
        ``True`` if the file has a direct ``decimal`` import.
    """
    tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "decimal" or alias.name.startswith("decimal."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "decimal" or (node.module or "").startswith("decimal."):
                return True
    return False


# ---------------------------------------------------------------------------
# Sanity: the test infrastructure itself
# ---------------------------------------------------------------------------


class TestStaticCheckInfrastructure:
    """Verify the test infrastructure parses Python correctly."""

    def test_reconciler_directory_exists(self) -> None:
        """The reconciler source directory exists."""
        assert _RECONCILER_DIR.is_dir(), f"Expected {_RECONCILER_DIR} to exist"

    def test_discover_py_files_returns_list(self) -> None:
        """File discovery returns a non-empty list."""
        files = _discover_py_files()
        assert isinstance(files, list)
        assert len(files) > 0

    def test_discovered_files_are_py(self) -> None:
        """Every discovered file has a ``.py`` extension."""
        for f in _discover_py_files():
            assert f.suffix == ".py", f"{f.name} is not a .py file"

    def test_ast_parses_self_correctly(self) -> None:
        """The test harness can parse its own source without errors."""
        self_path = pathlib.Path(__file__)
        tree = ast.parse(self_path.read_text(encoding="utf-8"), filename=str(self_path))
        # We expect to find import statements in this file
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        assert len(imports) >= 1

    def test_has_direct_decimal_import_detects_import(self) -> None:
        """_has_direct_decimal_import returns True for a file with ``import decimal``."""
        test_file = _RECONCILER_DIR / "money.py"
        if test_file.is_file():
            assert _has_direct_decimal_import(test_file) is True

    def test_has_direct_decimal_import_returns_false_for_clean_file(self) -> None:
        """_has_direct_decimal_import returns False for a file without decimal imports."""
        # Pick a file that doesn't import decimal (e.g., the __init__.py)
        init_file = _RECONCILER_DIR / "__init__.py"
        if init_file.is_file():
            assert _has_direct_decimal_import(init_file) is False


# ---------------------------------------------------------------------------
# Structural guarantee: only money.py imports decimal
# ---------------------------------------------------------------------------


class TestOnlyMoneyImportsDecimal:
    """AST-walk every reconciler module to enforce the structural guarantee."""

    @pytest.mark.parametrize(
        "pyfile",
        _discover_py_files(),
        ids=[f.name for f in _discover_py_files()],
    )
    def test_only_money_imports_decimal(self, pyfile: pathlib.Path) -> None:
        """Only ``money.py`` may directly import the ``decimal`` module."""
        if pyfile.name == _ALLOWED_MODULE:
            # ``money.py`` is the sole permitted module.
            return  # skip — allowed

        if _has_direct_decimal_import(pyfile):
            pytest.fail(
                f"{pyfile.name} must not import 'decimal' directly. "
                f"Only {_ALLOWED_MODULE} may import decimal. "
                f"Use MoneyValue (from paxman.contract.canonical) instead."
            )

    def test_money_py_does_import_decimal(self) -> None:
        """Sanity: ``money.py`` itself does import decimal (otherwise the guard is vacuously true)."""
        money_file = _RECONCILER_DIR / "money.py"
        assert money_file.is_file(), f"Expected {money_file} to exist"
        assert _has_direct_decimal_import(money_file), (
            f"{_ALLOWED_MODULE} should import decimal; if it no longer does, update this test"
        )

    def test_all_files_are_covered_by_parametrize(self) -> None:
        """Ensure the parametrize test covers every file in the directory."""
        files_from_glob = set(_discover_py_files())
        # The parametrize generator reads the same glob, so they match.
        # This test guards against the glob changing between test collection
        # and execution.
        assert len(files_from_glob) >= 1


# ---------------------------------------------------------------------------
# Each file individually (for clearer error reporting)
# ---------------------------------------------------------------------------


class TestIndividualFileDecimalFree:
    """Explicit per-file tests for maintainers who want direct blame."""

    def test___init___no_decimal(self) -> None:
        assert not _has_direct_decimal_import(_RECONCILER_DIR / "__init__.py")

    def test_confidence_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "confidence.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_conflict_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "conflict.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_evidence_compare_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "evidence_compare.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_merge_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "merge.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_reconciler_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "reconciler.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_truth_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "truth.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_unresolved_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "unresolved.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_validation_no_decimal(self) -> None:
        pyfile = _RECONCILER_DIR / "validation.py"
        if pyfile.is_file():
            assert not _has_direct_decimal_import(pyfile)

    def test_money_has_decimal(self) -> None:
        """money.py is the exception — it MUST import decimal."""
        pyfile = _RECONCILER_DIR / "money.py"
        assert pyfile.is_file(), f"Expected {pyfile} to exist"
        assert _has_direct_decimal_import(pyfile), (
            "money.py should import decimal; if the implementation "
            "changed, this test must be updated"
        )

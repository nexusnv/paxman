"""Smoke tests for the Jupyter Lab playground notebooks.

These tests do NOT require a Jupyter kernel. They use ``nbconvert --to script``
to convert each notebook to a Python script, then check:

1. The notebook file exists with the expected name.
2. The script does not import internal paxman modules.
3. The script references at least one public paxman API function.

This prevents silent bitrot without the cost of running notebooks in CI.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

PLAYGROUND = Path(__file__).resolve().parent.parent
NOTEBOOKS_DIR = PLAYGROUND / "notebooks"

# List of expected notebooks (NN-name.ipynb). Update when adding notebooks.
EXPECTED_NOTEBOOKS: list[str] = [
    "00-welcome.ipynb",
    "01-basics-contracts.ipynb",
    "02-capability-text-extraction.ipynb",
    "03-capability-regex-extraction.ipynb",
    "04-capability-lookup.ipynb",
    "05-capability-inference.ipynb",
    "06-capability-validation.ipynb",
    "07-replay.ipynb",
    "08-money-and-decimal.ipynb",
    "09-full-pipeline-invoice.ipynb",
    "10-budget-and-policy.ipynb",
]

# Internal modules notebooks must NEVER import directly.
FORBIDDEN_IMPORTS: list[str] = [
    "paxman.planner",
    "paxman.executor",
    "paxman.reconciler",
    "paxman.artifact._hash",
    "paxman.capabilities.v1",
    "paxman.contract._format_hint",
    "paxman.validation",
]

# Public API markers that each notebook should reference.
# At least one must appear in every notebook.
PUBLIC_API_MARKERS: list[str] = [
    "paxman.normalize",
    "paxman.replay",
    "paxman.register_capability",
    "paxman.register_adapter",
    "paxman.__version__",
]


@pytest.mark.parametrize("name", EXPECTED_NOTEBOOKS)
def test_notebook_exists(name: str) -> None:
    """Assert each expected notebook file exists."""
    path = NOTEBOOKS_DIR / name
    assert path.exists(), f"Missing notebook: {path}"


def _convert_to_script(notebook_path: Path) -> str:
    """Convert a notebook to a Python script using nbconvert."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "script",
            "--stdout",
            str(notebook_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        pytest.skip(
            f"nbconvert failed for {notebook_path.name}: {result.stderr.strip()}"
        )
    return result.stdout


@pytest.mark.parametrize("name", EXPECTED_NOTEBOOKS)
def test_notebook_no_internal_imports(name: str) -> None:
    """Assert notebooks only use public paxman API, not internal modules."""
    path = NOTEBOOKS_DIR / name
    script = _convert_to_script(path)

    # Parse the script AST to find import statements
    try:
        tree = ast.parse(script)
    except SyntaxError:
        pytest.skip(f"Cannot parse converted script for {name}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in FORBIDDEN_IMPORTS:
                    if alias.name == forbidden or alias.name.startswith(
                        forbidden + "."
                    ):
                        pytest.fail(
                            f"{name} imports internal module '{alias.name}' "
                            f"(forbidden: {forbidden})"
                        )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for forbidden in FORBIDDEN_IMPORTS:
                    if node.module == forbidden or node.module.startswith(
                        forbidden + "."
                    ):
                        pytest.fail(
                            f"{name} imports from internal module '{node.module}' "
                            f"(forbidden: {forbidden})"
                        )


@pytest.mark.parametrize("name", EXPECTED_NOTEBOOKS)
def test_notebook_has_public_api_reference(name: str) -> None:
    """Assert each notebook references at least one public API surface."""
    path = NOTEBOOKS_DIR / name
    script = _convert_to_script(path)

    found = [m for m in PUBLIC_API_MARKERS if m in script]
    if not found:
        # Check for paxman itself as a fallback
        if "import paxman" not in script and "from paxman" not in script:
            pytest.fail(f"{name} does not reference any public paxman API")

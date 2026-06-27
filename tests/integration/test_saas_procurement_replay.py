"""D10.7: Cross-run replay_hash reproducibility via saas_procurement example.

This top-level integration test verifies that the ``saas_procurement``
example produces byte-equal ``replay_hash`` and full artifact JSON across
two independent Python subprocess invocations.

Runs as part of ``make test-integration`` (top-level test suite).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

# Path to the saas_procurement example.
_EXAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "examples" / "saas_procurement"
_MANIFEST_PATH = _EXAMPLE_DIR / "data" / "manifest.csv"

# Use the example's own .venv (has paxman + saas_procurement pre-installed).
_EXAMPLE_PYTHON = _EXAMPLE_DIR / ".venv" / "bin" / "python"


@pytest.fixture(scope="module")
def example_python() -> Path:
    """Return the saas_procurement example's Python interpreter.

    The example's ``.venv`` has ``paxman`` and ``saas_procurement``
    installed.  If the ``.venv`` is missing or broken, the test skips
    (the example is not expected to be available in all environments).
    """
    python = _EXAMPLE_PYTHON
    if not python.exists():
        pytest.skip(f"Example .venv not found at {python}")

    # Verify the interpreter can import saas_procurement + paxman.
    result = subprocess.run(  # noqa: S603
        [str(python), "-c", "import saas_procurement; import paxman"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(
            f"Example .venv at {python} cannot import "
            f"saas_procurement/paxman: {result.stderr.strip()}"
        )
    return python


def _run_saas_procurement(
    example_python: Path,
    output_dir: Path,
) -> subprocess.CompletedProcess:
    """Run the saas_procurement example once in a subprocess.

    Args:
        example_python: Path to the example's Python interpreter.
        output_dir: Directory where artifacts will be written.

    Returns:
        The completed subprocess result.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # cwd is set to the example root so relative paths in the
    # manifest resolve correctly.
    return subprocess.run(  # noqa: S603
        [
            str(example_python),
            "-m",
            "saas_procurement",
            str(_MANIFEST_PATH),
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(_EXAMPLE_DIR),
        timeout=60,
    )


_ARTIFACT_NAMES = (
    "invoice_acme.json",
    "invoice_globex.json",
    "quotation_initech.json",
)


@pytest.mark.integration
@pytest.mark.deterministic
@pytest.mark.replay
class TestSaasProcurementReplayHash:
    """D10.7: Verify replay_hash reproducibility via saas_procurement example."""

    def test_replay_hash_deterministic_across_subprocesses(
        self,
        example_python: Path,
        tmp_path: Path,
    ) -> None:
        """Two subprocess runs of saas_procurement produce identical replay_hash."""
        output1 = tmp_path / "run1"
        output2 = tmp_path / "run2"

        _run_saas_procurement(example_python, output1)
        _run_saas_procurement(example_python, output2)

        for artifact_name in _ARTIFACT_NAMES:
            path1 = output1 / artifact_name
            path2 = output2 / artifact_name

            assert path1.exists(), f"Missing artifact in run1: {path1}"
            assert path2.exists(), f"Missing artifact in run2: {path2}"

            artifact1 = json.loads(path1.read_text(encoding="utf-8"))
            artifact2 = json.loads(path2.read_text(encoding="utf-8"))

            assert artifact1["replay_hash"] == artifact2["replay_hash"], (
                f"D10.7 FAIL: replay_hash not deterministic for {artifact_name}. "
                f"Run 1: {artifact1['replay_hash']!r}, "
                f"Run 2: {artifact2['replay_hash']!r}"
            )

    def test_artifact_json_byte_equal(
        self,
        example_python: Path,
        tmp_path: Path,
    ) -> None:
        """Full artifact JSON is byte-equal across two subprocess runs."""
        output1 = tmp_path / "byte_run1"
        output2 = tmp_path / "byte_run2"

        _run_saas_procurement(example_python, output1)
        _run_saas_procurement(example_python, output2)

        for artifact_name in _ARTIFACT_NAMES:
            data1 = (output1 / artifact_name).read_text(encoding="utf-8")
            data2 = (output2 / artifact_name).read_text(encoding="utf-8")
            assert data1 == data2, f"D10.7 FAIL: {artifact_name} not byte-equal between two runs."

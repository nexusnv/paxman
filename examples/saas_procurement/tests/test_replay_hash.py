"""D10.7: Cross-run replay_hash reproducibility tests.

This test module is the gating test for D10.7.  It verifies that two
independent ``paxman.normalize()`` calls on the same input produce a
byte-equal ``replay_hash``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from saas_procurement import run_pipeline


class TestReplayHashDeterminism:
    """Verify replay_hash reproducibility across runs."""

    def test_replay_hash_is_deterministic(
        self,
        sample_manifest_path: Path,
        tmp_path: Path,
    ) -> None:
        """Two in-process runs produce identical replay_hash values."""
        output1 = tmp_path / "run1"
        output2 = tmp_path / "run2"
        output1.mkdir()
        output2.mkdir()

        run_pipeline(sample_manifest_path, output1)
        run_pipeline(sample_manifest_path, output2)

        artifact1 = json.loads((output1 / "invoice_acme.json").read_text(encoding="utf-8"))
        artifact2 = json.loads((output2 / "invoice_acme.json").read_text(encoding="utf-8"))

        assert artifact1["replay_hash"] == artifact2["replay_hash"], (
            "D10.7 FAIL: replay_hash not deterministic across in-process runs. "
            f"hash A: {artifact1['replay_hash']!r}, "
            f"hash B: {artifact2['replay_hash']!r}"
        )

    def test_replay_hash_is_stable_across_subprocess_runs(
        self,
        sample_manifest_path: Path,
        tmp_path: Path,
    ) -> None:
        """Two subprocess runs produce identical replay_hash values."""
        output1 = tmp_path / "sub_run1"
        output2 = tmp_path / "sub_run2"

        manifest_str = str(sample_manifest_path)

        result1 = subprocess.run(
            [sys.executable, "-m", "saas_procurement", manifest_str, str(output1)],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        result2 = subprocess.run(
            [sys.executable, "-m", "saas_procurement", manifest_str, str(output2)],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )

        assert result1.returncode == 0, f"Subprocess 1 failed: {result1.stderr}"
        assert result2.returncode == 0, f"Subprocess 2 failed: {result2.stderr}"

        artifact1 = json.loads((output1 / "invoice_acme.json").read_text(encoding="utf-8"))
        artifact2 = json.loads((output2 / "invoice_acme.json").read_text(encoding="utf-8"))

        assert artifact1["replay_hash"] == artifact2["replay_hash"], (
            "D10.7 FAIL: replay_hash not stable across subprocess runs. "
            f"hash A: {artifact1['replay_hash']!r}, "
            f"hash B: {artifact2['replay_hash']!r}"
        )

    def test_replay_data_is_byte_equal(
        self,
        sample_manifest_path: Path,
        tmp_path: Path,
    ) -> None:
        """The full artifact JSON is byte-equal between two runs."""
        output1 = tmp_path / "byte_run1"
        output2 = tmp_path / "byte_run2"
        output1.mkdir()
        output2.mkdir()

        run_pipeline(sample_manifest_path, output1)
        run_pipeline(sample_manifest_path, output2)

        for name in ("invoice_acme.json", "invoice_globex.json", "quotation_initech.json"):
            data1 = (output1 / name).read_text(encoding="utf-8")
            data2 = (output2 / name).read_text(encoding="utf-8")
            assert data1 == data2, f"D10.7 FAIL: {name} not byte-equal between two runs."

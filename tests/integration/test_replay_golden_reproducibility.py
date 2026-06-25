"""Replay golden reproducibility test (D7.16).

Per Sprint 7 D7.16 and exit criterion #6, this test verifies that
a real fixture's artifact, when replayed, produces the same
``replay_hash`` across two separate Python invocations.

The test runs the same normalization + replay in two subprocesses
(so that the GIL, the random state, and any module-level
caches are fresh) and asserts the ``replay_hash`` is identical.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import paxman

# Trigger auto-registration.
import paxman.contract.adapters.dict_dsl  # noqa: F401

_INPUT = "ACME Corp\nInvoice #1234\nTotal: $1,234.56\nDate: 2026-06-22"
_CONTRACT_PATH = "tests.fixtures.contracts.dict_dsl.invoice:DICT_DSL_INVOICE"


_SUBPROCESS_SCRIPT = textwrap.dedent(
    f"""
    import sys
    import os
    # Add tests/ to sys.path so we can import the fixture contract.
    sys.path.insert(0, os.path.abspath('tests'))

    import paxman
    import paxman.contract.adapters.dict_dsl

    from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE
    artifact = paxman.normalize(
        input_data={_INPUT!r},
        contract=DICT_DSL_INVOICE,
    )
    print('REPLAY_HASH:' + artifact.replay_hash)
    """
)


def _run_subprocess_normalize() -> str:
    """Run the normalize step in a fresh Python subprocess and return the hash."""
    # The subprocess command is built from a hard-coded string (no
    # untrusted input), so S603 (subprocess call) is safe.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _SUBPROCESS_SCRIPT],
        capture_output=True,
        text=True,
        cwd=".",
        check=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("REPLAY_HASH:"):
            return line[len("REPLAY_HASH:") :]
    raise RuntimeError(
        f"Subprocess did not produce REPLAY_HASH line. stdout={result.stdout!r}, stderr={result.stderr!r}"
    )


def test_replay_golden_reproducible_across_subprocesses() -> None:
    """Two subprocess invocations of normalize produce the same ``replay_hash``."""
    # Run the same script twice in two separate subprocesses.
    hash_1 = _run_subprocess_normalize()
    hash_2 = _run_subprocess_normalize()
    # The hashes must be identical across subprocesses.
    assert hash_1 == hash_2
    # And each must be a valid 64-char hex string.
    assert len(hash_1) == 64
    assert all(c in "0123456789abcdef" for c in hash_1)


def test_replay_golden_reproducible_in_subprocess_vs_in_process() -> None:
    """A subprocess's hash matches an in-process normalize's hash.

    This is a stricter form of D7.16: not only is the
    cross-subprocess hash stable, but the subprocess hash
    also matches the in-process hash (proving the subprocess
    isn't using a different default).
    """
    import paxman
    import paxman.contract.adapters.dict_dsl
    from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE

    in_process = paxman.normalize(input_data=_INPUT, contract=DICT_DSL_INVOICE)
    in_process_hash = in_process.replay_hash

    subprocess_hash = _run_subprocess_normalize()

    assert in_process_hash == subprocess_hash

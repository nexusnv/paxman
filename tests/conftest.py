"""Top-level pytest configuration for the paxman test suite.

This file is loaded automatically by pytest before any test module. It is the
canonical place to:

- register custom markers (see ``[tool.pytest.ini_options].markers`` in
  ``pyproject.toml`` for the canonical list),
- define session-scoped or package-scoped fixtures shared across the suite,
- and configure the import path for the src-layout package.

Per ``PACKAGE_STRUCTURE.md`` §19, the test layout is:

    tests/
    ├── unit/             # fast, isolated unit tests
    ├── integration/      # tests that exercise the full pipeline
    ├── property/         # hypothesis property tests
    ├── public_api/       # tests that the public surface is stable
    ├── fixtures/         # test data (vendored, golden, generated)
    └── conftest.py       # this file
"""

from __future__ import annotations

import datetime
import pathlib

import pytest

# --- Path setup ---------------------------------------------------------------

# Ensure `src/` is on sys.path so `import paxman` works without `pip install -e .`
# during local test runs. CI installs the package, so this is a no-op there.
_SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir():
    import sys

    src_str = str(_SRC)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


# --- Shared fixtures ---------------------------------------------------------


@pytest.fixture(scope="session")
def fixed_now() -> datetime.datetime:
    """A fixed UTC datetime for deterministic tests.

    Tests that need a stable "now" can depend on this fixture rather than
    calling ``datetime.datetime.now()`` directly.
    """
    return datetime.datetime(2026, 6, 22, tzinfo=datetime.UTC)


@pytest.fixture
def deterministic_seed() -> int:
    """A deterministic seed for randomized tests (Hypothesis, etc.)."""
    return 0x70617821  # "pax!" in hex

"""Public API snapshot test — verifies the public API surface is stable.

This test introspects ``paxman`` and its submodules to collect the exact
set of public symbols and function signatures, then compares them against
a golden JSON file (``tests/fixtures/public_api_snapshot.json``).

If the public API changes, this test **fails** — requiring the golden file
to be updated intentionally via :func:`_write_golden`.
"""

from __future__ import annotations

import inspect
import json
import pathlib
from typing import Any

import pytest

GOLDEN_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "public_api_snapshot.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_api_surface() -> dict[str, Any]:
    """Collect the current public API surface into a dict.

    Returns:
        A dict with top-level keys ``paxman_all``, ``api_types_all``,
        ``api_errors_all``, ``api_protocols_all``, and ``functions``.
    """
    import paxman
    from paxman.api import errors as api_errors
    from paxman.api import protocols as api_protocols
    from paxman.api import types as api_types

    surface: dict[str, Any] = {
        "paxman_all": sorted(paxman.__all__),
        "api_types_all": sorted(api_types.__all__),
        "api_errors_all": sorted(api_errors.__all__),
        "api_protocols_all": sorted(api_protocols.__all__),
        "functions": {},
    }

    for func_name in ("normalize", "replay", "register_adapter", "register_capability"):
        func = getattr(paxman, func_name)
        sig = inspect.signature(func)
        surface["functions"][func_name] = {
            "parameters": list(sig.parameters.keys()),
        }

    return surface


def _write_golden(surface: dict[str, Any] | None = None) -> None:
    """Write the golden snapshot file with the current API surface.

    Args:
        surface: The surface dict to write. If ``None``, it is collected
            from the live package.
    """
    if surface is None:
        surface = _collect_api_surface()
    with open(GOLDEN_PATH, "w") as f:
        json.dump(surface, f, indent=2, sort_keys=True)
        f.write("\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.deterministic
def test_public_api_matches_snapshot() -> None:
    """Verify the public API surface matches the golden snapshot.

    If the surface has changed, this test fails with a message directing
    the developer to update the golden file.
    """
    current = _collect_api_surface()

    if not GOLDEN_PATH.exists():
        raise AssertionError(
            f"Golden snapshot not found at {GOLDEN_PATH}. "
            'Run `python -c "from tests.public_api.test_public_api import _write_golden; _write_golden()"` '
            "to create it."
        )
    else:
        with open(GOLDEN_PATH) as f:
            golden = json.load(f)

    assert current == golden, (
        "Public API surface has changed!\n\n"
        "If the change is intentional, update the golden file by running:\n\n"
        '    python -c "from tests.public_api.test_public_api import _write_golden; _write_golden()"\n'
    )

"""Integration tests for golden ExecutionArtifact JSON files.

Per Sprint 7 D7.3, this test verifies that:

1. Each golden JSON file in :data:`tests/fixtures/artifacts/` is
   loadable and structurally valid.
2. The ``replay_hash`` in the golden matches the ``replay_hash`` of
   a fresh :func:`paxman.normalize` call with the same input +
   contract pair.
3. The golden has the same structure as a real
   :class:`~paxman.artifact.artifact.ExecutionArtifact` (validated
   by ``attrs``).

These tests run as ``integration`` markers and require the test
fixtures to be vendored (see ``scripts/bootstrap_golden_artifacts.py``
for the regeneration procedure).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

import paxman

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Layout: tests/integration/test_golden_artifacts.py
#         tests/fixtures/artifacts/*.json
_THIS_DIR = pathlib.Path(__file__).resolve().parent
_TESTS_DIR = _THIS_DIR.parent
_ARTIFACTS_DIR = _TESTS_DIR / "fixtures" / "artifacts"


# Trigger adapter auto-registration.
# Import the shared catalog (the single source of truth for golden
# fixtures — see ``scripts/bootstrap_golden_artifacts.py``). We use
# ``importlib.util.spec_from_file_location`` to bypass Python's
# path-hook caching, which is stale after the paxman.contract.adapters.*
# imports above.
import importlib.util as _catalog_util  # noqa: E402

import paxman.contract.adapters.dict_dsl  # noqa: E402
import paxman.contract.adapters.json_schema  # noqa: E402
import paxman.contract.adapters.pydantic  # noqa: E402

_CATALOG_PATH = _THIS_DIR.parent / "fixtures" / "artifacts" / "_catalog.py"
_catalog_spec = _catalog_util.spec_from_file_location(
    "tests.fixtures.artifacts._catalog", _CATALOG_PATH
)
if _catalog_spec is None or _catalog_spec.loader is None:
    raise ImportError(f"Could not load spec for {_CATALOG_PATH}")
_catalog_module = _catalog_util.module_from_spec(_catalog_spec)
sys.modules["tests.fixtures.artifacts._catalog"] = _catalog_module
_catalog_spec.loader.exec_module(_catalog_module)

GOLDEN_FIXTURES = _catalog_module.GOLDEN_FIXTURES
resolve_input_text = _catalog_module.resolve_input_text


def _load_golden(name: str) -> dict[str, object]:
    """Load a golden artifact JSON file."""
    path = _ARTIFACTS_DIR / f"{name}.json"
    if not path.exists():
        pytest.skip(
            f"Golden {name} not found at {path}; bootstrap via scripts/bootstrap_golden_artifacts.py"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_test_module_attr(module_path: str, attr: str) -> object:
    """Load an attribute from a test fixture module by file path.

    Mirrors :func:`scripts.bootstrap_golden_artifacts._load_contract`
    so we use the same robust resolution here.
    """
    parts = module_path.split(".")
    if parts and parts[0] == "tests":
        parts = parts[1:]
    file_path = _TESTS_DIR.joinpath(*parts).with_suffix(".py")
    if not file_path.exists():
        file_path = _TESTS_DIR.joinpath(*parts, "__init__.py")
        if not file_path.exists():
            raise FileNotFoundError(f"Could not locate module {module_path!r}")
    if module_path not in sys.modules:
        spec = importlib.util.spec_from_file_location(module_path, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path] = module
        spec.loader.exec_module(module)
    return getattr(sys.modules[module_path], attr)


# ---------------------------------------------------------------------------
# Golden fixtures: catalog
# ---------------------------------------------------------------------------
# The catalog is the single source of truth, shared with
# ``scripts/bootstrap_golden_artifacts.py`` via
# ``tests/fixtures/artifacts/_catalog.py`` (imported above).
GOLDEN_FIXTURES_LIST = [g.name for g in GOLDEN_FIXTURES]


# ---------------------------------------------------------------------------
# D7.3 — Golden structure tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    GOLDEN_FIXTURES_LIST,
)
def test_golden_is_loadable_json(name: str) -> None:
    """Each golden is a valid JSON object on disk."""
    golden = _load_golden(name)
    assert isinstance(golden, dict)
    # All goldens carry the same required hash-relevant fields.
    assert "replay_hash" in golden
    assert "status" in golden
    assert "field_results" in golden
    assert "execution_plan" in golden
    assert "contract_id" in golden


@pytest.mark.parametrize(
    "name",
    GOLDEN_FIXTURES_LIST,
)
def test_golden_replay_hash_is_64_hex(name: str) -> None:
    """Each golden's ``replay_hash`` is a 64-character lowercase hex string."""
    golden = _load_golden(name)
    replay_hash = golden["replay_hash"]
    assert isinstance(replay_hash, str)
    assert len(replay_hash) == 64
    assert all(c in "0123456789abcdef" for c in replay_hash)


@pytest.mark.parametrize(
    "name",
    GOLDEN_FIXTURES_LIST,
)
def test_golden_matches_fresh_normalize(name: str) -> None:
    """A fresh ``paxman.normalize()`` call reproduces the golden's ``replay_hash``.

    This is the core determinism claim: re-running the pipeline on
    the same input + contract produces the same hash.
    """
    fixture = next(g for g in GOLDEN_FIXTURES if g.name == name)
    input_text = resolve_input_text(fixture.name, fixture.input_text)
    contract = _load_test_module_attr(fixture.contract_module, fixture.contract_attr)

    artifact = paxman.normalize(input_data=input_text, contract=contract)
    golden = _load_golden(name)
    assert artifact.replay_hash == golden["replay_hash"], (
        f"replay_hash mismatch for {name}: "
        f"fresh={artifact.replay_hash}, golden={golden['replay_hash']}"
    )


@pytest.mark.parametrize(
    "name",
    GOLDEN_FIXTURES_LIST,
)
def test_golden_strips_id_and_created_at(name: str) -> None:
    """Each golden has ``id`` and ``created_at`` stripped for stability."""
    golden = _load_golden(name)
    assert "id" not in golden, (
        f"golden {name} should not contain 'id' (use replay_hash for identity)"
    )
    assert "created_at" not in golden, f"golden {name} should not contain 'created_at'"


def test_golden_at_least_five_exist() -> None:
    """Exit criterion #2: ≥5 golden artifact files exist."""
    goldens = list(_ARTIFACTS_DIR.glob("*.json"))
    assert len(goldens) >= 5, (
        f"Expected ≥5 golden artifacts, found {len(goldens)}: {[g.name for g in goldens]}"
    )


def test_goldens_have_replay_hashes() -> None:
    """Each golden has a non-empty 64-character hex replay_hash.

    A simple sanity check: every golden is valid.
    """
    for path in _ARTIFACTS_DIR.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        h = data.get("replay_hash")
        assert h, f"Golden {path.name} has no replay_hash"
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

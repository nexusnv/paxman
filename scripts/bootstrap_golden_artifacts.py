#!/usr/bin/env python
"""Bootstrap golden ``ExecutionArtifact`` JSON files from real ``paxman.normalize()`` calls.

Per Sprint 7 D7.3, golden artifacts are **bootstrapped from real runs**
(not predicted). This script:

1. Calls ``paxman.normalize(input, contract)`` for each curated fixture
   in :data:`GOLDEN_FIXTURES`.
2. Strips the non-hash-relevant fields (``id``, ``created_at``) so the
   golden file is reproducible across Paxman versions.
3. Serializes the artifact to JSON via
   :func:`paxman.artifact.serializer.encode_artifact` (stable encoder).
4. Writes the file to :data:`GOLDENS_DIR`.

Each golden is committed to ``tests/fixtures/artifacts/`` and verified
by ``tests/integration/test_golden_artifacts.py``.

The script is idempotent: re-running it produces the same JSON (modulo
``id`` / ``created_at``, which are stripped).

Usage::

    uv run python scripts/bootstrap_golden_artifacts.py

To regenerate a single golden (e.g., after a bug fix in the artifact
shape)::

    uv run python scripts/bootstrap_golden_artifacts.py --only invoice_unresolved_dict_dsl

See ``tests/fixtures/artifacts/GENERATION.md`` for the full procedure.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import pathlib
import sys
import typing

# Ensure ``src/`` and ``tests/`` are on ``sys.path`` so the script can
# run from a fresh checkout without ``pip install -e .``. We use
# ``sys.path`` insertion (not ``os.chdir``) to avoid mutating the
# process-wide working directory.
_REPO_ROOT_FOR_PATH = pathlib.Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT_FOR_PATH / "src"
_TESTS_DIR = _REPO_ROOT_FOR_PATH / "tests"

_SRC_DIR_STR = str(_SRC_DIR)
if _SRC_DIR_STR not in sys.path:
    sys.path.insert(0, _SRC_DIR_STR)

_TESTS_DIR_STR = str(_TESTS_DIR)
if _TESTS_DIR_STR not in sys.path:
    sys.path.insert(0, _TESTS_DIR_STR)

import paxman

# Use the stable encoder so the JSON is deterministic and handles
# enums, Decimals, datetimes, etc. correctly.
from paxman.serialization import stable_dumps

# Trigger auto-registration for the Dict DSL and Pydantic adapters.
import paxman.contract.adapters.dict_dsl
import paxman.contract.adapters.json_schema  # noqa: F401
import paxman.contract.adapters.pydantic  # noqa: F401
import paxman.contract.adapters.openapi  # noqa: F401
from paxman.artifact.artifact import ExecutionArtifact
from paxman.artifact.serializer import encode_artifact

# Repository root: this script lives in ``scripts/`` next to the package
# root, so we resolve relative to ``__file__``.
_THIS_DIR = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
_GOLDENS_DIR = _REPO_ROOT / "tests" / "fixtures" / "artifacts"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures"

# ---------------------------------------------------------------------------
# Golden fixture catalog
# ---------------------------------------------------------------------------
#
# The catalog is shared with ``tests/integration/test_golden_artifacts.py``
# via :mod:`tests.fixtures.artifacts._catalog` to prevent drift.
#
# We load the catalog via ``importlib.util.spec_from_file_location``
# to bypass Python's path-hook caching (which is stale after the
# paxman.contract.adapters.* imports above). This is the same
# approach used by ``_load_contract`` below.

import importlib.util as _catalog_util

_catalog_path = _TESTS_DIR / "fixtures" / "artifacts" / "_catalog.py"
_catalog_spec = _catalog_util.spec_from_file_location(
    "tests.fixtures.artifacts._catalog", _catalog_path
)
if _catalog_spec is None or _catalog_spec.loader is None:
    raise ImportError(f"Could not load spec for {_catalog_path}")
_catalog_module = _catalog_util.module_from_spec(_catalog_spec)
sys.modules["tests.fixtures.artifacts._catalog"] = _catalog_module
_catalog_spec.loader.exec_module(_catalog_module)

GOLDEN_FIXTURES = _catalog_module.GOLDEN_FIXTURES
resolve_input_text = _catalog_module.resolve_input_text


def _load_contract(module_path: str, attr: str) -> object:
    """Import *module_path* (a test fixture dotted path) and return *attr*.

    We use :func:`importlib.util.spec_from_file_location` to load the
    fixture module from its file path. This bypasses the
    ``sys.path``-based module finder, which is unreliable when this
    script is invoked from outside the repo root.

    *module_path* is rooted at ``tests/`` (e.g.,
    ``tests.fixtures.contracts.dict_dsl.invoice``). We strip the
    ``tests.`` prefix and resolve the rest relative to
    :data:`_TESTS_DIR`.
    """
    parts = module_path.split(".")
    if parts and parts[0] == "tests":
        parts = parts[1:]
    file_path = _TESTS_DIR.joinpath(*parts).with_suffix(".py")
    if not file_path.exists():
        # Try as a package (directory with __init__.py).
        file_path = _TESTS_DIR.joinpath(*parts, "__init__.py")
        if not file_path.exists():
            raise FileNotFoundError(
                f"Could not locate module {module_path!r} (looked at {file_path})"
            )

    # Build a list of fully-qualified module names from the top of the
    # test tree down to the leaf, and load each one in order. This
    # ensures that ``from tests.fixtures.contracts.json_schema.invoice
    # import ...`` style imports inside fixture modules work.
    full_parts = ["tests", *parts[:-1]]  # e.g. ['tests', 'fixtures', 'contracts', 'dict_dsl']
    leaf = parts[-1]
    full_module_path = ".".join([*full_parts, leaf])

    # Load each package along the path so that submodule_search_locations
    # is correctly populated. The leaf (file) is loaded last.
    running: list[str] = []
    for piece in full_parts:
        running.append(piece)
        running_path = ".".join(running)
        if running_path not in sys.modules:
            pkg_path = _TESTS_DIR.joinpath(*running[1:])  # drop "tests"
            pkg_init = pkg_path / "__init__.py"
            if not pkg_init.exists():
                continue  # Implicit namespace package; fine.
            spec = importlib.util.spec_from_file_location(
                running_path, pkg_init, submodule_search_locations=[str(pkg_path)]
            )
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[running_path] = module
            spec.loader.exec_module(module)

    # Now load the leaf.
    if full_module_path not in sys.modules:
        spec = importlib.util.spec_from_file_location(full_module_path, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {full_module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_path] = module
        spec.loader.exec_module(module)
    return getattr(sys.modules[full_module_path], attr)


def _strip_non_hash_fields(artifact: ExecutionArtifact) -> dict[str, typing.Any]:
    """Convert *artifact* to a dict and strip non-hash-relevant fields.

    The :attr:`ExecutionArtifact.id` and
    :attr:`ExecutionArtifact.created_at` are *not* part of the
    :func:`~paxman.artifact._hash.compute_replay_hash` and would
    otherwise differ across Paxman versions and across runs in the
    same version. Stripping them yields a stable JSON golden.

    Uses :func:`encode_artifact` to match the public encoding path
    so the bootstrap output is byte-equal to what
    :func:`paxman.artifact.serializer.encode_artifact` produces.
    """
    # ``encode_artifact`` returns a JSON string. Parse it back to a
    # dict so we can pop the non-hash-relevant fields.
    import json

    json_str = encode_artifact(artifact)
    raw = json.loads(json_str)
    raw.pop("id", None)
    raw.pop("created_at", None)
    return raw


def _bootstrap_one(name: str, input_text: str, module: str, attr: str) -> dict[str, typing.Any]:
    """Bootstrap a single golden artifact, returning the JSON-ready dict."""
    input_text = resolve_input_text(name, input_text)
    contract = _load_contract(module, attr)
    artifact = paxman.normalize(input_data=input_text, contract=contract)
    return _strip_non_hash_fields(artifact)


def bootstrap_all(only: str | None = None) -> dict[str, str]:
    """Bootstrap all goldens (or the one named *only*), writing to disk.

    Returns:
        A mapping from golden name to its written file path.
    """
    _GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    fixtures = GOLDEN_FIXTURES
    if only is not None:
        fixtures = [g for g in fixtures if g.name == only]
        if not fixtures:
            raise SystemExit(
                f"Unknown golden: {only!r}. Available: "
                f"{[g.name for g in GOLDEN_FIXTURES]}"
            )
    for fixture in fixtures:
        print(f"  bootstrapping {fixture.name}…", file=sys.stderr)
        data = _bootstrap_one(
            fixture.name,
            fixture.input_text,
            fixture.contract_module,
            fixture.contract_attr,
        )
        path = _GOLDENS_DIR / f"{fixture.name}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(stable_dumps(data))
            f.write("\n")
        written[fixture.name] = str(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap golden ExecutionArtifact JSON files from real runs."
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Regenerate only the named golden (e.g., invoice_unresolved_dict_dsl).",
    )
    args = parser.parse_args()
    written = bootstrap_all(only=args.only)
    print(f"Bootstrapped {len(written)} golden artifact(s):", file=sys.stderr)
    for name, path in written.items():
        print(f"  {name}: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

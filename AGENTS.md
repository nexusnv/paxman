# AGENTS.md

Agent-focused guidance for working in this repository. Complements
`README.md`, `MANDATE.md`, `ARCHITECTURE.md`, and `CODING_GUIDELINES.md`. The
deeper constitutional rules (the thirteen laws, the three invariants, the SPI
contract) live in those documents — read them before any non-trivial change.
`CODING_GUIDELINES.md` summarizes the practical engineering practices and
recurring review lessons; load it as context at the start of any agent session.

## Project Overview

Paxman is a **deterministic canonicalization engine** for Python. It rewrites
equivalent representations of *known* information into a single canonical form
and refuses to guess when the input does not determine a unique result.

**⚠️ Active Development — No Backward Compatibility:** Paxman v2 is in active
development. There is no v2 release yet, and v1 is not a concern of v2. In any
implementation or design planning, **never concern yourself with backward
compatibility**. Doing so creates redundant mechanisms that circumvent
compatibility issues that do not exist and never will. This development has
only one path: **forward**. Until v2 is released, there is no looking backward.

- **Language:** Python 3.11–3.13 (`requires-python = ">=3.11"`).
- **Package manager / runner:** [`uv`](https://docs.astral.sh/uv/) (`uv sync`, `uv run`).
- **Build backend:** Hatchling.
- **Only runtime dependency:** `attrs` (the `frozen=True` dataclass backbone).
- **Type checking:** `mypy` (moderate config, not `--strict`).
- **Lint + format:** `ruff` (line-length 100).
- **Tests:** `pytest` + `hypothesis` (property tests).

### The three invariants (MANDATE §1.2)

Every core change must preserve:

1. **Identity** — canonicalize only; never interpret, infer, or orchestrate.
2. **Determinism** — same input + contract + registered capabilities + config + version → same artifact.
3. **Replay** — `replay(artifact, contract) == artifact` byte-for-byte, without re-executing the capability.

The property tests in `tests/property/` are the mechanical evidence. A change
that breaks a property test broke an invariant.

## Setup Commands

```bash
git clone https://github.com/nexusnv/paxman.git
cd paxman
uv sync                 # create the venv and install dev + all-extras deps
uv run python quickstart.py   # smoke-test the public API
```

All commands below are run through `uv run` so they execute inside the
project venv. There is **no `make` target** in this tree — CI runs each gate
as a discrete `uv run …` command (see `ci.yml`).

## Local Development / CI Gate

Run **every** command below before opening a pull request. These mirror the
jobs in `.github/workflows/ci.yml` exactly:

```bash
uv run ruff check .                                      # lint
uv run ruff format --check .                             # format check (not auto-fix)
uv run lint-imports                                      # import boundary check
uv run mypy src/paxman                                   # type check
uv run python scripts/check_readme_quickstart.py         # README ↔ quickstart parity
uv run python scripts/check_capability_section_isolation.py
uv run python scripts/check_paxman_normalize_substring.py
uv run python scripts/check_retired_vocabulary.py        # banned words must not appear in src/paxman/
uv run pytest tests/unit --no-header                     # unit tests (multi-version in CI)
uv run pytest -m property --no-header                    # property tests (invariants)
uv run pytest tests/integration --no-header              # end-to-end public-API tests
```

To auto-fix formatting: `uv run ruff format .` (do not use `ruff check --fix`
silently — review every fix). To run a single test file or node:

```bash
uv run pytest tests/unit/test_email_grammar.py -q
uv run pytest tests/unit -k "test_lowercase" -q
```

## Testing Instructions

```text
tests/
  unit/         # fast, isolated unit tests (the required core gate)
  property/     # Hypothesis property tests — evidence for the three invariants
  integration/  # end-to-end exercise of the public API surface
```

- **Markers** (defined in `pyproject.toml`): `property`, `integration`.
  Use `-m property` / `-m integration` to select. The suite runs with
  `-ra --strict-markers` — every marker used in code must be registered.
- **Property tests are deterministic**: they use `hypothesis` with
  `derandomize=True` (mandate Law 1). Do not add randomness.
- **Coverage gate is per-subpackage ≥90%** (not a global threshold). Each of
  `_capabilities`, `_core`, `_dsl`, `_registry`, `_types`, `_errors` must
  independently stay ≥90% line coverage. CI enforces it with
  `coverage report --fail-under=90 --include="*/paxman/<pkg>/*"`.
  When adding code, add tests that cover your subpackage.
- Keep `tests/` out of coverage (already omitted in `pyproject.toml`).

## Architecture Orientation

```
src/paxman/
  _capabilities/        # the ONLY extension point — one package per domain
    protocol.py         # Capability protocol (can_handle / canonicalize)
    discovery.py        # builtin_capabilities() — source of truth
    _iso3166.py         # shared ISO 3166-1:2020 dataset
    _shared/            # shared recognition/evidence/contract scaffold
      grammar/          # Grammar, RecognizedRep, recognize_grammars
      evidence.py       # make_evidence / make_evidence_for
      contract.py       # authority_override_field
    email/  date/  uuid/ phone/ url/ boolean/ ip/ money/ geolocation/ country/
  _core/                # engine.py (canonicalize), replay.py, artifact.py,
                        # status.py, provenance.py, result.py, contracts.py,
                        # engine_env.py (Engine), validation.py, classification.py
  _provenance/          # authority editions, evidence, bundled datasets
    specs/              # RFC/ISO spec definitions
    registries/         # ISO 3166, ISO 4217, CLDR, ITU E.164
    behaviour/          # documented platform behavior
  _dsl/                 # contract DSL parser + serializer
  _registry/            # capability_registry.py (freezes on first canonicalize)
                        # contract_registry.py (kind → builder dispatch)
  _types/               # shared value types
  _errors/              # exception hierarchy
  _orchestrator_runtime.py
  __init__.py           # public API surface
```

**Public API** (top-level, in `paxman/__init__.py`):

- `paxman.canonicalize(input_data, contract) -> ExecutionArtifact`
- `paxman.canonicalize_with(input_data, contract, engine) -> ExecutionArtifact`
- `paxman.replay(artifact, contract) -> ExecutionArtifact`
- `paxman.register_capability(cap)` — must be called **before** the first
  `canonicalize` in the process (the registry freezes afterward and raises
  `FrozenRegistryError`).
- Contracts: `Email`, `Date`, `UUID`, `Boolean`, `IP`, `URL`, `Phone`,
  `Money`, `Geolocation`, `Country` (and their `Canonical*` forms).
  `parse_contract` for the DSL. Errors re-exported from `_errors`.
- `Engine` — the immutable `name -> Authority` binding that selects concrete
  authority editions (Concern 3). `Engine.default()` resolves active editions
  (what zero-config `canonicalize` uses); `Engine.with_authorities({...})`
  pins specific editions; `canonicalize_with(input, contract, engine)` is the
  engine-pinned entry point. A contract's `authority_override` pins one edition
  for a single call. `Edition(id)` / `Latest` are the selection values.

**Hard boundaries:**

- The pipeline (engine + replay) is **owned by Paxman**; contributors may not
  redefine it. Contribute a *capability*, not a pipeline change.
- `src/paxman/` modules under `_capabilities/<domain>/` are the supported
  place to add a new canonical type. Mirror an existing domain package's shape.

## Code Style

- Python 3.11+ syntax. Target `requires-python = ">=3.11"`.
- Type hints on **every public symbol** in `src/paxman/`.
- Docstrings on **every public symbol**. Plain prose style (Google/NumPy not
  required).
- **Forbidden in `src/paxman/`:**
  - `# type: ignore` and `as any` (type-error suppression).
  - `# noqa` of any kind.
  - The words retired by `scripts/check_retired_vocabulary.py` (the exact
    banned list lives in that script — do not re-list them here, or the words
    risk re-entering `src/paxman/`). It runs in CI and will fail the build.
- Test code may use `# noqa: S101` for asserts and `# noqa: B011` for
  `assertRaises(Exception)`.
- `attrs` frozen dataclasses are the canonical value-type form. Prefer them
  over mutable containers and over `dataclasses.dataclass` for core types.
- No network I/O, no LLM path, no parallelism — by design. Determinism is a
  library property, not an opt-out default.

## Commit & Pull Request Conventions

- **Commit style** (observed in history): `<type>(<scope>): <summary>`, e.g.
  `fix(date): remove banned word from grammar provenance`,
  `refactor(email): purify resolution layer`, `feat(date): add grammar
  recognition layer`. Types seen: `feat`, `fix`, `refactor`, `docs`, `chore`.
- Scope is the domain/package touched (`email`, `date`, `uuid`, `core`, `ci`,
  `docs`, …).
- Keep the working tree's in-flight work intact: don't reformat or touch files
  you weren't asked to change. One logical change per commit/PR.
- PRs target `main`. The PR template mirrors the CI gate list above.

## Gotchas & Troubleshooting

- **`uv sync` fails / stale lockfile:** the lockfile (`uv.lock`) is authoritative
  and pinned. After editing `[dependency-groups]` or `[project].dependencies`,
  run `uv lock` then `uv sync`. CI installs with `uv sync --frozen`, so the
  lockfile must stay consistent with `pyproject.toml`.
- **Registry frozen error:** if `register_capability` raises
  `FrozenRegistryError`, a `canonicalize` already ran in this process. Register
  all custom capabilities at import time, before any canonicalization.
- **Coverage drop on a new subpackage:** adding a file to a `_*` package pulls
  it into the ≥90% gate. Add tests alongside the code.
- **Retired-vocabulary CI failure:** search `src/paxman/` for the banned words;
  the `check_retired_vocabulary.py` script names them. Replace with
  mandate-compliant vocabulary (e.g. "resolver" not "planner").
- **`mypy` disabled codes:** `assignment`, `attr-defined`, `arg-type` are
  intentionally allowed (structural `_ContractLike` Protocol + attrs). Don't
  "fix" these by adding `# type: ignore`; the config already permits them.
- **Docs live in `docs/`** (`concepts/`, `how-to/`) and the constitutional docs
  `MANDATE.md` / `ARCHITECTURE.md` at the root. `CODING_GUIDELINES.md` at
  the root summarizes the practical engineering practices and recurring review
  lessons. Consult them before design questions.

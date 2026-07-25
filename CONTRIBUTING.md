# Contributing to Paxman

Paxman is a deterministic canonicalization engine. It is small, slow to
change, and specific about what it is. This document covers the minimum a
contributor needs to know; the deeper rationale lives in `MANDATE.md` and
`ARCHITECTURE.md`.

## The Shape of a Contribution

Paxman accepts two kinds of contributions:

- **Capabilities** — pure, deterministic transformations that satisfy a
  contract. A capability is the only extension point of Paxman. The full
  guidance for writing one is in
  [Concepts: Capabilities and the SPI](docs/concepts/capabilities-and-spi.md)
  and the worked example in
  [How-to: Write a compliant capability](docs/how-to/write-a-compliant-capability.md).
- **Core changes** — additions to the orchestrator, the registry, the
  artifact, the error hierarchy, or the contract vocabulary. These touch
  the parts of the library Paxman owns (not the parts the user owns) and
  must preserve the three invariants in `MANDATE.md` §1.2: identity,
  determinism, and replay.

## The Three Invariants

Every change to the core must preserve:

1. **Identity** — Paxman only canonicalizes; it never interprets, infers,
   or orchestrates.
2. **Determinism** — same input, contract, registered capabilities,
   configuration, and Paxman version produce the same artifact.
3. **Replay** — `replay(artifact, contract) == artifact` byte-for-byte,
   without re-executing the capability.

The property tests in `tests/property/` are the mechanical evidence for
these invariants. A change that breaks a property test is a change that
broke an invariant.

## Local Development

```bash
git clone https://github.com/nexusnv/paxman.git
cd paxman
uv sync
```

The full CI gate (the same checks `ci.yml` runs):

```bash
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
uv run mypy src/paxman
uv run python scripts/check_readme_quickstart.py
uv run python scripts/check_capability_section_isolation.py
uv run python scripts/check_paxman_normalize_substring.py
uv run python scripts/check_retired_vocabulary.py
uv run pytest tests/unit --no-header
uv run pytest -m property --no-header
uv run pytest tests/integration --no-header
```

Every command must pass before opening a pull request. The pull request
template mirrors this list.

## Code Style

- Python 3.11+ syntax. The project targets `requires-python = ">=3.11"`.
- Type hints on every public symbol in `src/paxman/`.
- Docstrings on every public symbol. The format is plain prose; the
  project does not enforce Google or NumPy style.
- No `# type: ignore` or `as any` in `src/paxman/`.
- No `# noqa` in `src/paxman/`. Test code may use `# noqa: S101` for
  asserts.
- The five words retired by `scripts/check_retired_vocabulary.py`
  must not appear in `src/paxman/`. The check runs in CI.

## Where to Ask

- **A question about the design** — read `MANDATE.md` and `ARCHITECTURE.md`
  first. Most questions are answered there.
- **A bug** — open an issue using the bug report template. Include the
  Paxman version, the Python version, the operating system, and a minimal
  reproducer.
- **A feature suggestion** — open an issue using the feature request
  template. Identify whether the change is within Paxman's identity
  boundary.
- **A security vulnerability** — follow the disclosure process in
  `SECURITY.md`. Do not open a public issue.

# Pull Request

> **Before opening a PR**, please read
> [`CONTRIBUTING.md`](./CONTRIBUTING.md) and
> [`SECURITY.md`](./SECURITY.md).

## Summary

<!-- One-paragraph description of the change. -->

## Type of change

<!-- Check one. -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that breaks existing behavior)
- [ ] Documentation update
- [ ] Refactor (no behavior change)
- [ ] Test update
- [ ] Build / CI / tooling

## How has this been tested?

<!-- Describe the tests you ran. Each command must pass before review. -->

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run mypy src/paxman`
- [ ] `uv run python scripts/check_readme_quickstart.py`
- [ ] `uv run python scripts/check_capability_section_isolation.py`
- [ ] `uv run python scripts/check_paxman_normalize_substring.py`
- [ ] `uv run python scripts/check_retired_vocabulary.py`
- [ ] `uv run pytest tests/unit --no-header`
- [ ] `uv run pytest -m property --no-header`
- [ ] `uv run pytest tests/integration --no-header`
- [ ] New unit tests added (describe below)
- [ ] New property tests added (describe below)
- [ ] New integration tests added (describe below)

## Checklist

- [ ] I have read
      [`CONTRIBUTING.md`](../CONTRIBUTING.md) and
      [`SECURITY.md`](../SECURITY.md).
- [ ] My code follows the project's style
      ([`CONTRIBUTING.md`](../CONTRIBUTING.md) §Code style).
- [ ] I have added docstrings for every public symbol in `src/paxman/`.
- [ ] I have added type hints on every public symbol in `src/paxman/`.
- [ ] I have not added any `# type: ignore` or `as any`
      to `src/paxman/`.
- [ ] I have not introduced any of the words retired by
      `scripts/check_retired_vocabulary.py` into `src/paxman/`.
- [ ] I have updated the relevant docs in `docs/`
      when behavior changed.
- [ ] For a new public symbol, I have added it to the relevant
      section of `docs/reference/`.
- [ ] For a new built-in capability, I have added a folder under
      `docs/capabilities/` with an `index.md` and a `changelog.md`.

## Public surface impact

<!-- If your change adds, removes, or modifies anything in
     `paxman.__all__` or any re-exported submodule, describe it.
     Otherwise write "no public surface changes". -->

- Symbols added: (or "none")
- Symbols removed: (or "none")
- Signatures changed: (or "none")

## Replay and determinism impact

<!-- If your change affects artifact immutability, the VersionStamp,
     capability resolution, or replay, describe it. Otherwise write
     "no replay/determinism impact". -->

- VersionStamp components touched: (or "none")
- New evidence rules: (or "none")

## Migration / backward compatibility

<!-- If your change is breaking, describe the migration path.
     Otherwise write "no breaking changes". -->

- Migration path: (or "no breaking changes")

## Additional context

<!-- Anything else that helps the reviewer. -->

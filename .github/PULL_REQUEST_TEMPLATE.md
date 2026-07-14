# Pull Request

> **Before opening a PR**, please read
> [`CONTRIBUTING.md`](./CONTRIBUTING.md) and
> [`SECURITY.md`](./SECURITY.md). Significant changes require an
> ADR (see [`docs/adr/README.md`](./docs/adr/README.md) "When to
> write an ADR").

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

## Related issue / ADR

<!-- Link the issue and the ADR (if any). -->

- Issue: #
- ADR: `docs/adr/NNNN-*.md` (or "n/a")

## How has this been tested?

<!-- Describe the tests you ran. -->

- [ ] `make lint`
- [ ] `make format-check`
- [ ] `make typecheck` (mypy --strict)
- [ ] `make typecheck-pyright` (pyright)
- [ ] `make imports` (import-linter)
- [ ] `make docs-check` (interrogate, 100% on public surface)
- [ ] `make security` (bandit)
- [ ] `make security-audit` (pip-audit)
- [ ] `make test-cov` (pytest with coverage; ≥ 90% lines on the
      four subsystems + ≥ 95% on `artifact/`)
- [ ] `make ci` (the full local-CI pipeline — 9 checks)
- [ ] New unit tests added (describe below)
- [ ] New property tests added (describe below)
- [ ] New integration tests added (describe below)

## Checklist

- [ ] I have read
      [`CONTRIBUTING.md`](./CONTRIBUTING.md),
      [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md), and
      [`SECURITY.md`](./SECURITY.md).
- [ ] My code follows the project's style (see
      [`DEVELOPMENT.md`](./DEVELOPMENT.md) §6 Code Style and §8
      Coding Style).
- [ ] I have added docstrings (Google style) for every public
      symbol.
- [ ] I have added type hints (mandatory on every public symbol).
- [ ] I have not added any `# type: ignore`, `# pyright: ignore`,
      or `as any` to `src/paxman/`.
- [ ] I have not added any `# noqa` to `src/paxman/`. (Test code
      may use `# noqa: S101` for asserts.)
- [ ] I have updated the relevant docs (`docs/concepts/`,
      `docs/howto/`, `EXTENDING.md`, `DEVELOPMENT.md`, or
      `README.md`).
- [ ] I have added a `CHANGELOG.md` entry under `[Unreleased]` in
      the appropriate section (`Added`, `Changed`, `Fixed`,
      `Deprecated`, `Removed`, `Security`).
- [ ] I have updated `tests/fixtures/public_api_snapshot.json` if
      the public API changed (use
      `python -c "from tests.public_api.test_public_api import _write_golden; _write_golden()"`).
- [ ] For significant changes, I have opened an ADR PR (or
      linked to an existing one).

## Subsystem boundary

<!-- If your change touches a subsystem boundary (imports, SPI,
     public surface), explain the impact. -->

- Subsystems touched: `contract/`, `planner/`, `capabilities/`,
  `executor/`, `reconciler/`, `artifact/`, `api/`
- Boundary rules verified: `make imports` (import-linter)

## Performance impact

<!-- If your change affects performance, include a before/after
     measurement. Otherwise, write "no measurable impact". -->

## Documentation impact

<!-- If your change affects documentation, list the files. Otherwise,
     write "no documentation changes needed". -->

## Migration / backward compatibility

<!-- If your change is breaking, describe the migration path. -->

- Migration path: (or "no breaking changes")
- Deprecation cycle: (or "n/a")

## Additional context

<!-- Anything else that helps the reviewer. -->

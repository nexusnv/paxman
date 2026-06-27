# Contributing to Paxman

> **Welcome!** Thank you for your interest in Paxman. This document
> describes how to set up a development environment, run the test
> suite, build the package, and contribute. It also describes the
> ADR-driven workflow that Paxman uses for significant changes.

Paxman is an **open-source** project licensed under **MIT** (per
[ADR-0008](../adr/0008-license-decision.md) and the
[license decision spec](https://github.com/nexusnv/paxman/wiki/Internal-Development/License-decision—full-analysis)). We
welcome contributions of all sizes — from typo fixes to new
subsystems.

---

## 1. Code of Conduct

Paxman has adopted the
[Contributor Covenant v2.1](./code-of-conduct.md). By participating,
you agree to abide by its terms. Please report unacceptable
behavior to the maintainers (see [§11](#11-contact)).

---

## 2. Quick start (TL;DR)

```bash
# 1. Fork and clone the repo
git clone https://github.com/<your-username>/paxman.git
cd paxman

# 2. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies (editable)
uv sync --all-extras --dev

# 4. Install pre-commit hooks
uv run pre-commit install

# 5. Verify
make ci    # the full local-CI pipeline (9 checks)

# 6. Open a PR on GitHub
```

If all 9 checks pass on your fork, you can open a PR against
`main`. The CI on GitHub Actions runs the same 9 checks.

---

## 3. When to write an ADR

Paxman uses [MADR](https://adr.github.io/madr/) (Markdown
Architectural Decision Records) for capturing significant
architectural decisions. Each ADR is short, decision-focused, and
immutable once Accepted.

Write an ADR when:

- Adding a new public API surface.
- Adding a new public SPI.
- Changing a system boundary rule.
- Adding a new dependency to the core.
- Changing the artifact format.
- Changing the replay model.
- Deprecating or removing public API.

Do not write an ADR for:

- Bug fixes.
- Refactors that don't change behavior or boundaries.
- Documentation updates.
- Internal naming.

The full list of ADRs and the template is in
[docs/adr/README.md](../adr/).

---

## 4. Development setup

### 4.1 Prerequisites

- **Python:** ≥ 3.11
- **Git:** for version control
- **uv** (recommended) or **pip** for package management
- **pre-commit** for git hooks
- **make** for running the common task runner (the repo ships a
  `Makefile`)

### 4.2 Install

```bash
# Clone your fork (replace <your-username> with your GitHub handle;
# the upstream URL is https://github.com/nexusnv/paxman.git).
# If you skipped the Quick start in §2, fork the repo first.
git clone https://github.com/<your-username>/paxman.git
cd paxman

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install package + dev dependencies (editable)
uv sync --all-extras --dev

# Install pre-commit hooks
uv run pre-commit install

# Verify
uv run pytest --co -q          # collect tests, don't run
uv run ruff check              # lint
uv run ruff format --check     # format
uv run mypy --strict src/paxman
```

### 4.3 The dev tools

Paxman uses:

- **`uv`** — fast Python package manager (PEP 621 + PEP 735).
- **`ruff`** — lint + format (single tool, two commands).
- **`mypy --strict`** — primary type checker.
- **`pyright`** — secondary type checker (advisory; for
  cross-validation).
- **`import-linter`** — enforces the module DAG.
- **`interrogate`** — 100% docstring coverage on the public
  surface.
- **`bandit`** — security lint.
- **`pip-audit`** — dependency vulnerability scan.
- **`hypothesis`** — property-based testing.
- **`pytest`** + **`pytest-cov`** + **`pytest-xdist`** — test runner.
- **`hatchling`** — build backend.

All tools are installed by `uv sync --all-extras --dev`.

---

## 5. The 9 CI checks

`make ci` runs all 9 local-CI checks in order:

| # | Check | Command | Purpose |
|---|---|---|---|
| 1 | `install-frozen` | `uv sync --frozen --all-extras --dev` | Install with the exact lockfile. |
| 2 | `lint` | `uv run ruff check .` | Lint (E/F/W/I/B/UP/ANN/ASYNC/S/RUF). |
| 3 | `format-check` | `uv run ruff format --check .` | Format check. |
| 4 | `typecheck` | `uv run mypy --strict src/paxman` | Strict mypy. |
| 5 | `typecheck-pyright` | `uv run pyright src/paxman` | Cross-validation (advisory in CI). |
| 6 | `imports` | `uv run lint-imports` | Module DAG enforcement. |
| 7 | `docs-check` | `uv run interrogate -vv src/paxman` | 100% docstring coverage on the public surface. |
| 8 | `security` | `uv run bandit -r src/paxman -c pyproject.toml` | Security lint (advisory in CI). |
| 9 | `test-cov` | `uv run pytest --cov=paxman ...` | Tests with coverage + per-subsystem threshold check. |

The order matters: install-frozen is first, then static checks
(lint, format, typecheck, typecheck-pyright, imports, docs-check),
then security, then tests. Each check is independent; you can
also run them individually (e.g. `make lint`).

The same 9 checks run on GitHub Actions CI (`.github/workflows/ci.yml`).

---

## 6. The contribution workflow

### 6.1 Fork and branch

Fork the repository on GitHub, then create a feature branch:

```bash
git checkout -b <type>/<scope>-<short-description>
```

`<type>` is one of:

- `feat` — a new feature
- `fix` — a bug fix
- `docs` — documentation only
- `chore` — build, CI, tooling
- `refactor` — behavior-preserving refactor
- `perf` — performance improvement
- `test` — adding or fixing tests

Examples:

- `feat/add-redis-cache-capability`
- `fix/planner-handles-empty-input`
- `docs/improve-replay-howto`

### 6.2 Make your changes

Edit the code, add tests, update docs. Run `make ci` locally before
opening the PR.

### 6.3 The PR template

The PR template is at
[https://github.com/nexusnv/paxman/blob/main/.github/PULL_REQUEST_TEMPLATE.md](https://github.com/nexusnv/paxman/blob/main/.github/PULL_REQUEST_TEMPLATE.md).
Fill it in. Include:

- A clear description of the change.
- A link to the relevant issue (if any).
- A list of the CI checks that pass.
- Screenshots (if the change is visual — Paxman has no UI in V1,
  but the website or docs may have visual changes).
- A confirmation that you have read
  [CODE_OF_CONDUCT.md](./code-of-conduct.md) and
  [SECURITY.md](../security/index.md).

### 6.4 Review

- At least one maintainer review is required.
- The CI must pass (all 9 checks).
- The PR must be up-to-date with `main` (rebase if needed).
- Sign the [Contributor License Agreement](#12-contributor-license-agreement)
  if your contribution is substantial (a CLA bot will guide you
  through the process if required).

### 6.5 Merge

Once the PR is approved and CI is green, a maintainer will merge
it. We use **squash-merge** by default; the commit message
follows the
[Conventional Commits](https://www.conventionalcommits.org/)
format.

---

## 7. The ADR-driven workflow

Significant changes start with an **ADR**. The flow:

1. **Open an issue** describing the change. Reference the
   `docs/adr/README.md` "When to write an ADR" checklist.
2. **Write the ADR** in `docs/adr/NNNN-<kebab-case-title>.md`
   using the MADR template.
3. **Open a PR** for the ADR. Get at least one maintainer review.
4. **Once the ADR is Accepted**, open implementation PRs that
   reference the ADR by number.

ADRs are immutable once Accepted. To reverse or refine a
decision, write a new ADR and mark the old one Superseded.

The full ADR list and template is in
[docs/adr/README.md](../adr/).

---

## 8. Coding style

### 8.1 Python

- **Type hints mandatory** on every public symbol.
- **`mypy --strict`** passes on the public surface
  (`paxman/__init__.py`, `paxman/api/**`).
- **No `# type: ignore`**, **no `# pyright: ignore`**, **no
  `as any`** in `src/paxman/`. CI rejects.
- **No `# noqa`** in `src/paxman/`. CI rejects. Test code may
  use `# noqa: S101` for asserts.
- **Google-style docstrings** for every public symbol.
- **Module docstrings** for every public module.

### 8.2 Naming

- `snake_case` for modules, functions, methods, variables.
- `PascalCase` for classes.
- `SCREAMING_SNAKE_CASE` for enums, statuses, bands, error codes.
- `_private` prefix for internal symbols.

### 8.3 Imports

- **No cross-subsystem imports.** The 9 cross-cutting modules at
  `paxman/` (errors, types, protocols, versioning, logging, budget,
  clock, ids, serialization) may NOT import from any subsystem
  layer.
- **Subsystem boundary rules** are enforced by `import-linter`. See
  [pyproject.toml](https://github.com/nexusnv/paxman/blob/main/pyproject.toml) for the full contract.

### 8.4 Tests

- **Unit tests** for every public function.
- **Property tests** for every deterministic algorithm.
- **Integration tests** for every cross-subsystem flow.
- **Replay-equality tests** for every artifact-producing path.
- **Test markers** — `deterministic`, `replay`, `property`, `slow`,
  `integration`, `unit`. Use them.

---

## 9. The Makefile

```bash
make help              # show all targets
make install           # install dev dependencies
make test              # run all tests
make test-unit         # run unit tests only
make test-property     # run hypothesis property tests only
make test-integration  # run integration tests only
make test-cov          # run tests with coverage
make lint              # run ruff check
make format            # run ruff format
make typecheck         # run mypy --strict
make typecheck-pyright # run pyright (cross-validation)
make imports           # run import-linter
make docs-check        # run interrogate (100% docstring coverage)
make security          # run bandit
make security-audit    # run pip-audit
make build             # build wheel and sdist
make ci                # run the local-CI pipeline (9 checks)
```

The full list is in [DEVELOPMENT.md](./development.md).

---

## 10. Security

If you find a security vulnerability, **do not open a public
GitHub issue**. See
[SECURITY.md §7](../security/index.md) for the vulnerability disclosure
process. Reports are acknowledged within 3 business days.

---

## 11. Contact

- **GitHub issues:** for bug reports, feature requests, and
  general questions. Use the templates in
  [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE/).
- **GitHub discussions:** for open-ended conversations, design
  questions, and announcements.
- **Security:** see [SECURITY.md §7](../security/index.md).
- **Maintainers:** see the [@nexusnv/paxman](https://github.com/orgs/nexusnv/people)
  org members. (A `MAINTAINERS.md` file will be added when the project
  transitions to a multi-maintainer model.)

---

## 12. Contributor License Agreement

Paxman is MIT-licensed. By submitting a pull request, you agree
that your contribution is licensed under the same MIT terms (see
[LICENSE](LICENSE)). No formal CLA is required for small
contributions.

For substantial contributions (a new subsystem, a new public SPI,
a new dependency), the maintainers may ask you to sign a CLA to
confirm the MIT terms. The CLA bot will guide you through the
process if required.

---

## 13. Recognition

Paxman uses an
[All Contributors](https://allcontributors.org/)-style
recognition. Substantial contributors are credited in release
notes ([`CHANGELOG.md`](../operations/changelog.md)). (An `AUTHORS.md` file will
be added when the project has its first external contributor.)

---

## 14. See also

- [README.md](https://github.com/nexusnv/paxman#readme) — project overview.
- [DEVELOPMENT.md](./development.md) — local dev setup, common
  tasks, release process.
- [EXTENDING.md](../reference/extending.md) — adding a new contract adapter,
  capability, or inference provider.
- [docs/adr/README.md](../adr/) — the ADR index and
  template.
- [SECURITY.md](../security/index.md) — vulnerability reporting.
- [TESTING_STRATEGY.md](./testing-strategy.md) — test strategy and
  patterns.
- [CODE_OF_CONDUCT.md](./code-of-conduct.md) — community standards.
- [CHANGELOG.md](../operations/changelog.md) — release notes.

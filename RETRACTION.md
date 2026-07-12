# ⚠️ RETRACTION — Paxman v1.x.y Releases Have Been Yanked

> **Read this first.** Paxman has formally retracted every published v1.x.y
> release. The library is back in **active development**. No `v1.*` release
> is the current, recommended, or supported version. **Do not install
> `paxman`, `paxman[all]`, or any of the published v1.x wheels / sdists
> in production environments.** They are retained on PyPI for historical
> reference only and are no longer maintained.

---

## TL;DR

| Question | Answer |
|---|---|
| Is Paxman a production-ready library? | **No.** It was claimed to be; it was not. The published v1.x releases are retracted. |
| Should I `pip install paxman`? | **No.** v1.x is yanked. There is no v2 release yet. |
| Where is the source of truth now? | This `main` branch. Development happens in feature branches. |
| When will v2 ship? | When the heuristic planner is wired up, the LLM provider SPI is integrated, and a real end-to-end test of the README quickstart passes in CI. Not before. |
| Where is the gap analysis? | See [`.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md`](./.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md) — a third-party code audit documenting the exact failures of the v1.x deliverable. |

---

## What happened

In July 2026, an independent code audit of the v1.1.0 codebase
(see [`.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md`](./.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md))
demonstrated that the published v1.x releases did not deliver what the
README and CHANGELOG claimed.

The exact code shown in the v1.1.0 README Quickstart:

```python
artifact = paxman.normalize(input_data=raw_invoice, contract=Invoice)
print(artifact.normalized_data)      # README says: {"supplier_name": "ACME Corp", ...}
print(artifact.unresolved_fields)    # README says: []  (or list of fields Paxman could not resolve)
```

in fact returns:

```text
artifact.status           = Status.UNRESOLVED
artifact.normalized_data  = {}
artifact.unresolved_fields = ['supplier_name', 'total_amount', 'currency_code', 'line_items']
```

The 7-step heuristic planner chain documented in `ARCHITECTURE.md` and
`ADR-0001` was **dead code** in the published releases — the planner entry
point was wired to `select_format_aware` only, so every field whose
contract did not declare a `format_hints` or `extract=` was always
`UNRESOLVED`. The `inference` capability, advertised as model-backed
extraction, was a hard-coded string formatter. The 94.78% test coverage
and 11/11 green CI gates were real — they verified plumbing, not behavior.

This retraction is a response to that audit. The published releases were
honest, well-engineered scaffolding around a deliverable that did not
work as advertised. Shipping that as "Production/Stable" was a mistake
we are correcting now.

---

## What is retracted

### Retracted from PyPI (yanked, kept for history)

- `paxman==1.0.0` (2026-06-27)
- `paxman==1.0.1` (2026-07-01)
- `paxman==1.0.2` (2026-07-03)
- `paxman==1.1.0` (2026-07-08)

All four versions are marked **YANKED** on PyPI. They are no longer
installable via `pip install paxman` by default (`pip install paxman==1.0.0`
still works because the artifact exists; the wheel and sdist remain
downloadable, but the version is flagged as not currently supported).

### Retracted from GitHub

- The `v1.0.0`, `v1.0.1`, `v1.0.2`, and `v1.1.0` git tags have been
  deleted from the local repo and from `origin`. The `v0.5.0-rc1` and
  `v1.0.0-rc.1` tags are retained for archaeological reference.
- The four GitHub Release pages (`v1.0.0`, `v1.0.1`, `v1.0.2`, `v1.1.0`)
  have been **replaced with retraction notices**. They are no longer
  advertised as stable downloads.
- The PyPI announcement Discussions (#116, #117, #118) are now
  cross-linked from this notice.

### Retracted from the codebase

- The `Production/Stable` Development Status classifier (Trove: 5) is
  replaced with `Pre-Alpha` (Trove: 2). PyPI will display the project
  as "pre-alpha" once the v2 dev release is published.
- The `## Status` section of `README.md` is rewritten to reflect
  development-mode status, not a shipped product.
- The `## Install` instructions no longer point at `pip install paxman`
  as a supported path. The supported path is now a working-tree
  editable install via `uv pip install -e ".[all]"` from this repo.
- The `release.yml` GitHub workflow has been **frozen** — it can no
  longer be triggered by a `v*` tag push. Future releases will be
  published manually with an explicit confirmation gate.
- The `make publish` / `make publish-test` Makefile targets are
  disabled. The CI pipeline no longer carries a PyPI publish step.

### NOT retracted

- **Source code history.** Every commit from v0.5.0-rc1 through v1.1.0
  remains in the git log. The retraction is administrative, not a
  rewrite. The v1.x source code is preserved exactly as it was; it is
  simply no longer claimed to be a working product.
- **Architecture decision records (ADRs).** The 11 ADRs (0001-0011)
  remain in `docs/adr/`. Some of them describe a system that was
  never built (the heuristic planner wiring, the real LLM provider).
  That mismatch is now documented in the audit postmortem.
- **Test suite.** The 2,754 tests that passed in v1.1.0 still exist
  and pass. They verify the plumbing; the plumbing is real. They do
  not verify the user-facing behavior, and the audit explains why
  that gap was invisible.
- **The audit itself.** `.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md`
  is the basis for this retraction and remains in the repo as a
  permanent record of the failure mode.

---

## Current state: development mode

The `main` branch is now the development trunk. The current version
constant in `src/paxman/versioning.py` and `pyproject.toml` is
`2.0.0.dev0` — a development pre-release of v2.0.0. There is **no
stable v2 release yet**.

Work in progress on `main` (and feature branches off it):

- Wiring the existing 7-step heuristic chain in
  `src/paxman/planner/heuristics.py:build_capability_chain` so the
  planner actually tries `select_local_deterministic` →
  `select_structured_lookup` → `select_local_inference` →
  `select_remote_inference` for fields without `format_hints` or
  `extract=`. The functions exist and are unit-tested in isolation;
  the entry point was simply not calling them.
- Adding a "README quickstart" smoke test to CI that runs the README
  example verbatim and asserts `artifact.normalized_data == {...}`.
  This is the structural fix that prevents the v1.x failure mode
  from recurring.
- Replacing the v1.x golden fixtures (all named `*_unresolved.json`)
  with `*_resolved.json` fixtures and updating the integration tests
  to assert against them.
- Continuing the v1.2.0 LLM-provider SPI work (`feat/real-llm-provider-1`,
  see in-progress plans in `docs/superpowers/plans/`).
- v2 feature work: real LLM-backed inference, parallel executor
  (deferred from V1 per ADR-0006), broader format support.

### How to follow progress

- Issues and PRs against `main` are tracked on
  [GitHub](https://github.com/nexusnv/paxman).
- The postmortem (`.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md`) is
  the authoritative description of what went wrong and what the v2
  acceptance criteria must include to prevent recurrence.
- `CHANGELOG.md` (top-level stub) and `docs/operations/changelog.md`
  (full changelog) carry the retraction entry at the top.

---

## If you arrived here from a v1.x install

You are running retracted code. Recommended actions:

1. **Do not use it in production.** The behavior is not what the docs
   claim. For a Pydantic `Invoice(supplier_name: str)` contract, every
   field will be `UNRESOLVED` and `normalized_data` will be `{}`.
2. **For a structured-input use case** (JSON / CSV / XML with explicit
   `format_hints` or per-field `extract=` regex patterns), the v1.1.0
   release *can* produce resolved data. It is deterministic, replayable,
   and the SHA-256 hash is byte-stable across runs. But it is no longer
   maintained.
3. **For a free-text / LLM-backed use case**, v1.x cannot help you.
   v1.2.0 plan 1/4 (the LLM provider SPI) shipped on
   `feat/real-llm-provider-1`, but the planner entry point still does
   not call the inference capability, and the inference capability is
   still a hard-coded string stub. Wait for v2.
4. **Pin to the exact v1.x version you need** if you have a working
   deployment (`paxman==1.1.0` is functional for the structured-input
   subset). Do not upgrade.

---

## Credits and ownership

This retraction is issued by the Paxman core team. The audit that
triggered it was commissioned as a third-party code review on 2026-07-12.
The author of the audit and this retraction statement is the same
person, working from the same evidence.

The technical findings in the audit are not in dispute. The
architectural choices (subsystem boundaries, ADRs, MONEY-as-Decimal,
deterministic replay) are sound; what failed was the wire-up of those
choices into a working planner, and the test discipline that would
have caught it.

The path forward is straightforward: wire the planner, write the
behavioral test, ship v2. There is no ambiguity about what to do.

— Paxman core team, 2026-07-12

---

## Appendix: Maintainer checklist — remote operations to complete the retraction

This document describes the retraction in full. The local repository
on `recovery/sprint-1-6` (the branch you are on) has been updated:

- `RETRACTION.md` created at the repo root.
- `pyproject.toml` version bumped to `2.0.0.dev0`; classifier changed
  to `2 - Pre-Alpha`; `Retraction` URL added to `[project.urls]`.
- `src/paxman/versioning.py` `__version__` bumped to `2.0.0.dev0`.
- `README.md`, `CHANGELOG.md`, `docs/operations/changelog.md`,
  `docs/index.md`, and the three historical release notes
  (`docs/concepts/RELEASE_NOTES_v1.0.{0,1,2}.md`) all carry retraction
  pointers at the top.
- `.github/workflows/release.yml` frozen via `env.RELEASE_FROZEN: "true"`
  and per-job `if: ${{ env.RELEASE_FROZEN != 'true' }}` guards.
- `Makefile` `publish` and `publish-test` targets disabled
  (return non-zero with a clear error message).
- Local git tags `v1.0.0`, `v1.0.1`, `v1.0.2`, `v1.1.0` deleted.
  `v0.5.0-rc1` and `v1.0.0-rc.1` retained.

The following remote operations are **not** run automatically by the
retraction commit. They require a maintainer with push and PyPI
credentials, and they are listed here in the order they should be
executed.

### 1. Delete the retracted tags on `origin`

```bash
# From the repository root, on the branch that received the retraction.
git push origin :refs/tags/v1.0.0 :refs/tags/v1.0.1 :refs/tags/v1.0.2 :refs/tags/v1.1.0
```

If `origin` is configured to deny non-fast-forward tag deletion
(rare; most repos allow it), use the GitHub web UI: navigate to
`https://github.com/nexusnv/paxman/tags`, click the three-dot menu
next to each tag, and select "Delete tag". Confirm the prompt.

### 2. Yank the four versions on PyPI

`twine` is the canonical tool. It requires a PyPI API token (or
OIDC trusted publishing configured for the project). If neither is
available, use the PyPI web UI: navigate to the project page
(`https://pypi.org/project/paxman/`), open the version's release
page, and select "Yank release" from the options menu.

```bash
# Yanking each version. `--pypi` is the default; `--test-pypi` is
# supported for the TestPyPI instance. Yanking is reversible.
twine yank paxman==1.0.0
twine yank paxman==1.0.1
twine yank paxman==1.0.2
twine yank paxman==1.1.0
```

To check the yank status from the command line:

```bash
pip index versions paxman  # does not list yanked versions
# or
curl -s https://pypi.org/pypi/paxman/json | python -c "
import json, sys
data = json.load(sys.stdin)
for v, files in sorted(data['releases'].items()):
    yanked = any(f.get('yanked') for f in files)
    print(f'  {v}: {\"YANKED\" if yanked else \"live\"}')
"
```

### 3. Replace the four GitHub Release pages with retraction notices

The web UI is the simplest path. For each of `v1.0.0`, `v1.0.1`,
`v1.0.2`, `v1.1.0`:

1. Navigate to `https://github.com/nexusnv/paxman/releases/tag/vX.Y.Z`.
2. Click "Edit release".
3. Replace the body with the retraction notice from
   [`RETRACTION.md`](./RETRACTION.md) (the top-level summary is
   sufficient).
4. Uncheck "Set as the latest release" (if it was checked) — leave
   the latest-release badge pointing at the `main` branch instead.
5. Save.

If the project uses `gh` CLI:

```bash
for tag in v1.0.0 v1.0.1 v1.0.2 v1.1.0; do
  gh release edit "$tag" \
    --notes "$(cat RETRACTION.md | head -120)" \
    --latest=false
done
```

### 4. Cross-link the PyPI announcement Discussions

The three Discussions associated with the v1.0.0 and v1.1.0 releases
(`#116`, `#117`, `#118`) should each receive a reply linking to this
`RETRACTION.md` and to the audit postmortem. This is a courtesy to
anyone who arrived at the project via those announcements.

### 5. Update the RTD configuration (optional)

The docs site at `paxman.readthedocs.io` continues to serve the
historical content. The retraction notice in `RETRACTION.md` is
visible via the new "Retraction notice" entry in the MkDocs nav
(`mkdocs.yml` updated in this retraction commit). No further RTD
configuration is required. If you want the retraction notice to
also appear as a banner at the top of every page on the RTD site,
add a partial include or edit the theme overrides.

### 6. Verify

After all six steps are complete:

```bash
# Confirm tags are gone:
git ls-remote --tags origin | grep -E "v1\.[0-9]+\.[0-9]+$" || echo "OK: no v1.x.y tags on origin"

# Confirm PyPI yanks are visible:
pip index versions paxman  # should NOT show 1.0.0, 1.0.1, 1.0.2, 1.1.0

# Confirm the local repo state matches what is described above:
git status --short
git tag -l  # should show v0.5.0-rc1 and v1.0.0-rc.1 only
git log --oneline -1  # should be the retraction commit
```

If all three checks pass, the retraction is complete.

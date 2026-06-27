# PyPI Trusted Publisher (OIDC) Setup

> **Date:** 2026-06-26
> **Sprint:** [Sprint 9 — Production Hardening](./sprint-09-production-hardening.md)
> **Deliverable:** D9.9
> **Status:** Manual setup required (one-time, by repo admin)

## Why OIDC?

Paxman uses **PyPI Trusted Publishing** (OpenID Connect) to publish to TestPyPI
and (in Sprint 10) to PyPI. This means:

- **No API tokens** are stored in the repo or in the GitHub Actions environment.
- The GitHub Actions runner authenticates the publish request using a short-lived
  OIDC token, which PyPI validates against the trusted publisher config.
- This eliminates the risk of a leaked API token being used to publish a
  malicious release.

Per `V1_ACCEPTANCE_CRITERIA.md` §3.1 and `SECURITY.md` §3.3, secrets-by-reference
is a hard requirement; OIDC trusted publishing is the implementation of that
principle for PyPI releases.

## Setup steps (one-time, by repo admin @nexusnv)

### TestPyPI trusted publisher

1. Go to https://test.pypi.org/manage/project/paxman/settings/publishing/
2. Click **"Add a new pending publisher"**
3. Fill in:
   - **PyPI Project Name:** `paxman`
   - **Owner:** `nexusnv`
   - **Repository name:** `paxman`
   - **Workflow filename:** `release.yml`
   - **Environment name:** `testpypi`
4. Click **"Add"**

> **Important:** The "Environment name" field on the publisher must
> match the ``environment: ...`` key in the workflow's publish job.
> For TestPyPI, the publisher uses `testpypi` and the workflow
> has ``environment: testpypi`` on the ``publish-testpypi`` job.
> For PyPI, the publisher uses `pypi` and the workflow has
> ``environment: pypi`` on the ``publish-pypi`` job.

### PyPI trusted publisher (for Sprint 10)

Same pattern as TestPyPI:

1. Go to https://pypi.org/manage/project/paxman/settings/publishing/
2. Click **"Add a new pending publisher"**
3. Fill in:
   - **PyPI Project Name:** `paxman`
   - **Owner:** `nexusnv`
   - **Repository name:** `paxman`
   - **Workflow filename:** `release.yml`
   - **Environment name:** `pypi`
4. Click **"Add"**

### GitHub environment (recommended)

Create GitHub environments to gate publishing:

1. Go to https://github.com/nexusnv/paxman/settings/environments
2. Create `testpypi` environment (no required reviewers needed for Sprint 10)
3. Create `pypi` environment (consider requiring 1+ review for production)

The release workflow (`.github/workflows/release.yml`) already references these
environment names on the publish jobs.

## Verification

After setup, you should be able to:

1. Create a tag: `git tag v0.5.0 && git push origin v0.5.0`
   (Use `git push origin <tag-name>` — never `git push --tags`, which can publish
   multiple tags unintentionally.)
2. GitHub Actions will trigger the `release.yml` workflow
3. The workflow will run the full CI gates, then publish to TestPyPI
4. Check https://test.pypi.org/project/paxman/ for the published package

## Security properties

- **No API tokens in repo**: `grep -r "pypi_\|API_TOKEN" .github/` returns no matches
- **No API tokens in environment**: The GitHub OIDC token is short-lived (max 1 hour)
- **No secret in CI logs**: The `pypa/gh-action-pypi-publish` action handles OIDC transparently
- **Tamper-evident**: A `SHA256SUMS` checksum file is generated as a post-build step
  (`cd dist && sha256sum *.whl *.tar.gz > SHA256SUMS`). Users verify artifact integrity
  with `cd dist && sha256sum -c SHA256SUMS`. This is distinct from the V1 replay hash
  (`replay_hash`), which is a separate deterministic signature of the normalization
  pipeline — the two mechanisms are complementary: `SHA256SUMS` covers distribution
  integrity, while `replay_hash` covers normalization determinism.

## Fallback (if OIDC misconfigures)

Per the sprint risk register: "OIDC trusted publisher setup has a subtle
misconfiguration: Medium likelihood, High impact. Test with TestPyPI first.
Read PyPI's trusted publishing docs carefully. If OIDC fails, fall back to
a token temporarily and document the rollback."

The fallback is to use a PyPI API token as a GitHub Actions secret:

1. Generate a token at https://test.pypi.org/manage/account/token/
2. Add it as a GitHub secret: `TESTPYPI_API_TOKEN`
3. Temporarily modify `.github/workflows/release.yml` to use `password: ${{ secrets.TESTPYPI_API_TOKEN }}`
4. Document the rollback in this file and the release notes

This is **NOT preferred** — OIDC is the production path. The fallback exists
for emergency recovery only.

## References

- https://docs.pypi.org/trusted-publishers/
- https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- https://github.com/pypa/gh-action-pypi-publish#trusted-publishing
- [`../SECURITY.md`](../../SECURITY.md) §3.3 — what the artifact contains (no secrets)
- [`../DEPENDENCIES.md`](../../DEPENDENCIES.md) — dependency policy

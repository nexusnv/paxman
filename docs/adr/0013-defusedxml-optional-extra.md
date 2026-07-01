# ADR-0013: defusedxml as Optional Security Extra

> **Status:** Accepted
> **Date:** 2026-07-01
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —
> **Related:** [Issue #72](https://github.com/nexusnv/paxman/issues/72), [PR #71](https://github.com/nexusnv/paxman/pull/71) (V1.1.0 format extractors), [ADR-0005](./0005-confidence-ownership.md) (capabilities do not assign confidence), [ADR-0011](./0011-format-auto-detection-for-json-schema-dicts.md) (format auto-detection — sibling V1.1.0 hardening ADR)

## Context and Problem Statement

The V1.1.0 format-aware extractors (PR #71) added `xpath_extraction@1.0` to
parse untrusted XML/HTML input. The implementation uses
`xml.etree.ElementTree.fromstring` from the Python standard library, which
is flagged by `ruff S314` and `bandit B314`/`B405` because, even with
Python ≥ 3.7.1's `expat` ≥ 2.4.0 mitigations against billion-laughs
(CVE-2013-0340), the standard library parser is still exposed to:

- **External entity expansion (remote SSRF and local file disclosure)**
  via DTD processing.
- **DTD retrieval** (bandit B314 calls this out explicitly).
- **Future regressions** — the stdlib parser's security posture is a
  moving target maintained by CPython; `defusedxml` is purpose-built and
  patched faster when new XML attacks emerge.

PR #71 introduced the parser with a documented `# noqa: S314` (in
`pyproject.toml` per-file-ignores) and an inline `# nosec B314` (bandit)
suppression at the call site, with a rationale comment explicitly stating
"defusedxml migration is a V1.2 follow-up (issue #72)."

The V1 core-dependency policy (`docs/reference/dependencies.md` §1, also
enforced by `AGENTS.md`) limits core dependencies to ≤ 3 packages and
explicitly forbids adding new ones without an ADR. Moving `defusedxml`
to core is therefore out of scope for V1.2. The remaining options are
**a hardening wrapper around stdlib** or **an optional extra with
runtime fallback**.

This ADR is **defense-in-depth**: the current threat model (`docs/security/`)
treats the caller as the input source rather than an attacker, and a
`Budget.max_input_size_bytes` cap (which the inline comment refers to)
does not yet exist. The hardening is real, the urgency is moderate, and
the cost of an optional extra is one line in `pyproject.toml`.

## Decision Drivers

- **Defense-in-depth** — `defusedxml` is the canonical Python library
  for hardened XML parsing; it is the prescribed fix in
  [bandit's B314 documentation](https://github.com/PyCQA/bandit/blob/main/bandit/blacklists/calls.py#L225-L261)
  ("Methods should be replaced with their defusedxml equivalents").
- **Pillow precedent** — Pillow's `getxmp()` (`src/PIL/Image.py:60-64,
  1580-1617`) uses the exact pattern we are adopting: try
  `from defusedxml import ElementTree` at module import, fall back to a
  graceful degradation (`warnings.warn` + empty dict) when the optional
  dependency is not installed. Pillow is one of the most-installed
  Python packages and ships this pattern in production.
- **Zero-cost for non-XML users** — `pip install paxman` (without
  extras) must not pull in `defusedxml`. The current user base that
  does not use `xpath_extraction` must not be affected.
- **Core dependency policy** — the 3-package core limit
  (`docs/reference/dependencies.md` §1) and `AGENTS.md` forbid
  adding `defusedxml` to core. Optional extras are the documented
  escape hatch.
- **Determinism** — Paxman's V1 determinism guarantee (PRD §4.5,
  `REPLAY_AND_DETERMINISM.md`) requires that the same input + same
  contract + same Paxman version produce byte-equal results. The
  hardened parser is a drop-in replacement for the stdlib parser: same
  `.fromstring()` signature, same `Element` object, same `.findall()`
  semantics, same exception class (`defusedxml.ElementTree.ParseError`
  is `xml.etree.ElementTree.ParseError` by identity). Replay never
  re-parses XML — it rehydrates from the stored evidence — so the
  backend chosen at first import is irrelevant to `replay()`.
- **No public API change** — the `XPathExtractionCapability` public
  surface is unchanged. Only the internal parse backend switches.
- **No new public surface** — `xml-secure` is an extra; the
  capability registry, the planner, the executor, the reconciler, the
  artifact, and the API are all unchanged. The public API snapshot
  test in `tests/public_api/test_public_api.py` continues to pass.

## Considered Options

### Option A — Optional extra + feature-detect + INFO log on fallback (chosen)

Declare `xml-secure = ["defusedxml>=0.7.1"]` in
`[project.optional-dependencies]`. At module import time, try
`from defusedxml.ElementTree import fromstring`; on `ImportError`,
fall back to `xml.etree.ElementTree.fromstring` and emit a one-shot
`structlog.info("xpath_extraction: using stdlib XML parser (install
paxman[xml-secure] for hardened parsing)", backend="stdlib",
hint="pip install paxman[xml-secure]")`.

The parse call at `xpath_extraction.py:invoke()` uses the detected
backend: `_fromstring(ctx.raw_input)`. The `except ET.ParseError`
clause continues to work because `defusedxml.ElementTree.ParseError`
is a re-export of the stdlib `ParseError` (verified by `is` check).

Add `xml-secure` to the `all` meta-extra so CI exercises the hardened
path automatically. Remove the `S314` per-file-ignore in
`pyproject.toml:145-150` (the hardened path is not flagged); the
stdlib fallback retains an inline `# nosec B314` because that path
*is* the unhardened one.

**Pros:**

- Matches the Pillow precedent exactly (one of the most-installed
  Python packages, with a real-world audit history).
- Zero cost for users who do not install the extra.
- No core dependency added — DEPENDENCIES.md §1 is preserved.
- CI exercises the hardened path via `make install-frozen` (which
  uses `--all-extras`).
- The INFO log on the stdlib fallback is a user-visible signal:
  silent fallback would be the textbook optional-security-dep
  anti-pattern; the log surfaces the unhardened mode at startup.
- `defusedxml==0.7.1` is already a transitive dependency in
  `uv.lock` (via `py-serializable` → `openapi-spec-validator`), so
  adding it as a direct optional extra changes nothing in CI.
- The `xml-secure` extra is the documented pattern for security-
  adjacent deps: small, single-purpose, optional.

**Cons:**

- Two code paths (defusedxml and stdlib) require a guard test to
  assert the backend matches the installed packages. This is
  addressed by the new tests in
  `tests/unit/test_capability_xpath_extraction.py`.
- The stdlib fallback path is still vulnerable to entity expansion.
  This is acceptable because: (a) Paxman's V1 threat model treats
  the caller as the input source, not an attacker; (b) the fallback
  is observable via the INFO log; (c) the docstring in the optional
  extra signals the recommended install.
- Import-time feature detection fixes the backend at first import.
  This is not a determinism footgun: replay never re-parses XML;
  the artifact's stored evidence is the same regardless of backend
  (same `Element` objects, same `.tag`/`.text`/`.findall()` API).

### Option B — Stdlib-only with custom hardening wrapper (rejected)

Write a ~30-line `_safe_parse_xml` that wraps `xml.etree.ElementTree.fromstring`,
rejects DTD declarations, and caps entity expansion. No new dependency.
Equivalent security property in theory.

**Pros:**

- No `defusedxml` dependency at all.
- Core policy is preserved (no extra needed).
- Single code path.

**Cons:**

- The "30-line wrapper" is a long-term maintenance burden. The stdlib
  XML threat surface evolves; `defusedxml` follows the stdlib CVE
  stream; a homegrown wrapper does not.
- Bandit's B314 documentation explicitly prescribes `defusedxml` as
  the fix, not a custom wrapper. A future security review will ask
  "why didn't you just use `defusedxml`?"
- A custom wrapper does not match the project's packaging convention.
  Every other format-adjacent dep (`pydantic`, `jsonschema`,
  `openapi-spec-validator`) is a PyPI package, not inline code.
- `defusedxml` is 25 KB, zero transitive deps, maintained by
  Christian Heimes (CPython security lead, defusedxml author). The
  cost of *adding* it is essentially zero; the cost of *writing and
  maintaining* an equivalent wrapper is real.
- The Pillow precedent demonstrates that the optional-extra pattern
  is well-understood and battle-tested in the Python ecosystem. A
  custom wrapper is a local invention with no community reference.

### Option C — Move defusedxml to core dependencies (rejected)

Add `defusedxml>=0.7.1` to `dependencies = [...]` in `pyproject.toml`.

**Pros:**

- Hardened XML is the default; no fallback path.
- Simplest user experience: `pip install paxman` gives the hardened
  parser automatically.

**Cons:**

- **Violates DEPENDENCIES.md §1** — the 3-package core limit. Adding
  `defusedxml` as a 5th core dep is a breaking change in spirit (every
  user's install footprint grows), requires a separate ADR justifying
  the addition, and is explicitly forbidden by `AGENTS.md` ("Adding a
  core dependency requires an ADR").
- Increases the install footprint for callers who never use
  `xpath_extraction` — the largest Paxman user segment in V1.
- `defusedxml` is a security dep, not a core engine dep. Per
  `docs/reference/dependencies.md` §5.1: "the dependency is needed
  by the core engine, not by an adapter or provider" is the criterion
  for a core dep; a security dep that one capability uses does not
  meet that bar.

### Option D — Defer to V2 (rejected)

Document the current `# noqa: S314` as accepted and revisit in V2.

**Pros:**

- No code change.

**Cons:**

- B314 is a Medium-severity bandit finding. Every future security
  review re-litigates the same `# noqa` comment.
- The S314 suppression is a known-bad marker. Future readers trip
  over it.
- V2 is not scheduled. V1.1.0 is the natural release window.
- The previous agent's analysis correctly identified the issue as
  "precautionary, not a real fix" — deferring does not fix the
  audit-magnet problem.

## Decision Outcome

**Chosen option: A (Optional extra + feature-detect + INFO log on fallback).**

The implementation:

1. **Declare the extra** in `pyproject.toml`:

   ```toml
   [project.optional-dependencies]
   pydantic = ["pydantic>=2.5"]
   json-schema = ["jsonschema>=4.20"]
   openapi = ["openapi-spec-validator>=0.6"]
   # Security extra (this ADR). Hardened XML parsing for xpath_extraction.
   xml-secure = ["defusedxml>=0.7.1"]
   # Convenience meta-extra. CI installs all extras via --all-extras.
   all = ["paxman[pydantic,json-schema,openapi,xml-secure]"]
   ```

2. **Module-level feature detect** in
   `src/paxman/capabilities/v1/xpath_extraction.py` (replacing the
   single-line `import xml.etree.ElementTree as ET`):

   ```python
   import xml.etree.ElementTree as _stdlib_ET
   from paxman.logging import get_logger as _get_logger

   _log = _get_logger("paxman.capabilities.xpath_extraction")

   # --- XML backend feature-detect (ADR-0013) ---
   try:
       from defusedxml.ElementTree import fromstring as _defused_fromstring  # type: ignore[import-untyped]
   except ImportError:
       _defused_fromstring = None  # type: ignore[assignment]

   if _defused_fromstring is not None:
       _fromstring = _defused_fromstring
       _XML_BACKEND: str = "defusedxml"
   else:
       _fromstring = _stdlib_ET.fromstring
       _XML_BACKEND = "stdlib"
       _log.info(
           "xpath_extraction: using stdlib XML parser "
           "(install paxman[xml-secure] for hardened parsing)",
           backend="stdlib",
           hint="pip install paxman[xml-secure]",
       )
   ```

3. **Parse call site** uses the detected backend:

   ```python
   root = _fromstring(ctx.raw_input)  # nosec B314  (stdlib fallback only)
   ```

   The `# nosec B314` is correct *only* on the stdlib fallback path.
   When `defusedxml` is installed, this directive is a no-op
   (bandit does not flag `defusedxml.ElementTree.fromstring`).

4. **Remove the `S314` per-file-ignore** for
   `xpath_extraction.py` in `pyproject.toml`. With `defusedxml`
   available, the hardened path is not flagged. The stdlib fallback
   is the only path that *would* be flagged, and the inline
   `# nosec B314` covers it.

5. **Documentation** in `docs/reference/dependencies.md` §3.2
   (new "Security extras" subsection) and in the `[Unreleased]`
   section of `docs/operations/changelog.md`.

## Consequences

### Positive

- Removes the documented security smell: the `# noqa: S314` per-file-
  ignore is gone. The inline `# nosec B314` is honest about the
  fallback path.
- Real defense-in-depth, not just a label: `defusedxml` rejects DTDs,
  external entities, and unbounded expansion *by default*, in the
  parser, before any work happens.
- Matches the Pillow precedent — well-tested in the Python ecosystem.
- Preserves the V1 zero-dep posture for non-XML users.
- `defusedxml==0.7.1` is already in the lockfile (transitive), so
  CI behavior is unchanged; the only delta is the user-visible
  extra name `xml-secure`.
- No public API change; no public surface change; no contract
  adapter change; no registry change; no artifact format change.
- The INFO log on the stdlib fallback is the user-visible signal
  that makes the optional-extra pattern non-deceptive: callers who
  care about XML security see the log and install the extra.

### Negative

- The stdlib fallback path is still vulnerable to entity expansion.
  This is acceptable per the threat model but is a real residual
  risk for users who install paxman without `[xml-secure]`.
- The INFO log fires at module import time. This is consistent with
  Paxman's structured-logging posture (the `paxman.logging` module
  is the canonical logger factory) and does not include the raw
  input (per `Policy.log_raw_input: bool = False`).
- Two code paths require a guard test. The new tests
  (`test_xml_backend_is_detected`,
  `test_defusedxml_is_available_in_test_env`,
  `test_billion_laughs_rejected_or_degraded`) lock the backend
  selection and the security regression.

### Neutral

- `defusedxml`'s `ElementTree` module re-exports the stdlib
  `ParseError`, so the existing `except ET.ParseError` clause keeps
  working for both backends.
- The pre-existing capability self-registration gap (ADR-0012 does
  not include the V1.1.0 format extractors in
  `_bootstrap_v1_capabilities`) is **out of scope** for this ADR.
  A separate issue will be filed to address it.

## Validation

- **Unit test** — `test_xml_backend_is_detected` asserts
  `_XML_BACKEND in {"defusedxml", "stdlib"}`. The test env installs
  `paxman[all]`, so the backend is `defusedxml`.
- **Env sanity test** — `test_defusedxml_is_available_in_test_env`
  asserts `importlib.util.find_spec("defusedxml") is not None`. If
  this fails, the test env is misconfigured; the test fails loudly.
- **Security regression test** —
  `test_billion_laughs_rejected_or_degraded` sends a billion-laughs
  payload to the capability. Under `defusedxml`, the payload is
  rejected with `EntitiesForbidden` (verified by a manual repro
  before this ADR was written). Under stdlib, the test asserts
  the payload does not silently produce expanded entity content
  as a candidate.
- **Existing tests** — all 20 existing
  `tests/unit/test_capability_xpath_extraction.py` tests pass
  unchanged. Coverage on `xpath_extraction.py` stays ≥ 90%.
- **Local CI** — `make ci` runs all 10 checks. The `security`
  check (bandit) passes: the defusedxml path is not flagged; the
  stdlib fallback retains the inline `# nosec B314`.
- **uv lock** — `uv lock --no-sync` produces a minimal or empty
  diff (defusedxml is already a transitive dep).

## References

- [Issue #72](https://github.com/nexusnv/paxman/issues/72) — the
  originating request.
- [PR #71](https://github.com/nexusnv/paxman/pull/71) — V1.1.0
  format extractors, which added `xpath_extraction@1.0` with the
  stdlib parser and the documented suppression.
- [`docs/reference/dependencies.md`](./../reference/dependencies.md) §1
  (core dependency policy) and §5.2 (optional extra policy).
- [`AGENTS.md`](./../../AGENTS.md) — anti-patterns and core-dep
  limit.
- [`pyproject.toml`](./../../pyproject.toml) `[project.optional-dependencies]`
  — the existing extras (`pydantic`, `json-schema`, `openapi`, `all`).
- Pillow's `src/PIL/Image.py:60-64, 1580-1617` — the
  `try: from defusedxml / except ImportError: None` pattern with
  `warnings.warn` on the fallback.
- Bandit's [B313-B319 calls list](https://github.com/PyCQA/bandit/blob/main/bandit/blacklists/calls.py#L225-L261)
  — the prescribed fix is `defusedxml`.
- `defusedxml` README — the threat model (billion laughs, quadratic
  blowup, external entity, DTD retrieval).
- [`docs/adr/0011-format-auto-detection-for-json-schema-dicts.md`](./0011-format-auto-detection-for-json-schema-dicts.md)
  — sibling V1.1.0 hardening ADR.
- [`docs/adr/0012-v1-capabilities-self-register-on-import.md`](./0012-v1-capabilities-self-register-on-import.md)
  — orthogonal; this ADR does not change the capability SPI or
  the registration contract.

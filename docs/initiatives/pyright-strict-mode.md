# Pyright Strict Mode

> **Status:** Active (PR-0 in progress).
> **Audience:** Paxman contributors and maintainers.
> **Related docs:** [Engineering Standards](../contributing/engineering-standards.md), [Issue #26](https://github.com/nexusnv/paxman/issues/26), [Contributing](../contributing/index.md)

## 1. Problem Statement

The Paxman codebase currently runs pyright in `basic` mode as an advisory
cross-validation check (D8.19). The primary type gate is `mypy --strict`.

Running pyright in `strict` mode reveals **490 diagnostics across 85 files**,
with the hotspot concentrated at the adapter/canonical/planner seams:

- `contract/adapters/dict_dsl.py` — 59 diagnostics
- `contract/adapters/openapi.py` — 50 diagnostics
- `contract/adapters/json_schema.py` — 35 diagnostics
- `artifact/artifact.py` — 33 diagnostics
- `contract/canonical.py` — 24 diagnostics
- `planner/field_plan.py` — 21 diagnostics

The diagnostic distribution is not random. It tracks the boundaries where
external formats (`dict[str, Any]`, JSON Schema, OpenAPI, Pydantic) meet
the internal canonical model. This indicates that the type boundaries at
these seams are not explicit enough.

## 2. Success Criterion

**Criterion B: Future Capability Enablement**

> V2 inference providers and recursive contracts need tighter adapter
> Protocols; this Initiative lands the Protocols those features will build on.

**Rationale:** The adapter-layer Protocols (`CanonicalField`, `CanonicalContract`,
`MoneyValue`, `CapabilitySpec`, `EvidenceRef`) will be extended by V2 features.
Tightening these Protocols now reduces risk for V2 work and makes the adapter
layer more maintainable.

**Operational proxy:** Diagnostics drop from 490 to < 50 (non-`isinstance`),
with the residual diagnostics concentrated in documented silenced rules.

## 3. What This Initiative Is NOT

- **Not a hard CI gate.** mypy `--strict` remains the canonical gate. Pyright
  strict runs as additional validation (advisory, `continue-on-error: true`).
- **Not a zero-diagnostic requirement.** `reportUnnecessaryIsInstance` is
  silenced at the rule level because runtime correctness beats static elegance.
  Each silenced rule is documented in [Engineering Standards](../contributing/engineering-standards.md).
- **Not an ADR.** CI tooling policy is engineering process, not architecture.
  Documented in [Engineering Standards](../contributing/engineering-standards.md)
  alongside ruff/coverage/pytest-marker policy.
- **Not a V1.1 feature.** Sequenced behind real V1.1 features (#23, #24, #84).

## 4. Implementation Plan

### PR-0: Initiative Doc + Engineering Standards + CI Wiring (this PR)

**Deliverables:**
- This Initiative doc
- [Engineering Standards](../contributing/engineering-standards.md) doc
- `pyrightconfig-strict.json` (strict-mode config with silenced rules)
- `make typecheck-pyright-strict` Makefile target
- `pyright-strict` advisory CI job in `.github/workflows/ci.yml`
- mkdocs.yml nav update + cross-references

**Acceptance:**
- Initiative doc states success criterion B
- Engineering Standards doc documents canonical-vs-additional checker policy
- `make typecheck-pyright-strict` runs pyright in strict mode (advisory)
- CI job runs pyright strict (advisory, `continue-on-error: true`)
- mypy `--strict` still passes
- No source code changes

### PR-1: Adapter-Layer Protocol Tightening + Audit

**Deliverables:**
- Tighten `CanonicalField`, `CanonicalContract`, `MoneyValue`, `CapabilitySpec`,
  `EvidenceRef` Protocols to reduce `Any`-leakage at adapter boundaries
- Address non-`isinstance` diagnostics as a side-effect of Protocol work
- Audit 251 `reportUnnecessaryIsInstance` cases; document deliberate runtime
  safety nets in [Engineering Standards](../contributing/engineering-standards.md)
  under "Silenced rules: `reportUnnecessaryIsInstance`"

**Acceptance:**
- Pyright strict reports ≤ 50 non-`isinstance` diagnostics
- mypy `--strict` still passes
- Tests still pass
- New `Any`s in the public surface are zero

### PR-2 (optional): Follow-up Protocol Work

**Deliverables:**
- Follow-up Protocol or annotation work scoped to residual diagnostics
- Each follow-up PR re-states the criterion it is moving

**Acceptance:**
- Success criterion met (diagnostics < 50)
- mypy `--strict` still passes
- Tests still pass

## 5. CI Impact

**New CI job:** `pyright-strict` (advisory, `continue-on-error: true`)

**CI delta:** ~13s added to the CI pipeline (measured locally). Well within
the 30s budget from the original issue DoD.

**Rollout:** The job is advisory from day one. It does not block PRs. If
a future Initiative wants to promote it to a hard gate, that is a separate
conversation requiring its own ADR.

## 6. Silenced Rules

The following pyright rules are intentionally silenced in `pyrightconfig-strict.json`:

| Rule | Count | Justification | Audit Status |
|---|---:|---|---|
| `reportUnnecessaryIsInstance` | 251 | Deliberate runtime safety nets over `Any`-typed adapter inputs. Runtime correctness beats static elegance. | To be audited in PR-1 |
| `reportUnknownParameterType` | — | Carried forward from basic config | Not audited |
| `reportUnknownArgumentType` | — | Carried forward from basic config | Not audited |
| `reportUnknownLambdaType` | — | Carried forward from basic config | Not audited |
| `reportUnknownVariableType` | — | Carried forward from basic config | Not audited |
| `reportUnknownMemberType` | — | Carried forward from basic config | Not audited |

**Policy:** Each silenced rule must have a one-line justification logged in
[Engineering Standards](../contributing/engineering-standards.md). The justification
is auditable in PR review.

## 7. Risks

- **Public API delta risk:** Tightening adapter Protocols may force changes to
  the shape of `CanonicalField`/`CanonicalContract`. If so, that's a new public
  type change requiring a follow-up ADR.
- **Test discovery risk:** If any of the 251 `isinstance` calls is a deliberate
  runtime check (e.g. for a value that came in as `Any` and the static type is
  wrong), removing it is a real behavior change. PR-1 must be reviewed
  call-site by call-site.
- **Adapter exhaustiveness:** `openapi-spec-validator` and `jsonschema` don't
  ship type stubs. If PR-1 reveals that strict mode needs stubs we don't have,
  that's a dependency policy decision and should not be silently bypassed.

## 8. References

- [Issue #26](https://github.com/nexusnv/paxman/issues/26) — original issue with synthesized position
- [Engineering Standards](../contributing/engineering-standards.md) — canonical-vs-additional checker policy, silenced rules log
- [Contributing](../contributing/index.md) — contribution workflow
- [Architecture](../reference/architecture.md) — subsystem design
- [Package Structure](../reference/package-structure.md) — module layout

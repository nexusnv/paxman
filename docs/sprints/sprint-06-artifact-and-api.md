# Sprint 6 — Artifact + API (First End-to-End)

> **Duration:** 2 weeks
> **Goal:** Implement the **Artifact subsystem** (the product + replay source) and the **public API** (`paxman.normalize()` and `paxman.replay()`). End of sprint: the **full pipeline works end-to-end** with real `paxman.normalize()` returning a real `ExecutionArtifact` that can be replayed.
> **Status:** This is the sprint that produces the first **v0.1.0-alpha** internally usable build. Still pre-release (no PyPI publish), but callable from a script.

## Scope (in)

### Artifact subsystem (`src/paxman/artifact/`)
- `artifact.py` — `ExecutionArtifact`, `FieldResult` data models (the final output bundle)
- `confidence.py` — confidence band mapping (float ↔ `CERTAIN`/`HIGH`/`MEDIUM`/`LOW`/`UNTRUSTED`)
- `evidence.py` — evidence references + provenance
- `diagnostics.py` — structured diagnostics
- `statistics.py` — execution statistics
- `serializer.py` — stable JSON encoding for the artifact (delegates to `cross-cutting/serialization.py`)
- `_hash.py` — replay hash internals (SHA-256)
- `replay.py` — replay hash computation + rehydration + version checks

### Public API (`src/paxman/api/`)
- `types.py` — re-exports: `CanonicalContract`, `CanonicalField`, `FieldType`, `Status`, `ConfidenceBand`, `ResolutionPolicy`, `Budget`, `Policy`, `ExecutionArtifact`, `CurrencyPolicy`
- `errors.py` — public error re-exports (all 13 classes from `cross-cutting/errors.py`)
- `protocols.py` — public SPIs: `ContractAdapter`, `Capability`
- `registry.py` — public `register_adapter()`, `register_capability()`
- `version.py` — `__version__` string
- `normalize.py` — top-level orchestration: `paxman.normalize(input_data, contract, budget=None, policy=None) -> ExecutionArtifact`
- `replay.py` — top-level `paxman.replay(artifact, contract) -> ExecutionArtifact`

### `src/paxman/__init__.py`
- Re-export public surface from `api/*`
- Re-export `__version__`
- Tiny: ≤ 30 lines

### Tests
- Unit tests for all Artifact modules
- Unit tests for all `api/` modules
- **First end-to-end smoke test:** `paxman.normalize(text, InvoiceContract)` returns an `ExecutionArtifact`
- Replay equality: `paxman.replay(artifact, contract) == artifact` (byte-equal JSON)
- Replay tamper detection: modified artifact raises `HashMismatchError`
- Replay version mismatch: wrong Paxman version raises `VersionMismatchError`
- Public API snapshot test: `tests/public_api/test_public_api.py` fails if anything new is added without an ADR

### Tooling
- `import-linter` contract: `artifact/` may NOT import from `api/`; `api/` may import from any layer
- `bandit` security scan clean
- `pip-audit` clean

## Scope (out)

- **Property tests** (Sprint 7) — Sprint 6 has unit tests and 1 end-to-end smoke.
- **Hypothesis strategies** (Sprint 7) — `paxman.testing` strategies module.
- **Performance optimization** (Sprint 9) — Sprint 6 is correctness-only.
- **Golden artifacts** (Sprint 7) — Sprint 6 produces one smoke artifact; Sprint 7 bootstraps the full set.
- **PyPI publish** (Sprint 10).

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D6.1 | `artifact/artifact.py` — `ExecutionArtifact`, `FieldResult` | 2.0 |
| D6.2 | `artifact/confidence.py` — band mapping | 0.5 |
| D6.3 | `artifact/evidence.py` | 1.0 |
| D6.4 | `artifact/diagnostics.py` | 1.0 |
| D6.5 | `artifact/statistics.py` | 1.0 |
| D6.6 | `artifact/serializer.py` (uses `cross-cutting/serialization.py`) | 2.0 |
| D6.7 | `artifact/_hash.py` — SHA-256 internals | 1.0 |
| D6.8 | `artifact/replay.py` — rehydration + version checks | 3.0 |
| D6.9 | `api/types.py` — re-exports | 2.0 |
| D6.10 | `api/errors.py` — re-exports | 1.0 |
| D6.11 | `api/protocols.py` — re-exports | 1.0 |
| D6.12 | `api/registry.py` — `register_adapter`, `register_capability` | 1.0 |
| D6.13 | `api/version.py` — `__version__` | 0.5 |
| D6.14 | `api/normalize.py` — top-level orchestration | 3.0 |
| D6.15 | `api/replay.py` — `paxman.replay()` | 1.5 |
| D6.16 | `src/paxman/__init__.py` — re-exports (≤30 lines) | 1.0 |
| D6.17 | Unit tests for all Artifact modules | 3.0 |
| D6.18 | Unit tests for all `api/` modules | 2.0 |
| D6.19 | **First end-to-end smoke test** (`tests/integration/test_smoke_e2e.py`) | 1.5 |
| D6.20 | Replay equality test (byte-equal) | 1.0 |
| D6.21 | Replay tamper detection test | 0.5 |
| D6.22 | Replay version mismatch test | 0.5 |
| D6.23 | `tests/public_api/test_public_api.py` — public API snapshot | 1.0 |
| D6.24 | `import-linter` contract for `artifact/` and `api/` | 0.5 |
| D6.25 | Update `README.md` quickstart to use the real `paxman.normalize()` | 0.5 |

**Total: ~31.5 id-ed.** Sized for **4 engineers × 2 weeks** (2 on artifact, 1 on api, 1 on tests + public API).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 4 engineers (1 senior, 3 mid-level) | Replay is subtle; needs senior review |
| **Tools** | All Sprint 1-5 deps | Standard Python dev env |
| **Tests** | Reconciler + all 5 capabilities from Sprint 3-5 | Done |
| **Docs** | `REPLAY_AND_DETERMINISM.md` — the full replay model | Read by the replay implementer |
| **Decisions** | Replay hash inputs (per `REPLAY_AND_DETERMINISM.md` §2.1) — already decided | Already in doc |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **hashlib** (stdlib) | — | SHA-256 for replay hash | Stdlib |
| **json** (stdlib) | — | Uses `cross-cutting/serialization.py`, not stdlib directly | Per the anti-pattern in `TESTING_STRATEGY.md` §10.2 |
| **packaging** (PyPA) | latest | Version comparison for replay version checks | New dev dep |
| **hypothesis** | ≥ 6.0 | (Sprint 7) | Not used this sprint |

## API keys / secrets

None.

## Exit criteria

1. `paxman.normalize(text, InvoiceContract)` returns an `ExecutionArtifact` end-to-end.
2. `paxman.replay(artifact, contract)` returns a byte-equal artifact.
3. Modifying any field of the artifact (via `dataclasses.replace`) and calling `paxman.replay` raises `HashMismatchError`.
4. `paxman.replay` with a different Paxman version (mocked) raises `VersionMismatchError`.
5. `paxman.register_adapter(MyAdapter())` and `paxman.register_capability(MyCapability())` work.
6. The public API surface is exactly: `paxman.normalize`, `paxman.replay`, `paxman.register_adapter`, `paxman.register_capability`, `paxman.__version__`, plus the public types and errors listed in `V1_ACCEPTANCE_CRITERIA.md` §1.4.
7. `tests/public_api/test_public_api.py` fails if any new symbol is added to `paxman/__init__.py` without an ADR.
8. The artifact contains all required fields: `normalized_data`, `field_results`, `unresolved_fields`, `evidence`, `diagnostics`, `execution_plan`, `replay_hash`, `statistics`.
9. The artifact serializes to a stable JSON (sorted keys, no whitespace, RFC 8785-style).
10. Test coverage on `artifact/` ≥ 95% (V1 acceptance §2.2 — replay is critical).
11. Test coverage on `api/` ≥ 90%.
12. `mypy --strict src/paxman` is clean on all 7 subsystems + api.
13. `import-linter` is clean.
14. `bandit` is clean.
15. `pip-audit` is clean.
16. `make ci` is green.
17. The `README.md` quickstart runs end-to-end (manual smoke test by an engineer).

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The replay hash is unstable across Python versions or platforms | Medium | High | Use SHA-256, hex-encode. The hash inputs are explicitly listed in `REPLAY_AND_DETERMINISM.md` §2.1. Add a property test that runs the hash 1000 times and asserts byte-equal output. |
| The orchestrator in `api/normalize.py` mishandles an error path (e.g., Reconciler raises, but the artifact is returned anyway) | Medium | High | Explicitly enumerate the error-handling paths. Test every documented error path. |
| The artifact JSON shape is incompatible with future versions | Medium | Medium | Embed `paxman_version`, `planner_version`, `capability_versions` in the artifact. Document the schema in `artifact/artifact.py` module docstring. |
| The public API snapshot test is too strict and breaks every PR | Low | Medium | Allow `__version__` and the listed public types. Anything else requires an ADR. |
| `artifact/serializer.py` accidentally re-implements the stdlib JSON encoder (defeats the determinism guarantee) | Low | High | Hard rule: `artifact/serializer.py` MUST delegate to `cross-cutting/serialization.py`. Add a unit test that asserts the imported encoder is the one from cross-cutting. |
| `import-linter` flags `api/` importing from `contract/`, `planner/`, etc. (legitimate) but rejects `api/normalize.py` importing from all of them | Low | Low | The `api/` layer is explicitly allowed to import from any layer per `PACKAGE_STRUCTURE.md` §11. Configure `import-linter` to allow this. |
| The first end-to-end smoke test takes >10 seconds | Low | Low | Use a tiny contract (3 fields, plain text input). Performance is a Sprint 9 concern. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §1.3 (artifact, api), §1.4 (public API), §1.5 (replay).
- `../PACKAGE_STRUCTURE.md` §8 — `artifact/` module spec, §9 — `api/` module spec.
- `../REPLAY_AND_DETERMINISM.md` §2, §3 — replay hash and replay protocol.
- `../ARCHITECTURE.md` §4.6, §4.7, §9.
- `../TESTING_STRATEGY.md` §5, §10.2.
- `../SECURITY.md` — public surface stability (no leaking internal types).

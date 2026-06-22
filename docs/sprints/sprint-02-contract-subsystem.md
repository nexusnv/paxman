# Sprint 2 — Contract Subsystem

> **Duration:** 2 weeks
> **Goal:** Implement the **contract subsystem** end-to-end: `CanonicalContract`, validator, and the 3 **required** adapters (Pydantic, JSON Schema, Dict DSL). OpenAPI adapter deferred to Sprint 4.
> **Status:** First sprint where the package becomes meaningfully useful — users can pass a Pydantic model and get a `CanonicalContract` back.

## Scope (in)

- `src/paxman/contract/_types.py` — `FieldType` enum, `Constraint`, `ResolutionPolicy` data models

  > **Note (added per Oracle review F2):** `FieldType` was placed in
  > `paxman.types` during Sprint 1 (cross-cutting module, single source
  > of truth). `paxman.contract._types` re-exports it via
  > `from paxman.types import FieldType` so the contract layer uses it
  > without redefining it. The implementation matches the Sprint 1
  > decision; this spec was written before Sprint 1 finalised the
  > placement.
- `src/paxman/contract/canonical.py` — `CanonicalContract`, `CanonicalField`, `MoneyValue` attrs data models
- `src/paxman/contract/validator.py` — rejects invalid contracts → `InvalidContractError` family
- `src/paxman/contract/semantics.py` — semantic tag handling (e.g., "iso4217", "email")
- `src/paxman/contract/registry.py` — adapter lookup by `format_id`
- `src/paxman/contract/adapters/base.py` — `ContractAdapter` Protocol
- `src/paxman/contract/adapters/pydantic.py` — Pydantic v2 → CanonicalContract + back
- `src/paxman/contract/adapters/json_schema.py` — JSON Schema (draft 2020-12) → CanonicalContract
- `src/paxman/contract/adapters/dict_dsl.py` — Dict DSL (syntax from Sprint 0) → CanonicalContract
- Fixture contracts: `tests/fixtures/contracts/pydantic/` (≥3 models), `tests/fixtures/contracts/dict_dsl/` (≥3 contracts)
- Unit tests for every module above
- Property tests: roundtrip Pydantic → canonical → Pydantic preserves structure (within Pydantic v2's expressible subset)
- `import-linter` contract: `contract/` may NOT import from `planner/`, `executor/`, `reconciler/`, `artifact/`, `capabilities/`, or `api/`

## Scope (out)

- **OpenAPI adapter** (Sprint 4).
- **Planner, executor, reconciler, artifact, api** — those start Sprint 3+.
- **No `register_adapter()` public API yet** — that lands in Sprint 6 with the rest of `api/`.

## Deliverables

| ID | Deliverable | Effort (id-ed) |
|---|---|---|
| D2.1 | `contract/_types.py` — `FieldType` enum (9 values), `Constraint`, `ResolutionPolicy` | 2.0 |
| D2.2 | `contract/canonical.py` — `CanonicalContract`, `CanonicalField`, `MoneyValue` | 4.0 |
| D2.3 | `contract/validator.py` — every error path → `InvalidContractError` family | 3.0 |
| D2.4 | `contract/semantics.py` — semantic tag handling | 2.0 |
| D2.5 | `contract/registry.py` — adapter lookup | 1.0 |
| D2.6 | `contract/adapters/base.py` — `ContractAdapter` Protocol | 1.0 |
| D2.7 | `contract/adapters/pydantic.py` — adapt + export | 3.0 |
| D2.8 | `contract/adapters/json_schema.py` — adapt + export (draft 2020-12; earlier drafts best-effort) | 4.0 |
| D2.9 | `contract/adapters/dict_dsl.py` — adapt + export (using Sprint 0 syntax) | 2.0 |
| D2.10 | Fixture contracts: 3+ Pydantic, 3+ Dict DSL, 3+ JSON Schema | 2.0 |
| D2.11 | Unit tests for all 9 modules (≥1 test per public function) | 4.0 |
| D2.12 | Property tests: roundtrip preserves structure for Pydantic and Dict DSL | 2.0 |
| D2.13 | `import-linter` contract for `contract/` | 0.5 |
| D2.14 | Update `tests/fixtures/contracts/README.md` to reflect actual files | 0.2 |

**Total: ~30.7 id-ed.** Sized for **4 engineers × 2 weeks** with parallel work (3 adapters in parallel + 1 fixture writer + test lead).

## Prerequisites

| Type | Item | Notes |
|---|---|---|
| **People** | 4 engineers (1 senior, 3 mid-level) | Parallel work on adapters |
| **Tools** | Pydantic v2 installed; `jsonschema` installed; Dict DSL spec from Sprint 0; `pydantic-core` (for Pydantic v2 internals) | All dev dependencies in `pyproject.toml` |
| **Tests** | Sprint 1 test infrastructure (`conftest.py`, markers) | Done |
| **Docs** | `EXTENDING.md` §1 — adapter SPI reference | Read by adapter authors |
| **Decisions** | Dict DSL spec (Sprint 0) | Critical: defines the test source of truth |
| **Fixture data** | Decide on 3+ canonical contracts: invoice, quotation, all_v1_types | Per `tests/fixtures/contracts/README.md` |

## Tooling / applications / libraries

| Tool | Version | Purpose | Notes |
|---|---|---|---|
| **Pydantic** | ≥ 2.5 | Adapter test target + provider | `pip install paxman[pydantic]` |
| **jsonschema** | ≥ 4.20 | JSON Schema validation | `pip install paxman[json-schema]` |
| **hypothesis** | ≥ 6.0 | Property-based tests for roundtrip | New dev dep in this sprint |
| **factory_boy** | latest | Programmatic contract generation (optional, for tests) | Dev dep |
| **faker** | latest | Synthetic data generation | Dev dep |

## API keys / secrets

None.

## Exit criteria

1. `paxman.contract.adapt(InvoiceModel)` returns a `CanonicalContract` for a Pydantic model with at least one field of each V1 type.
2. The Pydantic adapter's `export(canonical)` returns a Pydantic model that round-trips: `adapt(export(adapt(X))) == adapt(X)`.
3. The Dict DSL adapter works against the Sprint 0 spec — at least 3 example contracts in `tests/fixtures/contracts/dict_dsl/` parse and produce equivalent canonical forms to the Pydantic versions.
4. The JSON Schema adapter handles draft 2020-12 (`type`, `properties`, `required`, `enum`, `pattern`, `minLength`/`maxLength`, `minimum`/`maximum`, `items`).
5. The validator rejects every documented error path: `UnsupportedFieldTypeError`, `InvalidConstraintError`, `InvalidPathError`, `InvalidSemanticTagError`.
6. Test coverage on `contract/` ≥ 90% lines (V1 acceptance §2.2).
7. `mypy --strict src/paxman/contract` is clean.
8. `import-linter` is clean: `contract/` may NOT import from any subsystem layer.
9. Property test: `adapt(export(adapt(contract))) == adapt(contract)` for 100 random Pydantic contracts (Hypothesis).
10. `interrogate src/paxman/contract` reports 100% on the public surface.
11. `make ci` is green.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The Pydantic adapter's MONEY handling is wrong (e.g., misinterprets `conint` vs `confloat`) | Medium | High | Property test all Pydantic field constraints; explicit MONEY test cases; pair review with senior engineer. |
| JSON Schema adapter's `MONEY` inference is brittle (no native JSON Schema type) | High | Medium | Document `x-paxman-type` extension as the canonical way to express MONEY in JSON Schema; provide a heuristic fallback for `pattern: "^[A-Z]{3}..."` with `format: currency`. |
| The canonical model scope creeps (someone adds `URL`, `BINARY`, `ANY`) | Medium | High | Hard rule: only 9 V1 types per GLOSSARY.md. Any new type requires an ADR. |
| Dict DSL spec from Sprint 0 has an edge case the adapter hits | Medium | Medium | Add a feedback loop: Sprint 2 may propose amendments to the Dict DSL spec via a follow-up PR. |
| Property tests for roundtrip are flaky | Low | Medium | Use `derandomize=True`, `deadline=None` for the slow roundtrips. Mark the strategy `@example` to pin known-good inputs. |
| The validator's error paths are incomplete (some errors leak as `Exception`) | Medium | High | Test every error path explicitly. Use `pytest.raises(InvalidContractError)` with `match=` on the `error_code` for each. |
| Adapter tests take >10s total (slow Pydantic model construction) | Low | Low | Use small models in tests; cache the canonical form in module-level fixtures. |

## See also

- `../V1_ACCEPTANCE_CRITERIA.md` §1.1 (Contract adapters), §1.4 (Public types).
- `../PACKAGE_STRUCTURE.md` §3 — `contract/` module spec.
- `../docs/adr/0004-money-first-class-type.md` — MONEY type rationale.
- `../docs/adr/0007-contract-adapter-set-v1.md` — V1 adapter set.
- `../EXTENDING.md` §1 — `ContractAdapter` SPI.
- `../GLOSSARY.md` — `FieldType` enum, `CanonicalContract`, `CanonicalField`.
- `../tests/fixtures/contracts/README.md` — planned fixture contracts catalog.

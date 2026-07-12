# V1.1.0: OpenAPI 3.1 Full Coverage — Design Spec

> **Status:** Draft (V1.1.0 scope, supersedes the V1 best-effort baseline in ADR-0007)
> **Date:** 2026-06-29
> **Parent issue:** [#22](https://github.com/nexusnv/paxman/issues/22)
> **Sub-issue (design):** [#41](https://github.com/nexusnv/paxman/issues/41)
> **Affected components:** `paxman.contract.adapters.openapi` + `paxman.contract.adapters.json_schema`

## 1. Context and Motivation

The V1.0.0 OpenAPI adapter (`src/paxman/contract/adapters/openapi.py`) is **best-effort**
per [ADR-0007](../adr/0007-contract-adapter-set-v1.md). It accepts both `3.0.x` and
`3.1.x` documents but treats them identically. OpenAPI 3.1 (released Feb 2021) is the
**current** major version of the OpenAPI Specification and the version most new tools
produce. Four features unique to 3.1 are silently dropped or rejected today:

1. **JSON Schema 2020-12 dialect.** OpenAPI 3.1 fully aligns with JSON Schema 2020-12.
   Today the adapter sets `$schema` to draft 2020-12 regardless of the document's
   declared dialect and does not consult `jsonSchemaDialect` (a 3.1-only field).
2. **`$defs` and `$ref` resolution.** OpenAPI 3.1 uses the standard JSON Schema
   `$ref` machinery, including the root-level `$defs` block. The current adapter
   only resolves `#/components/schemas/<name>` and rejects everything else —
   including `#/$defs/<name>`, which is the 3.1 way.
3. **Webhook support.** OpenAPI 3.1 introduces a top-level `webhooks` map, parallel
   to `paths`. V1 ignores it.
4. **Path-item-level `parameters` override behavior.** In 3.0.x, a path-item-level
   `parameters` array is **appended** to operation-level `parameters`. In 3.1, a
   path-item-level `parameters` array is **merged** (overrides by `name + in`).
   The current adapter reads neither.

This V1.1.0 release lifts the V1 best-effort posture for these four features while
keeping the rest of the adapter surface stable.

## 2. Goals and Non-Goals

### Goals

- **G1.** Parse OpenAPI 3.1 documents natively (not as a 3.0 dialect).
- **G2.** Honor the document's `jsonSchemaDialect` and `$schema` when present.
- **G3.** Resolve `$ref` to `#/$defs/<name>` and `#/components/schemas/<name>`
  symmetrically, with cycle detection and the same V1 reject-list for external /
  path refs.
- **G4.** Accept (and ignore-but-do-not-error) the 3.1 `webhooks` map and
  path-item-level `parameters` arrays.
- **G5.** Path-item-level `parameters` use 3.1 merge semantics when adapting a
  3.1 document (and remain appended-only for 3.0.x).
- **G6.** All 9 V1 field types remain supported; the existing petstore 3.0 test
  continues to pass byte-equal.
- **G7.** Adversarial 3.1 fixture added to the test corpus, with full property
  round-trip coverage.
- **G8.** `mypy --strict` and `ruff` remain clean on `src/paxman/`. No new core
  dependencies.

### Non-Goals (V1.1.0 scope discipline)

- **N1.** Composition (`oneOf`/`anyOf`/`allOf`/`discriminator`) remains V2. The
  reject-list is unchanged.
- **N2.** External `$ref` resolution (URL fetch) remains V2. Only intra-document
  refs are supported.
- **N3.** Reading `paths.*` request/response bodies is not in scope. The V1
  contract model is one canonical contract per `adapt()` call; 3.1 `webhooks` is
  documented but ignored.
- **N4.** `prefixItems` (tuple validation) is not in scope. `type: array` with
  `items` is the only array shape supported.
- **N5.** The `export()` method continues to emit OpenAPI **3.0.3** (the lowest
  common denominator). A 3.1 export is V2.

## 3. Design Overview

### 3.1 Version-branching seam

The existing adapter already detects the OpenAPI version string
(`_SUPPORTED_OPENAPI_VERSIONS`, lines 87–96 of `openapi.py`). The new seam is a
single helper:

```python
def _is_openapi_3_1(version: str) -> bool: ...
```

… and a set of new module-level constants:

```python
_OPENAPI_3_1_VERSIONS: frozenset[str] = frozenset({"3.1.0", "3.1.1"})
_OPENAPI_3_0_VERSIONS: frozenset[str] = frozenset({"3.0.0", "3.0.1", "3.0.2", "3.0.3"})
_DEFAULT_JSON_SCHEMA_DIALECT: str = _DRAFT_2020_12
```

All 3.1-specific behavior routes through this seam, keeping the 3.0 code path
byte-equal to V1.0.0.

### 3.2 `jsonSchemaDialect` handling

OpenAPI 3.1 lets a document declare `jsonSchemaDialect` at the top level. The
adapter reads it (best-effort), defaults to draft 2020-12, and passes the chosen
dialect down to the JSON Schema adapter so it can populate the `$schema` key
correctly. The `jsonSchemaDialect` value is **not** used to dispatch to a
different parser — the V1 JSON Schema adapter already targets draft 2020-12;
older dialects are still best-effort.

**Forwarding contract:** the JSON Schema adapter gains an optional
`schema_dialect: str | None = None` parameter. When `None`, the adapter uses its
existing default. When set, it uses the caller's value if it is in
`_SUPPORTED_DRAFTS`; otherwise it raises `INVALID_VERSION`.

### 3.3 `$ref` resolution: `$defs` + `components.schemas`

The existing `_inline_refs()` walker only knows about `#/components/schemas/<name>`.
The 3.1-aware walker accepts a **second** `definitions` namespace:

```python
def _inline_refs(
    schema: dict[str, typing.Any],
    *,
    components_schemas: dict[str, typing.Any],
    defs: dict[str, typing.Any],
    schema_name: str,
) -> dict[str, typing.Any]: ...
```

The walker accepts refs whose pointer is **either**
`#/components/schemas/<name>` (3.0) **or** `#/$defs/<name>` (3.1). A ref that uses
one prefix while the document is declared as the other version is treated as
**mismatched** and rejected with `INVALID_REF` (this prevents accidental
3.0↔3.1 schema mixing).

External refs (`https://…`, `./other.yaml`), path refs (`#/paths/…`), and pointer
refs to non-existent targets remain rejected with `UNSUPPORTED_OPENAPI_FEATURE` /
`INVALID_REF` — same behavior as V1.0.0.

The cycle-detection contract is unchanged: a `$ref` chain (`A` → `B` → `A`) is
detected and rejected with `INVALID_REF`.

### 3.4 `webhooks` and path-item-level `parameters`

These are **accepted** at the top level so the V1 reject-list for top-level V2
features (`oneOf`/`anyOf`/`allOf`/`discriminator`) is unchanged. They are
documented as **ignored** in the support matrix. A new test asserts that the
presence of `webhooks` and a `paths./x.parameters` array does not change the
adapted `CanonicalContract`.

This is a deliberate non-feature: full webhook/path parsing is V2 (N3).

### 3.5 Path-item-level `parameters` 3.1 merge semantics

For 3.1 documents only, when the adapter scans `paths` (which it currently does
not — see N3), the path-item-level `parameters` array is **merged** with the
operation-level `parameters` by the (`name`, `in`) tuple, with operation-level
entries winning on collision. For 3.0.x the semantics remain **append** (path-item
entries are appended after operation-level entries with no dedup).

**V1.1.0 implementation note:** because V1 ignores `paths.*` body parsing (N3),
the merge behavior is exercised only by **unit tests** that drive the new
`_merge_path_parameters()` helper directly. The behavior is **locked in** for
V2.0, when path parsing ships.

## 4. Detailed Component Changes

### 4.1 `src/paxman/contract/adapters/openapi.py`

**New constants**

```python
_OPENAPI_3_1_VERSIONS: typing.Final[frozenset[str]] = frozenset({"3.1.0", "3.1.1"})
_OPENAPI_3_0_VERSIONS: typing.Final[frozenset[str]] = frozenset({"3.0.0", "3.0.1", "3.0.2", "3.0.3"})
```

**New private helpers**

| Helper | Purpose |
|---|---|
| `_is_openapi_3_1(version: str) -> bool` | Predicate for the 3.1 seam. |
| `_read_json_schema_dialect(external: dict) -> str \| None` | Read top-level `jsonSchemaDialect`; returns `None` if absent. |
| `_read_defs(external: dict) -> dict[str, Any]` | Read `$defs`; returns `{}` if absent. Validates it is a dict. |
| `_merge_path_parameters(op_params, path_params, *, version) -> list` | 3.1 merge vs 3.0 append semantics. |

**Modified: `adapt()`**

1. After the version check, compute `is_3_1 = _is_openapi_3_1(version)`.
2. Read `dialect = _read_json_schema_dialect(external)`. Best-effort: if a 3.0
   document declares a non-draft-2020-12 dialect, ignore it silently. For 3.1,
   the dialect must resolve to a known draft or the document is rejected with
   `INVALID_JSON_SCHEMA_DIALECT`.
3. Read `defs = _read_defs(external)`.
4. Replace the single-arg call to `_inline_refs(schema_def, schemas, schema_name)`
   with the new two-namespace form.
5. Pass `schema_dialect=dialect` to `JsonSchemaAdapter().adapt(json_schema_doc)`.

**Modified: `_inline_refs()` signature**

The signature gains `*` keyword-only `components_schemas` and `defs` parameters;
positional `schemas` is removed. The walker now accepts either prefix; cycles
are tracked across the union of seen names (a name from `components.schemas`
cannot collide with a name from `$defs` — they live in different namespaces).

**Modified: `export()`**

Unchanged. Continues to emit `openapi: 3.0.3` (N5).

### 4.2 `src/paxman/contract/adapters/json_schema.py`

**New parameter on `adapt()`**

```python
def adapt(
    self,
    external: typing.Any,
    *,
    schema_dialect: str | None = None,
) -> CanonicalContract: ...
```

When `schema_dialect is not None`:
- Validate against `_SUPPORTED_DRAFTS`. If absent, raise `InvalidContractError`
  with `error_code="INVALID_VERSION"`.
- Use it as the value for the `$schema` field on the **exported** dict. (The
  adapter does not parse the dialect differently; it just remembers the value
  to round-trip it on `export()`.)

The parameter is keyword-only and defaults to `None` to preserve V1.0.0
byte-equivalence for every existing call site (Dict DSL, Pydantic, and existing
OpenAPI tests that pass a 3.0 document with no dialect).

### 4.3 New test fixture: `tests/fixtures/contracts/openapi/petstore_3_1.yaml`

A hand-rolled, MIT-licensed OpenAPI 3.1 fixture based on the official
`OAI/OpenAPI-Specification` 3.1 examples. It must:

- Declare `openapi: 3.1.0` and
  `jsonSchemaDialect: https://json-schema.org/draft/2020-12/schema`.
- Use a root-level `$defs` block with at least one shared definition.
- Use `type: [string, null]` for a nullable field (the 3.1 idiom).
- Exercise every V1 field type except `MONEY` (MONEY stays 3.0 via
  `x-paxman-type`).
- Include a `webhooks` map (adversarial — must be ignored).
- Include a path-item-level `parameters` array (adversarial — must be ignored).
- Be small enough to inline-assert in unit tests (< 200 lines).
- Be attributed in `tests/fixtures/DATASET_LICENSES.md` with source URL and
  license (MIT).

### 4.4 `tests/fixtures/DATASET_LICENSES.md`

Add an entry for `petstore_3_1.yaml` (MIT, source: OAI/OpenAPI-Specification,
hand-rolled subset). Also fix the existing drift: the file already references
`petstore_3_0.yaml` and `petstore_3_1.yaml` but the actual file is named
`petstore.yaml`. The fix is to **rename** the existing file to
`petstore_3_0.yaml` so the 3.0 fixture has a name aligned with the new 3.1
sibling.

## 5. Test Plan

### 5.1 Unit tests (existing file `tests/unit/test_contract_openapi.py` augmented)

- `test_adapt_accepts_3_1_with_dialect` — passes a 3.1 doc with
  `jsonSchemaDialect: https://json-schema.org/draft/2020-12/schema`; asserts
  `adapt()` succeeds.
- `test_adapt_rejects_3_1_with_unknown_dialect` —
  `jsonSchemaDialect: https://example.com/bad-dialect` →
  `INVALID_JSON_SCHEMA_DIALECT`.
- `test_adapt_resolves_defs_ref` —
  `Pet.properties.owner.$ref: '#/$defs/Owner'` resolves to the `Owner` schema
  in the new 3.1 fixture.
- `test_adapt_resolves_components_schemas_ref_under_3_1` — even in a 3.1
  document, a `$ref: '#/components/schemas/X'` still works
  (backward-compatibility).
- `test_adapt_rejects_defs_ref_in_3_0_document` —
  `$ref: '#/$defs/X'` in a `3.0.3` document → `INVALID_REF` (mismatched prefix).
- `test_adapt_ignores_webhooks` — document has a non-empty `webhooks` map; the
  adapted `CanonicalContract` is unchanged from the same document without
  `webhooks`.
- `test_adapt_ignores_path_item_parameters` — a path-item `parameters` array
  does not affect the adapted contract.
- `test_export_round_trip_3_1` — adapted 3.1 document → `export()` produces a
  valid 3.0.3 dict (N5).
- `test_adapt_3_1_nullable_type_array` — a 3.1 `type: [string, null]` field is
  mapped with `nullable=True` on the `CanonicalField`.
- `test_format_id` — still returns `"openapi:3.x"` (no format-id change for
  V1.1.0).

### 5.2 Property tests (Hypothesis) — `tests/property/test_contract_openapi_property.py` (new)

- **Round-trip** — for every `OpenApiDocumentStrategy`-generated instance:
  `adapt(doc) == adapt(export(adapt(doc)))` for the canonical content (the
  OpenAPI envelope is not preserved, but the field set, types, required flags,
  and constraints are).
- **Determinism** — `adapt(doc) == adapt(deepcopy(doc))` for every generated
  instance.
- **Cycle detection** — generated documents with `$ref` cycles raise
  `InvalidContractError` with `error_code="INVALID_REF"` and not `RecursionError`.
- **`@pytest.mark.deterministic`** added to every OpenAPI test (closing the gap
  noted by the test-census subagent).

### 5.3 Adversarial fixture

`tests/fixtures/contracts/openapi/petstore_3_1.yaml` is itself a smoke test:
loading it must succeed, the contract must have a non-empty field set, every
V1 type except `MONEY` must be represented, and the `replay_hash` of an
empty-input run must be stable across two runs on the same Python and Paxman
version.

### 5.4 Backward-compat regression

Every existing test in `tests/unit/test_contract_openapi.py` (16 tests today)
and `tests/unit/api/test_api_normalize.py` (`test_api_normalize` 3.0 path) must
pass unchanged. The `test_adapt_petstore_produces_canonical_contract` must
continue to assert `contract.id == "Swagger Petstore"` (the 3.0 fixture is
renamed `petstore_3_0.yaml`; the title is unchanged).

## 6. Error Model — New Codes

| `error_code` | When | Where |
|---|---|---|
| `INVALID_JSON_SCHEMA_DIALECT` | A 3.1 document declares a `jsonSchemaDialect` not in `_SUPPORTED_DRAFTS`. | `openapi.py` `_read_json_schema_dialect()` |
| `INVALID_DEF` | A 3.1 `$defs` block is present but not a dict. | `openapi.py` `_read_defs()` |
| `INVALID_REF` (extended) | A `$ref` uses the 3.1 (`#/$defs/…`) prefix in a 3.0 document, or vice versa. | `openapi.py` `_inline_refs_impl()` |

All three are `InvalidContractError` subclasses — the V1 error contract is
preserved.

## 7. Migration / Compatibility

- **No public API change.** `OpenApiAdapter.format_id` is unchanged.
  `OpenApiAdapter.adapt()` and `.export()` signatures are unchanged.
- **No new core dependency.** `jsonSchemaDialect` is parsed with stdlib only.
- **Existing 3.0 callers see no change.** Byte-equal behavior for every 3.0
  input that does not declare `jsonSchemaDialect`.
- **DATASET_LICENSES.md drift fix.** The fixture rename is a non-functional
  change but should be called out in the changelog.

## 8. Out of Scope — V2 Follow-ups

- Full 3.1 export (write back `openapi: 3.1.0` + `$defs`).
- `oneOf` / `anyOf` / `allOf` (composition) with 3.1-specific
  `unevaluatedProperties`.
- Path + webhook body parsing.
- Tuple validation (`prefixItems`).
- External `$ref` resolution.

## 9. Acceptance Criteria (DoD)

- [ ] All 6 Definition-of-Done items from issue #22 are checked.
- [ ] Existing 3.0 tests pass byte-equal (regression suite).
- [ ] New `petstore_3_1.yaml` fixture committed and attributed.
- [ ] `ruff check`, `ruff format --check`, `mypy --strict`, `pyright` all green
      on `src/paxman/`.
- [ ] `make ci` passes locally.
- [ ] This design spec is referenced from `docs/reference/extending.md` (or a
      new `docs/howto/openapi-3-1.md`).
- [ ] CHANGELOG entry under `## [Unreleased] → ### Added`:
      "OpenAPI 3.1: `jsonSchemaDialect`, `$defs` ref resolution, `webhooks` /
      path-item `parameters` accepted (ignored)".

# ADR-0011: Format Auto-Detection for JSON Schema Dicts

> **Status:** Accepted
> **Date:** 2026-07-01
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Per ADR-0007 and ADR-0009, Paxman V1 supports four contract formats via four adapters: Pydantic, JSON Schema, Dict DSL, and OpenAPI. The `paxman.normalize()` and `paxman.replay()` entry points accept a heterogeneous `contract` argument and dispatch to the right adapter through `_detect_format()` (`src/paxman/api/normalize.py:56-99`).

V1.0.0 shipped a detection order that routes:

1. Pydantic (duck-typed via `model_fields`)
2. `dict` -> `"dict_dsl"` (unconditional)
3. `str` -> tries JSON Schema, then OpenAPI

This order silently mis-routes JSON Schema documents that have been loaded as Python `dict` literals (e.g. via `json.load()` or inline fixture data) to the Dict DSL adapter. The Dict DSL adapter then raises `InvalidContractError(error_code="MISSING_CONTRACT_ID")` — a confusing error pointing at the wrong adapter — even though the JSON Schema adapter (`format_id="json_schema:draft-2020-12"`) is registered and can natively handle dict inputs (`src/paxman/contract/adapters/json_schema.py:149-225`).

Issue #52 (filed 2026-07-01) is the canonical tracking issue. The reproduce case is:

```python
import json
import paxman
import paxman.contract.adapters.json_schema  # noqa: F401

schema = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
}

# Fails with: "Dict DSL contract is missing required 'id' key"
artifact = paxman.normalize(input_data=b"hello", contract=schema)
```

The same input as a JSON string (`json.dumps(schema)`) works correctly. The fix: when a `dict` input has structural markers of a JSON Schema document, route to the JSON Schema adapter instead of the Dict DSL adapter.

This ADR is required per `AGENTS.md` ("Adding a public API surface requires an ADR"). Although the change is a bug fix rather than a new public API, it changes the observable behavior of `_detect_format()` and the surface that users see when their JSON Schema documents are passed as dicts.

## Decision Drivers

- **User mental model** — a Python `dict` with `"type"`, `"properties"`, and/or `"$schema"` keys is JSON Schema, not Dict DSL. Users should not have to know about Paxman's internal format taxonomy.
- **Discoverability** — the misleading `MISSING_CONTRACT_ID` error currently sends users to the wrong adapter documentation. A `dict` with JSON Schema markers should route to the JSON Schema adapter and produce a useful `CanonicalContract`.
- **No new dependencies** — the JSON Schema adapter already accepts dict inputs; the fix is a detection-order change, not a new adapter or parser.
- **3-package core policy (DEPENDENCIES.md §2)** — the fix adds no dependencies.
- **Backward compatibility for Dict DSL** — the Dict DSL surface (`{"id": "x", "fields": [...]}`) has well-defined structural markers (`id` and `fields` at the top level). The detection heuristic must not regress legitimate Dict DSL contracts.
- **No changes to public API surface** — the function signatures of `paxman.normalize()` and `paxman.replay()` are unchanged. Only the internal dispatch logic changes.

## Considered Options

### Option A — Heuristic: check for JSON Schema markers before routing to Dict DSL (chosen)

When the `contract` argument is a `dict`, check for well-known JSON Schema structural markers before falling back to Dict DSL. JSON Schema's surface has consistent markers across all valid documents:

- `"$schema"` — explicit dialect declaration (most authoritative marker)
- `"type"` + `"properties"` — object schema shape (the most common JSON Schema shape)
- `"$defs"` or `"definitions"` — schema-internal definitions (JSON Schema 2020-12 / draft-07)
- `"$id"` — schema identifier (JSON Schema 2020-12)
- `"$ref"`, `"oneOf"`, `"anyOf"`, `"allOf"`, `"const"`, `"enum"`, `"items"`, `"additionalProperties"`, `"patternProperties"` — keywords exclusive to JSON Schema
- Top-level `"openapi"` — OpenAPI document
- `bool` — JSON Schema `true`/`false` shorthand (not realistic for paxman but possible)

The Dict DSL surface has its own markers:

- `"id"` at the top level (required)
- `"fields"` at the top level (required, list)
- Each field uses `"name"`, `"type"`, `"required"` keys (not `"properties"`)

These two surfaces are **structurally disjoint** in the markers the detection code checks. The fix is a small set of `in`-checks with the JSON Schema markers first.

**Pros:**

- One-function change (`_detect_format()` in `src/paxman/api/normalize.py:56-99`).
- Matches the user's mental model: a dict that looks like JSON Schema IS JSON Schema.
- Preserves all existing Dict DSL contracts (Dict DSL never has `$schema`, `$defs`, or top-level `properties`).
- No new dependencies, no new public API surface, no schema-version bumps.
- The `JsonSchemaAdapter.adapt()` already accepts dict inputs natively, so the adapter logic does not change.

**Cons:**

- The detection is heuristic — a hand-crafted dict that happens to have both `$schema` and `id` could be ambiguous. In practice, no such legitimate contract exists; the JSON Schema and Dict DSL surfaces are disjoint.
- Future JSON Schema keywords (e.g. `prefixItems` in 2020-12) would require updates to the detection list. Mitigated by the fact that `_detect_format()` falls through to Dict DSL if no JSON Schema marker matches, so missing a new keyword only means the new keyword triggers a misleading error (not a wrong adapter dispatch).
- A user passing a `dict` with `type: "object"` and `properties` (an extremely common JSON Schema pattern) will now hit the JSON Schema adapter even if they intended something else. This is the intended behavior — JSON Schema is the natural interpretation.

### Option B — Try JSON Schema adapter on Dict DSL failure

In `normalize()` after `_detect_and_adapt(contract)` raises `InvalidContractError`, retry with `format_id="json_schema:draft-2020-12"`. If the JSON Schema adapter succeeds, use that contract.

**Pros:**

- No changes to the detection order; Dict DSL keeps priority for dict inputs.
- Works for dicts that look like neither JSON Schema nor Dict DSL — the retry catches the common case.

**Cons:**

- Doubles the dispatch cost on every call (one Dict DSL attempt + one JSON Schema attempt on failure).
- Masks real Dict DSL errors — if both adapters reject the input, the user sees the JSON Schema error, not the Dict DSL error that may be more relevant.
- Slower on the failure path (two full `adapt()` calls).
- Does not match the user's mental model: a `dict` with `type`/`properties` is JSON Schema, not "Dict DSL that we then retry as JSON Schema."

### Option C — Require all users to call the adapter explicitly

Remove auto-detection entirely. Users must call `paxman.contract.adapters.json_schema.JsonSchemaAdapter().adapt(schema)` and pass the resulting `CanonicalContract` to `paxman.normalize()`.

**Pros:**

- Forces users to know which adapter they want.
- Removes the entire class of detection bugs.

**Cons:**

- Breaks the documented `paxman.normalize(input, contract=schema)` quickstart in the README and `welcome.ipynb` and `paxman_tour.ipynb`.
- Violates ADR-0007's promise that contract format detection is built into the public API.
- Mass migration burden on all existing users.

### Option D — Document the current behavior and call it a feature

Keep the current detection order; document that JSON Schema must be passed as a `str` (or a Pydantic model); consider Dict DSL the canonical dict format.

**Pros:**

- No code change.
- Honest about the design choice.

**Cons:**

- The current behavior is contrary to the user's mental model and produces a confusing error message.
- Inconsistent with the documented `JsonSchemaAdapter.adapt()` API which accepts dicts natively.
- Pushes the burden onto the user to know a non-obvious internal detail of paxman.

## Decision Outcome

**Chosen option: A (heuristic: check for JSON Schema markers before routing to Dict DSL).**

`paxman.normalize()` and `paxman.replay()` will route a `dict` contract to `"json_schema:draft-2020-12"` if it has any of the following top-level markers:

- `"$schema"` (JSON Schema dialect declaration — the most authoritative marker)
- `"openapi"` (OpenAPI document — the second authoritative marker; OpenAPI delegation to JSON Schema adapter is unchanged)
- The combination of `"type"` (one of the JSON Schema primitive types) AND one of: `"properties"`, `"required"`, `"$defs"`, `"definitions"`, `"patternProperties"`, `"additionalProperties"`, `"allOf"`, `"anyOf"`, `"oneOf"`, `"not"`, `"items"`, `"prefixItems"`, `"contains"`, `"propertyNames"`, `"minProperties"`, `"maxProperties"`, `"minItems"`, `"maxItems"`, `"uniqueItems"`, `"pattern"`, `"const"`, `"enum"`, `"multipleOf"`, `"minimum"`, `"maximum"`, `"exclusiveMinimum"`, `"exclusiveMaximum"`, `"minLength"`, `"maxLength"`, `"format"`, `"title"`, `"description"`, `"default"`, `"examples"`, `"readOnly"`, `"writeOnly"`, `"deprecated"`, `"contentEncoding"`, `"contentMediaType"`

Otherwise, the dict is routed to `"dict_dsl"` as before.

Rationale:

1. **Disjoint markers** — JSON Schema and Dict DSL use disjoint top-level keys. The heuristic is unambiguous for all real contracts in the wild.
2. **Matches user intent** — a dict with `type`/`properties`/`$schema` is JSON Schema 99% of the time. Routing it to the JSON Schema adapter is the right default.
3. **No API change** — the public function signatures of `paxman.normalize()` and `paxman.replay()` are unchanged. Only the internal dispatch logic is corrected.
4. **Trivially revertable** — if a real-world Dict DSL contract ever uses `$schema` (extremely unlikely; Dict DSL does not have a `$schema` concept), the heuristic can be tightened.
5. **Honors the spirit of ADR-0009** — the Dict DSL remains a "literal Python `dict` structure" and is still detected when it has `id` and `fields` but no JSON Schema markers.

## Consequences

### Positive

- Users passing a JSON Schema `dict` (e.g. loaded via `json.load()`) get a `CanonicalContract` instead of `Status.INVALID_CONTRACT`.
- The error message on rejection becomes useful: `JsonSchemaAdapter` errors are about JSON Schema, not Dict DSL.
- Fixes issues #52, #54, and #55 (broken docstring examples in `normalize()` and `replay()`) with a single change.
- No new dependencies, no new public API surface, no ADR for a "new public API" required for downstream adapters.

### Negative

- The detection logic in `_detect_format()` grows from a 4-line `isinstance` chain to a marker-check function. This is a one-time cost in code complexity.
- Future JSON Schema keywords (e.g. JSON Schema 2020-12 features added later) require updating the marker list. Mitigated by the fact that the fallthrough is `dict_dsl` (so missing a marker gives a misleading error, not a wrong dispatch).

### Neutral

- Documentation: this ADR is the source of truth for the new detection logic. The `EXTENDING.md` guide and the `paxman_tour.ipynb` notebook should be updated to reflect that JSON Schema dicts are now auto-detected.
- The public `paxman.contract.registry` (adapter registry) is unchanged. The four adapters register themselves with the same `format_id` values; only the dispatch logic changes.

## Validation

- `tests/unit/api/test_api_normalize.py` will be updated to assert:
  - `{"type": "object", "properties": {"x": {"type": "string"}}}` is detected as `"json_schema:draft-2020-12"`.
  - `{"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": {"x": {"type": "string"}}}` is detected as `"json_schema:draft-2020-12"`.
  - `{"openapi": "3.1.0", ...}` is detected as `"openapi:3.0"`.
  - `{"id": "x", "fields": [{"name": "y", "type": "STRING", "required": True}]}` (Dict DSL shape) is detected as `"dict_dsl"`.
  - The pre-existing `test_dict_dsl_detected` test that codifies the buggy behavior (passing `{"type": "object", "properties": {}}` and expecting `"dict_dsl"`) will be deleted or rewritten to use a Dict DSL shape.
- `tests/unit/test_contract_json_schema.py` already covers dict input to `JsonSchemaAdapter.adapt()`. No change needed there.
- Round-trip property test (existing): `adapt(export(adapt(d))) == adapt(d)` should pass for both Dict DSL and JSON Schema dict inputs.

## References

- Issue #52: JSON Schema passed as a dict is silently mis-routed to Dict DSL
- Issue #54: `normalize()` docstring example uses a JSON Schema dict that fails at runtime
- Issue #55: `replay()` docstring example uses a JSON Schema dict that fails at runtime
- `0007-contract-adapter-set-v1.md` — V1 adapter set
- `0009-dict-dsl-v1.md` — Dict DSL V1 surface (sibling spec at `../specs/dict-dsl-spec.md`)
- `../reference/extending.md` §1 — adapter SPI
- `src/paxman/api/normalize.py:56-99` — current `_detect_format()` implementation
- `src/paxman/contract/adapters/json_schema.py:149-225` — JSON Schema adapter `adapt()` method
- `src/paxman/contract/adapters/dict_dsl.py` — Dict DSL adapter

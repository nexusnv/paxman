# Paxman 1.0.1 — Release Notes — 2026-07-01

> **Status:** Stable v1.0.x patch release.
> **Audience:** Paxman users, contributors, and reviewers.
> **Related docs:** [CHANGELOG.md](../operations/changelog.md),
> [Release notes v1.0.0](./RELEASE_NOTES_v1.0.0.md),
> [README.md](../index.md).

---

## TL;DR

Paxman 1.0.1 is a patch release that fixes three user-reported
contract-adapter bugs discovered within 96 hours of the 1.0.0
release. **No public API surface change. No core dependencies
changed.** The wheel artifact (`paxman-1.0.1-py3-none-any.whl`) is
bit-for-bit compatible with 1.0.0 on the public surface; only the
three fixed code paths differ. All three bugs were in adapter
detection or translation logic — none touched the planner, executor,
reconciler, artifact, or replay subsystems.

---

## What changed

This is a **patch release** in the strict semver sense: bug fixes
only, no new features, no behavior changes outside the three fixed
code paths, no API removals, no dependency changes.

| Area | Change |
|------|--------|
| Public API | **Unchanged.** All five V1 functions (`normalize`, `replay`, `register_adapter`, `register_capability`, `__version__`) and every public type retain the same signatures. |
| Core dependencies | **Unchanged.** Still `attrs`, `typing-extensions`, `structlog` (3 packages). |
| Optional dependencies | **Unchanged.** `pydantic` is still the only `[pydantic]` extra; `[all]` still installs all four V1 adapters. |
| Wheel artifact | Bit-for-bit compatible with 1.0.0 on the public surface. |
| Replay hash | **Unchanged** for any input that worked in 1.0.0. Artifacts produced under 1.0.0 replay identically under 1.0.1 and vice versa. |
| Test count | 2352 → 2365 tests (13 new tests for the three fixes). |
| Golden artifacts | **Unchanged** — none of the 8 `tests/fixtures/artifacts/*.json` files were regenerated. |

---

## What was fixed

### Fix 1 — JSON Schema `dict` inputs are now routed correctly
**Issue:** [#52](../adr/0011-format-auto-detection-for-json-schema-dicts.md)

**Symptom.** Passing a valid JSON Schema document as a Python `dict`
to `paxman.normalize()` (e.g. a schema loaded via `json.load()` or
an inline fixture) failed with the misleading error
`Dict DSL contract is missing required 'id' key`, even though the
JSON Schema adapter (`format_id="json_schema:draft-2020-12"`) is
registered and natively accepts dict inputs.

**Root cause.** The V1.0.0 detection order in
`_detect_format()` (`src/paxman/api/normalize.py:56-99`) routed any
`dict` unconditionally to the Dict DSL adapter. The JSON Schema
adapter was only consulted when the contract was a `str`.

**Fix.** A `dict` that contains any of the well-known JSON Schema
structural markers — `$schema`, `openapi`, `properties`, `$defs`,
`definitions`, `type` (top-level), `items`, `enum`, `oneOf`,
`anyOf`, `allOf` — is now routed to the JSON Schema adapter. A
`dict` that contains the Dict DSL structural markers (`id` +
`fields`) is still routed to the Dict DSL adapter. The two
surfaces are disjoint, so detection is unambiguous for all real
contracts.

**Why this matters.** This was the most visible of the three bugs
because every backend service that builds contracts in code
(`json.load()`, dynamic schema generation, OpenAPI-to-JSON-Schema
pipelines) hit it on the first call. The fix is documented as
[ADR-0011](../adr/0011-format-auto-detection-for-json-schema-dicts.md).

**Reproduce (before the fix):**

```python
import paxman
import paxman.contract.adapters.json_schema  # noqa: F401

schema = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
}
paxman.normalize(input_data=b"hello", contract=schema)
# ValueError: Dict DSL contract is missing required 'id' key
```

**After the fix** the same call routes to the JSON Schema adapter
and produces a valid `CanonicalContract`.

---

### Fix 2 — OpenAPI 3.0 `nullable: true` is no longer dropped
**Issue:** [#56](#)

**Symptom.** OpenAPI 3.0.x schemas (the most widely deployed
version of OpenAPI in production) use the `nullable: true` keyword
to mark a field as accepting `null` in addition to its declared
type. The V1.0.0 OpenAPI adapter silently dropped this keyword, so
a field declared `nullable: true` in OpenAPI 3.0 was being
represented as `nullable=False` in the resulting
`CanonicalContract`. The Reconciler then rejected `None`
candidates for fields that the contract had declared nullable.

**Root cause.** The OpenAPI 3.0 `nullable: true` keyword has no
direct equivalent in JSON Schema or in the V1 `CanonicalField`
model. The V1.0.0 OpenAPI adapter did not translate it.

**Fix.** The OpenAPI adapter now translates the 3.0
`nullable: true` keyword to the 3.1 `type: [type, "null"]` form
*before* delegating to the JSON Schema adapter. The translation is
applied to every property in the schema and is idempotent for
properties that already use the 3.1 list-type form. OpenAPI 3.1.x
schemas (which natively use `type: [type, "null"]`) are unchanged.

**Reproduce (before the fix):**

```yaml
# openapi.yaml — OpenAPI 3.0.3
components:
  schemas:
    Supplier:
      type: object
      properties:
        notes:
          type: string
          nullable: true   # silently dropped
```

```python
import paxman
import paxman.contract.adapters.openapi  # noqa: F401

contract = paxman.contract.adapters.openapi.adapt(openapi_schema)
# contract.fields["notes"].nullable == False  # wrong
```

**After the fix** `contract.fields["notes"].nullable` is `True`.

---

### Fix 3 — Pydantic nested `BaseModel` fields now map to `OBJECT`
**Issue:** [#57](#)

**Symptom.** A Pydantic field with a direct nested-model
annotation (e.g. `item: LineItem` where `LineItem` is a
`pydantic.BaseModel` subclass) raised
`UnsupportedFieldTypeError` with `error_code="UNSUPPORTED_FIELD_TYPE"`
at `adapt()` time, even though the Pydantic adapter's docstring
explicitly documents this case as supported and the V1 design
treats the `OBJECT` field type as a passthrough (the Reconciler
does not flatten nested schemas in V1).

**Root cause.** `_python_type_to_field_type()` in the Pydantic
adapter did not include a `issubclass(annotation, pydantic.BaseModel)`
branch. The pre-existing `list[BaseModel] → ARRAY` mapping was
correct and is unchanged; the missing branch was the direct (not
list-wrapped) `BaseModel` case.

**Fix.** A new `issubclass(annotation, pydantic.BaseModel)` branch
maps to `FieldType.OBJECT`. This matches the adapter's existing
docstring and the V1 design (the `OBJECT` field type is a
passthrough; nested schemas are not flattened in V1).

**Reproduce (before the fix):**

```python
from pydantic import BaseModel
import paxman
import paxman.contract.adapters.pydantic  # noqa: F401

class LineItem(BaseModel):
    sku: str
    qty: int

class Invoice(BaseModel):
    id: str
    item: LineItem   # raised UNSUPPORTED_FIELD_TYPE

paxman.normalize(input_data=b"x", contract=Invoice)
```

**After the fix** the same call adapts to a `CanonicalContract`
with `item: FieldType.OBJECT`.

---

## What was documented

### Docstring example replacement — `normalize()`
**Issue:** [#54](#)

The previous `paxman.normalize()` docstring example passed a JSON
Schema `dict` that failed at runtime (because of Fix 1). The
example now uses a valid JSON Schema document with explicit
`required` and produces `Status.PARTIAL_SUCCESS` (the honest
result for a row-text invoice with no V1 capabilities registered;
the docstring no longer overpromises `Status.SUCCESS`). Also fixed
an `SyntaxWarning` for an invalid `\$` escape sequence in the same
example.

### Docstring example replacement — `replay()`
**Issue:** [#55](#)

Same root cause as #54: the previous `replay()` example used an
empty `properties: {}` that the JSON Schema adapter rejects. The
new example uses a valid non-empty JSON Schema document and is
marked `# doctest: +SKIP` because the call to `replay()` requires
a complete artifact from `normalize()`.

---

## Upgrade notes

Paxman 1.0.1 is a **drop-in replacement** for 1.0.0. No code
changes are required when upgrading:

```bash
pip install --upgrade paxman
# or
pip install --upgrade paxman[pydantic]
# or
pip install --upgrade paxman[all]
```

- The public API snapshot (`tests/fixtures/public_api_snapshot.json`)
  is unchanged.
- All artifacts produced under 1.0.0 replay identically under
  1.0.1 and vice versa (the `replay_hash` function is unchanged).
- All 8 `tests/fixtures/artifacts/*.json` goldens are unchanged.
- No new core dependencies.
- No new optional dependencies.

If you depended on the V1.0.0 behavior of any of the three
fixed code paths — for example, you were working around the
misrouted JSON Schema `dict` by passing your schemas as JSON
strings — that workaround is no longer required under 1.0.1,
but the workaround continues to work (it was never broken;
it was just no longer necessary).

---

## Verification

| Check | Result |
|-------|--------|
| `make lint` | clean |
| `make format` | clean |
| `make typecheck` (`mypy --strict src/paxman`) | 0 errors |
| `make typecheck-pyright` (`pyright`) | clean |
| `make imports` (`import-linter`) | 6 contracts, 0 broken |
| `make interrogate` | 100% on public surface |
| `make test-unit` | all unit tests pass (new tests included) |
| `make test-property` | all property tests pass |
| `make test-integration` | all integration tests pass |
| `make test-cov` | per-subsystem thresholds met |
| `make build` | `paxman-1.0.1-py3-none-any.whl` + sdist produced |
| `make test-public-api` | snapshot unchanged |
| `make test-examples` | 3 reference examples pass |

**Test count:** 2352 → 2365 (13 new tests: 8 for the JSON Schema
detection heuristic, 5 for the OpenAPI `nullable` translation,
plus the 2 for the Pydantic `BaseModel` mapping that were absorbed
from the existing 1.0.0 suite).

**ADRs added:** [ADR-0011](../adr/0011-format-auto-detection-for-json-schema-dicts.md) —
Format auto-detection for JSON Schema `dict` inputs. The OpenAPI
`nullable` translation and Pydantic `BaseModel` mapping fixes
were small enough to land as direct commits and did not require
new ADRs.

---

## Reference

- [Release notes v1.0.0](./RELEASE_NOTES_v1.0.0.md) — what shipped in
  the first stable release.
- [CHANGELOG.md](../operations/changelog.md) — full release history.
- [ADR-0011](../adr/0011-format-auto-detection-for-json-schema-dicts.md) —
  architectural decision for Fix 1.
- [README.md](../index.md) — quickstart and usage guide.
- [ARCHITECTURE.md](../reference/architecture.md) — subsystem design and
  sequence diagram.
- [GLOSSARY.md](../reference/glossary.md) — vocabulary.
- [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md) —
  replay model deep dive.
- [SECURITY.md](../security/index.md) — threat model and PII handling.
- [EXTENDING.md](../reference/extending.md) — how to add adapters,
  capabilities, and inference providers.
- [docs/concepts/](./) — conceptual docs (contracts, capabilities,
  planning, reconciliation, replay, migration guide).
- [docs/howto/](../howto/) — quick-start how-tos.
- [examples/](../../examples/) — reference examples.

---

## See also: what was *not* in 1.0.1

For users reading the v1.0.0 release notes and looking for a
signal on which deferred V2 features are closest to landing,
1.0.1 contains **no movement** on any V2 item. The deferred list
is unchanged from v1.0.0:

- LLM planner (V2)
- Async API (V2)
- Parallel field execution (V2)
- Real inference provider integrations — OpenAI, Anthropic,
  Cohere (V2)
- RAG framework integration (V2)
- OpenAPI 3.1 full coverage (V2)
- Pyright strict mode (V2)
- Migration tools (V2)

Paxman 1.0.1 is, intentionally, the smallest possible patch
release: three bugs fixed, two docstring examples corrected, zero
new features.

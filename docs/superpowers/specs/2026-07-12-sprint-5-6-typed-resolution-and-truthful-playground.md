# Combined Sprint 5–6: Typed Resolution and Truthful Playground

## Goal

Make explicitly extracted scalar values usable for the contract's declared
type, while ensuring every example and notebook reports unresolved outcomes
plainly rather than treating pipeline completion as successful normalization.

## Problem

Sprint 4 safely extracts a named string capture and can apply explicit string
cleanup. It intentionally does not coerce that string to `INTEGER`, `DECIMAL`,
`BOOLEAN`, or `DATE`; Sprint 1 therefore rejects those candidates. The
playground additionally contains legacy notebooks that assert `SUCCESS` for
unconfigured contracts or describe document-wide text extraction as field
resolution. Together these gaps make normal, typed document normalization
appear less capable than it should be and can still mislead users about an
unresolved result.

## Scope

This combined sprint introduces explicit, deterministic candidate preparation
inside the Reconciler after contract-declared extraction. It supports exactly:

- `INTEGER`: base-10 signed integer text;
- `DECIMAL`: decimal text parsed without floats;
- `BOOLEAN`: an explicitly supplied, closed true/false token mapping;
- `DATE`: an explicitly supplied `strptime` format;
- `STRING`: no parse stage is needed; Sprint 3 cleanup remains sufficient.

No parser is inferred from a field name, description, raw input, locale, or
value shape. There is no generic “best effort” coercion and no default date,
boolean, currency, or number format. `MONEY`, `ENUM`, `OBJECT`, and `ARRAY`
remain unresolved unless a future, separately designed capability supplies a
typed candidate.

## Contract Shape

`parse` is an optional field declaration, accepted only with `extract` and
normalised across all adapters:

```python
{
    "name": "total",
    "type": "DECIMAL",
    "extract": {
        "capability": "regex_extraction",
        "config": {"pattern": r"Total:\s*(?P<value>\d+\.\d{2})"},
    },
    "parse": {"kind": "decimal"},
}
```

Dict DSL uses `parse`; JSON Schema/OpenAPI use `x-paxman-parse`; Pydantic uses
the same extension in `json_schema_extra`. Each parser configuration is
validated during adaptation and made immutable in the canonical contract.

The planner remains unchanged: it emits the declared extractor and any string
cleanup chain. Before candidate eligibility filtering, the Reconciler prepares
each candidate according to the field's `parse` declaration. String cleanup
therefore runs before parsing. Invalid parse input drops only that candidate
and emits a field diagnostic; reconciliation then reports the field
`UNRESOLVED`.

## Authority and Evidence

Candidate preparation is deterministic Reconciler logic: it reads a candidate,
its canonical field, and the immutable parser declaration; it never reads raw
input or executes a capability. Every converted candidate receives parse
provenance and failed conversions receive a field diagnostic. Decimal
construction stays in `reconciler/money.py`, the sole permitted `decimal`
import location.

## Truthful Reporting

No new public API is added. The artifact remains the source of truth:

- `artifact.status` is the run outcome;
- `artifact.unresolved_fields` names fields not accepted by the reconciler;
- `artifact.field_results[path].status`, value, confidence, and evidence are
  the per-field outcome;
- artifact diagnostics explain parser and resolution failures.

Update playground notebooks 01 and 09 so they either use explicit extraction
and parsing declarations or visibly label the result `UNRESOLVED` /
`PARTIAL_SUCCESS`. Remove assertions that require `SUCCESS` merely because an
adapter accepted a contract. Add executable notebook tests that reject code or
markdown claims of successful field normalization when the shown artifact has
unresolved required fields.

## Non-goals

- No LLM, inference, generated regex, locale inference, OCR, or raw-document
  fallback.
- No coercion of unconstrained strings.
- No public function, confidence change, replay recomputation, or persistence.
- No parsing of nested arrays/objects in this sprint.

## Acceptance Criteria

1. Explicit regex extraction plus explicit parsing resolves each supported
   scalar type with evidence and deterministic replay.
2. Invalid declared parser configuration fails contract adaptation; invalid
   candidate text resolves no field and is diagnosed.
3. A parser is never applied without an explicit extractor.
4. All existing fields without `parse` keep their Sprint 4 behavior.
5. Notebook execution and static checks demonstrate truthful status handling;
   no notebook asserts success for an unconfigured contract.
6. Full tests, format, lint, strict mypy, docs checks, playground notebook
   execution, and coverage thresholds pass.

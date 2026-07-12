# Sprint 4: Explicit Extraction Design

## Goal

Allow a contract to supply the field-specific extraction configuration required
to normalize a value from plain text, without restoring document-wide fallback
resolution or field-name heuristics.

## Contract Declaration

The Dict DSL uses an `extract` object; JSON Schema and OpenAPI use the
`x-paxman-extract` extension; Pydantic supplies that extension through
`json_schema_extra`.

```python
{
    "capability": "regex_extraction",
    "config": {"pattern": r"Invoice\\s*#(?P<value>\\S+)"},
}
```

Sprint 4 accepts only `regex_extraction@1.0`. Its existing capability parser
remains responsible for regex semantics; the contract parser validates the
declaration shape and requires a non-empty string `pattern`. Invalid or
unknown declarations are invalid contracts, not runtime planning failures.

## Canonical and Planner Behavior

Adapters normalize the declaration into immutable canonical extraction
metadata. `build_capability_chain` selects exactly that extraction step when
present. It may append the explicit cleanup steps introduced in Sprint 3, in
their declared order, with `input_from_candidate: true`.

Existing format-aware extraction remains unchanged. A field declares either
format-aware extraction (`format_hints`) or explicit regex extraction in
Sprint 4; declaring both is rejected as ambiguous. A field with neither
declaration remains unresolved.

## Safety Boundary

The planner will not infer extraction configuration from a field name,
description, type, semantic tag, or raw input. It will not schedule a cleanup
step unless the field's declared extractor produced candidates. The change
does not add a public function, provider, or fallback behavior.

## Validation

Tests cover declaration parsing and round-tripping across all adapters,
ambiguous declarations, deterministic planner ordering, and `normalize()` on
plain text that extracts then cleans a value with the full evidence chain.

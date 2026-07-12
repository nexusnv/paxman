# Sprint 3: Deterministic Cleanup Chain Design

## Goal

Make explicitly configured, format-aware extraction plans produce normalized
string candidates through the existing executor hand-off mechanism, without
adding public API or applying a cleanup transform by default.

## Scope

Sprint 3 changes planner synthesis only.  For a configured format-aware
extractor, the planner may append an explicitly declared cleanup step after
the extractor.  Each appended step has `input_from_candidate: true`, allowing
the Sprint 2 executor behavior to pass the upstream candidate value in
`config["value"]`.

The supported cleanup steps are the existing `trim_extraction@1.0` and
`case_normalization@1.0` capabilities.  Their existing configuration remains
authoritative: trim's `chars` and case normalization's `mode` must be
explicitly supplied by the plan configuration.

## Safety Boundary

No cleanup step is inferred from a field's type, name, description, format
hint, or input content.  In particular, the planner must not append default
trimming or case normalization to every STRING field.  Such an inference can
change a legitimate value and would violate the recovery program's truthful
resolution boundary.

The change must not broaden automatic resolution beyond the existing
format-aware extractor selected by `select_format_aware`.  A field without a
matching, configured extractor remains unresolved.

## Contract Declaration and Representation

The declaration is contract-level metadata on a field.  The Dict DSL uses
`cleanup`; JSON Schema and OpenAPI use `x-paxman-cleanup`; and Pydantic uses
the same JSON-Schema extension through `json_schema_extra`.  Every adapter
normalizes that wire form into one canonical, immutable cleanup-step record.

Each entry has a capability id and an optional capability-specific `config`:

```python
{"capability": "trim_extraction"}
{"capability": "case_normalization", "config": {"mode": "lower"}}
```

Only the existing `trim_extraction@1.0` and `case_normalization@1.0` ids are
accepted.  A case-normalization entry must explicitly provide a supported
mode; trim may omit configuration and use its documented capability default.
The parser rejects malformed entries and unknown cleanup ids as invalid
contracts rather than letting a planned run fail later.

`build_capability_chain` emits the extractor first, then the cleanup steps in
declared order.  It adds `input_from_candidate: true` to each cleanup step
while preserving the cleanup capability's own configuration.  This produces
internal plan data, not a new public function or parameter.

## Failure Handling and Evidence

The executor remains the execution authority.  A cleanup failure drops only
the affected candidate and emits its diagnostic.  Successful cleanup outputs
retain both upstream extractor evidence and transform evidence, as delivered
by Sprint 2.

## Validation

Tests will prove that a configured format-aware extractor followed by trim
and/or case normalization is emitted in deterministic order, includes the
hand-off flag, and resolves an end-to-end normalization case with the complete
evidence chain.  Regression tests will prove that unconfigured fields and
format-aware fields without explicit cleanup configuration retain their
current plan shape.

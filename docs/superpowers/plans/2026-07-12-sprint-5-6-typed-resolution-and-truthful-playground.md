# Combined Sprint 5–6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit typed parsing after safe extraction and make playground outcomes truthful.

**Architecture:** Canonical parser metadata drives deterministic Reconciler candidate preparation before eligibility filtering. Adapter validation prevents implicit parsing; the existing reconciler remains the sole truth and confidence authority. Playground notebooks consume only artifact outcomes.

**Tech Stack:** Python 3.11+, attrs, pytest, Hypothesis, Jupyter nbconvert, mypy, ruff.

---

### Task 1: Canonical parser metadata

**Files:**
- Create: `src/paxman/contract/_parse.py`
- Modify: `src/paxman/contract/canonical.py`
- Test: `tests/unit/contract/test_parse.py`

- [ ] **Step 1: Write failing parser tests**

```python
def test_parse_spec_accepts_decimal_for_decimal_field() -> None:
    assert parse_spec({"kind": "decimal"}, field_name="total", field_type=FieldType.DECIMAL)


@pytest.mark.parametrize("raw", [{"kind": "date"}, {"kind": "integer"}])
def test_parse_spec_rejects_kind_for_wrong_field_type(raw: object) -> None:
    with pytest.raises(ParseValidationError):
        parse_spec(raw, field_name="total", field_type=FieldType.DECIMAL)
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest tests/unit/contract/test_parse.py -q`

Expected: missing parser module.

- [ ] **Step 3: Implement `ParseSpec` and strict declaration validation**

```python
@attrs.frozen(slots=True)
class ParseSpec:
    kind: Literal["integer", "decimal", "boolean", "date"]
    config: Mapping[str, object]
```

Require `boolean.true_values` and `boolean.false_values` to be disjoint,
require `date.format`, and reject all type/kind mismatches. Add
`parse_spec: ParseSpec | None` to
`CanonicalField`; require an extraction step when a parse spec is present.

- [ ] **Step 4: Run GREEN and commit**

Run: `pytest tests/unit/contract/test_parse.py -q`

Run: `git add src/paxman/contract/_parse.py src/paxman/contract/canonical.py tests/unit/contract/test_parse.py && git commit -m "feat(contract): add typed parse metadata"`

### Task 2: Adapter declarations and round trips

**Files:**
- Modify: `src/paxman/contract/adapters/dict_dsl.py`
- Modify: `src/paxman/contract/adapters/json_schema.py`
- Modify: `src/paxman/contract/adapters/pydantic.py`
- Test: `tests/unit/test_contract_dict_dsl.py`
- Test: `tests/unit/test_contract_json_schema.py`
- Test: `tests/unit/test_contract_pydantic.py`
- Test: `tests/unit/test_contract_openapi.py`

- [ ] **Step 1: Add failing adapter round-trip tests**

```python
def test_decimal_parse_round_trips() -> None:
    canonical = adapter.adapt({..., "extract": REGEX, "parse": {"kind": "decimal"}})
    assert canonical.fields[0].parse_spec.kind == "decimal"
    assert adapter.export(canonical)[...]["parse"] == {"kind": "decimal"}
```

Add equivalent `x-paxman-parse` tests for JSON Schema, Pydantic, and OpenAPI.

- [ ] **Step 2: Run and confirm RED**

Run: `pytest tests/unit/test_contract_dict_dsl.py tests/unit/test_contract_json_schema.py tests/unit/test_contract_pydantic.py tests/unit/test_contract_openapi.py -q`

Expected: parser metadata is absent.

- [ ] **Step 3: Parse and export the forms**

```python
# Dict DSL: parse_spec=parse_spec(raw.get("parse"), field_name=name, field_type=field_type)
# Schema:   parse_spec=self._extract_parse(name, schema, field_type, contract_id)
# Pydantic: parse_spec=self._extract_parse(name, field_info, field_type, model_cls)
```

Wrap `ParseValidationError` as `InvalidContractError` with existing adapter
context conventions. OpenAPI inherits JSON Schema behavior.

- [ ] **Step 4: Run GREEN and commit**

Run: same focused adapter command.

Run: `git add src/paxman/contract/adapters tests/unit/test_contract_*.py && git commit -m "feat(contract): parse typed parser declarations"`

### Task 3: Deterministic Reconciler candidate preparation

**Files:**
- Create: `src/paxman/reconciler/parsing.py`
- Modify: `src/paxman/reconciler/reconciler.py`
- Modify: `src/paxman/reconciler/money.py`
- Test: `tests/unit/reconciler/test_parsing.py`
- Test: `tests/property/test_reconciler_parsing_determinism.py`

- [ ] **Step 1: Write failing unit tests for every supported parser**

```python
@pytest.mark.parametrize(("value", "config", "expected"), [
    ("42", {"kind": "integer"}, 42),
    ("12.50", {"kind": "decimal"}, Decimal("12.50")),
    ("yes", {"kind": "boolean", "true_values": ["yes"], "false_values": ["no"]}, True),
    ("2026-07-12", {"kind": "date", "format": "%Y-%m-%d"}, "2026-07-12"),
])
def test_prepare_candidate_returns_typed_candidate_with_provenance(...): ...
```

Add failures for invalid text and config; assert zero candidates plus a
structured diagnostic. Add a `derandomize=True` property test asserting same
input/config produces byte-equal result.

- [ ] **Step 2: Run and confirm RED**

Run: `pytest tests/unit/reconciler/test_parsing.py tests/property/test_reconciler_parsing_determinism.py -q`

Expected: candidate preparation helper absent.

- [ ] **Step 3: Implement capability within subsystem boundaries**

`prepare_candidates` reads only `Candidate` records, the canonical field, and
its `ParseSpec`; it never reads raw input or assigns confidence. It returns
prepared candidates plus diagnostics. Delegate Decimal construction to a small
pure helper in `reconciler/money.py` to preserve the Decimal-only import
boundary.

- [ ] **Step 4: Run GREEN and commit**

Run: focused reconciler/property command.

Run: `git add src/paxman/reconciler tests/unit/reconciler/test_parsing.py tests/property/test_reconciler_parsing_determinism.py && git commit -m "feat(reconciler): prepare typed candidates"`

### Task 4: End-to-end truthful outcomes

**Files:**
- Modify: `tests/integration/test_truthful_resolution.py`
- Create: `tests/integration/test_typed_resolution.py`
- Modify: `docs/concepts/planning.md`
- Modify: `docs/specs/dict-dsl-spec.md`

- [ ] **Step 1: Write failing public API tests**

```python
def test_explicit_decimal_extraction_resolves_decimal_not_string() -> None:
    artifact = paxman.normalize("Total: 12.50", DECIMAL_CONTRACT)
    assert artifact.status is Status.SUCCESS
    assert artifact.normalized_data == {"total": Decimal("12.50")}


def test_invalid_explicit_decimal_is_unresolved_with_diagnostic() -> None:
    artifact = paxman.normalize("Total: twelve", DECIMAL_CONTRACT)
    assert artifact.status is Status.UNRESOLVED
    assert artifact.normalized_data == {}
    assert artifact.unresolved_fields == ["total"]
```

Add equivalent integer, boolean, and date scenarios, evidence-chain
assertions, and replay-hash equality.

- [ ] **Step 2: Run and confirm RED**

Run: `pytest tests/integration/test_typed_resolution.py tests/integration/test_truthful_resolution.py -q`

Expected: typed fields are unresolved before the parser stage exists.

- [ ] **Step 3: Document declaration and outcome rules**

Document each `parse` form, the extractor prerequisite, parser failure
semantics, and the distinction between `SUCCESS`, `PARTIAL_SUCCESS`, and
`UNRESOLVED`.

- [ ] **Step 4: Run GREEN and commit**

Run: focused integration command.

Run: `git add tests/integration docs/concepts/planning.md docs/specs/dict-dsl-spec.md && git commit -m "test: cover typed resolution outcomes"`

### Task 5: Repair playground claims and execute notebooks

**Files:**
- Modify: `playground/notebooks/01-basics-contracts.ipynb`
- Modify: `playground/notebooks/09-full-pipeline-invoice.ipynb`
- Modify: `playground/tests/test_notebook_smoke.py`
- Modify: `playground/README.md`

- [ ] **Step 1: Add failing notebook assertions**

Require notebooks 01 and 09 to display `artifact.status`,
`artifact.unresolved_fields`, and each field status. Add a static regression
test rejecting the legacy text `status != paxman.Status.SUCCESS` gate and the
claim that text extraction returns a field value.

- [ ] **Step 2: Run and confirm RED**

Run: `pytest playground/tests/test_notebook_smoke.py -q`

Expected: notebook 01 contains the legacy success gate.

- [ ] **Step 3: Make notebook examples truthful**

Use explicit extraction and parse declarations for successful scalar examples.
For intentionally unconfigured examples, print the artifact status and explain
why it is unresolved; never raise because it is not `SUCCESS`. Update notebook
09 narrative to distinguish pipeline execution from resolved fields. Update
the README notebook descriptions accordingly.

- [ ] **Step 4: Run static and headless notebook tests**

Run: `pytest playground/tests/test_notebook_smoke.py -q && bash playground/tooling/run_notebooks.sh playground/notebooks`

Expected: all notebooks execute; no internal-import or false-success claim
remains.

- [ ] **Step 5: Commit**

Run: `git add playground && git commit -m "docs(playground): report normalization outcomes truthfully"`

### Task 6: Full validation and handoff

**Files:**
- Verify only: all combined Sprint 5–6 changes

- [ ] **Step 1: Run complete quality gates**

Run: `make ci && pytest playground/tests -q && bash playground/tooling/run_notebooks.sh playground/notebooks`

Expected: all CI and notebook checks pass.

- [ ] **Step 2: Run replay and adversarial regression subsets**

Run: `pytest tests/integration/test_replay_integrity.py tests/integration/end_to_end/test_adversarial_inputs.py tests/integration/test_truthful_resolution.py -q`

Expected: replay remains pure and all unsafe/unconfigured values remain unresolved.

- [ ] **Step 3: Inspect delivery state**

Run: `git diff main...HEAD --check && git status --short && git log --oneline main..HEAD`

Expected: no whitespace errors; only combined Sprint 5–6 commits are present.

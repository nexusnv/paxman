# Sprint 4 Explicit Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize plain-text values only through an explicitly configured regex extractor, optionally followed by explicit cleanup.

**Architecture:** Introduce immutable canonical extraction metadata parsed from `extract` / `x-paxman-extract`. The planner selects that single extractor in place of format-aware dispatch and appends existing cleanup hand-off steps; a field declaring both paths is invalid.

**Tech Stack:** Python 3.11+, attrs, pytest, mypy, ruff.

---

### Task 1: Canonical extraction declaration

**Files:**
- Create: `src/paxman/contract/_extraction.py`
- Modify: `src/paxman/contract/canonical.py`
- Test: `tests/unit/contract/test_extraction.py`

- [ ] **Step 1: Write failing parser tests**

```python
def test_parse_extraction_accepts_regex_pattern() -> None:
    step = parse_extraction(
        {"capability": "regex_extraction", "config": {"pattern": r"ID:(?P<value>\\w+)"}},
        field_name="invoice_id",
    )
    assert step.capability_id == "regex_extraction"


@pytest.mark.parametrize("raw", [
    {"capability": "text_extraction", "config": {}},
    {"capability": "regex_extraction", "config": {}},
    {"capability": "regex_extraction", "config": {"pattern": ""}},
])
def test_parse_extraction_rejects_unsafe_or_incomplete_declarations(raw: object) -> None:
    with pytest.raises(ExtractionValidationError) as exc_info:
        parse_extraction(raw, field_name="invoice_id")
    assert exc_info.value.error_code == "INVALID_EXTRACTION"
```

- [ ] **Step 2: Verify failure**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/contract/test_extraction.py -q`

Expected: import failure for `_extraction`.

- [ ] **Step 3: Implement canonical metadata**

```python
@attrs.frozen(slots=True)
class ExtractionStep:
    capability_id: str
    config: Mapping[str, object] = attrs.field(converter=_freeze_config)


def parse_extraction(raw: object, *, field_name: str) -> ExtractionStep | None:
    # None -> None; otherwise require exactly regex_extraction and a non-empty pattern.
```

Add `extraction_step: ExtractionStep | None = None` to `CanonicalField`.

- [ ] **Step 4: Verify passing tests and commit**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/contract/test_extraction.py -q`

Run: `git add src/paxman/contract/_extraction.py src/paxman/contract/canonical.py tests/unit/contract/test_extraction.py && git commit -m "feat(contract): add explicit extraction metadata"`

### Task 2: Adapter support and ambiguity validation

**Files:**
- Modify: `src/paxman/contract/adapters/dict_dsl.py`
- Modify: `src/paxman/contract/adapters/json_schema.py`
- Modify: `src/paxman/contract/adapters/pydantic.py`
- Test: `tests/unit/test_contract_dict_dsl.py`
- Test: `tests/unit/test_contract_json_schema.py`
- Test: `tests/unit/test_contract_pydantic.py`
- Test: `tests/unit/test_contract_openapi.py`

- [ ] **Step 1: Write failing adapter tests**

```python
def test_dict_dsl_extract_round_trip() -> None:
    canonical = _adapter().adapt({"id": "c", "fields": [{
        "name": "invoice_id", "type": "STRING", "required": True,
        "extract": {"capability": "regex_extraction", "config": {"pattern": r"ID:(?P<value>\\w+)"}},
    }]})
    assert canonical.fields[0].extraction_step is not None


def test_dict_dsl_rejects_extract_with_format_hints() -> None:
    with pytest.raises(InvalidContractError, match="ambiguous"):
        _adapter().adapt({"id": "c", "fields": [{
            "name": "invoice_id", "type": "STRING", "required": True,
            "format_hints": ["csv"],
            "extract": {"capability": "regex_extraction", "config": {"pattern": "x"}},
        }]})
```

- [ ] **Step 2: Verify failure**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/test_contract_dict_dsl.py tests/unit/test_contract_json_schema.py tests/unit/test_contract_pydantic.py tests/unit/test_contract_openapi.py -q`

Expected: extraction metadata is absent and ambiguity is accepted.

- [ ] **Step 3: Implement wire-form parsing and exports**

```python
# Dict DSL
extraction_step=parse_extraction(raw.get("extract"), field_name=name)

# JSON Schema family
extraction_step=self._extract_extraction(name, schema_or_field_info, identity)

# Export forms
out["extract"] = field.extraction_step.to_wire()
out["x-paxman-extract"] = field.extraction_step.to_wire()
```

Reject a field carrying both a non-empty `format_hints` and an extraction step with `InvalidContractError(error_code="AMBIGUOUS_EXTRACTION")`. OpenAPI inherits the JSON Schema behavior.

- [ ] **Step 4: Verify passing tests and commit**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/test_contract_dict_dsl.py tests/unit/test_contract_json_schema.py tests/unit/test_contract_pydantic.py tests/unit/test_contract_openapi.py -q`

Run: `git add src/paxman/contract/adapters tests/unit/test_contract_dict_dsl.py tests/unit/test_contract_json_schema.py tests/unit/test_contract_pydantic.py tests/unit/test_contract_openapi.py && git commit -m "feat(contract): parse explicit extraction"`

### Task 3: Planner dispatch and public integration

**Files:**
- Modify: `src/paxman/planner/heuristics.py`
- Modify: `tests/unit/planner/test_heuristics_format_hints.py`
- Modify: `tests/integration/test_truthful_resolution.py`
- Modify: `docs/specs/dict-dsl-spec.md`
- Modify: `docs/concepts/planning.md`

- [ ] **Step 1: Write failing planner and integration tests**

```python
def test_build_chain_uses_declared_regex_before_cleanup() -> None:
    field = _field(extraction_step=ExtractionStep("regex_extraction", {"pattern": r"ID:(?P<value>\\w+)"}),
                   cleanup_steps=(CleanupStep("trim_extraction"),))
    chain = build_capability_chain(field, make_profile(b"ID: A-1"), Policy(), None)
    assert [step.capability_id for step in chain] == ["regex_extraction", "trim_extraction"]


def test_plain_text_contract_with_declared_regex_resolves_only_the_capture() -> None:
    artifact = paxman.normalize(input_data="ID: A-1", contract=CONTRACT)
    assert artifact.normalized_data == {"invoice_id": "A-1"}
```

- [ ] **Step 2: Verify failure**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/planner/test_heuristics_format_hints.py tests/integration/test_truthful_resolution.py -q`

Expected: planner emits no regex step; normalized data is empty.

- [ ] **Step 3: Implement explicit dispatch**

```python
if field.extraction_step is not None:
    chain = [FieldPlanStep(
        capability_id=field.extraction_step.capability_id,
        capability_version="1.0",
        config=field.extraction_step.config,
        note="contract-configured extraction",
    )]
else:
    chain = select_format_aware(field, registry)
```

Append configured cleanup only when the resulting chain is non-empty. Document the `extract` key and its no-heuristics safety boundary.

- [ ] **Step 4: Verify full behavior and commit**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/planner tests/integration/test_truthful_resolution.py -q`

Run: `git add src/paxman/planner/heuristics.py tests/unit/planner tests/integration/test_truthful_resolution.py docs/specs/dict-dsl-spec.md docs/concepts/planning.md && git commit -m "feat(planner): dispatch explicit extraction"`

### Task 4: Full validation

**Files:**
- Verify only: changed Sprint 4 files

- [ ] **Step 1: Run all tests and coverage thresholds**

Run: `pytest tests -q --cov=src/paxman --cov-branch --cov-report=term && python scripts/check_subsystem_coverage.py`

Expected: all tests pass, coverage remains at least 90%, and all D7.15 thresholds pass.

- [ ] **Step 2: Run static validation and inspect the branch**

Run: `ruff check src/paxman tests && ruff format --check src/paxman tests && mypy --strict src/paxman && git diff --check && git status --short`

Expected: all checks pass and the worktree is clean after commits.

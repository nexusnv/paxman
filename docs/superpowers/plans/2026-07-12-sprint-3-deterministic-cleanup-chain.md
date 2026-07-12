# Sprint 3 Deterministic Cleanup Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow explicitly declared field cleanup steps to follow a selected format-aware extractor through the Sprint 2 candidate hand-off path.

**Architecture:** Contract adapters normalize `cleanup` / `x-paxman-cleanup` entries into immutable canonical metadata. The planner appends only those declared cleanup steps after `select_format_aware` selects an extractor, and sets `input_from_candidate: true`.

**Tech Stack:** Python 3.11+, attrs, pytest, mypy, ruff.

---

### Task 1: Add canonical cleanup metadata

**Files:**
- Create: `src/paxman/contract/_cleanup.py`
- Modify: `src/paxman/contract/canonical.py`
- Modify: `src/paxman/contract/__init__.py`
- Test: `tests/unit/contract/test_cleanup.py`

- [ ] **Step 1: Write the failing parser tests**

```python
def test_parse_cleanup_preserves_declared_order() -> None:
    steps = parse_cleanup(
        [{"capability": "trim_extraction"},
         {"capability": "case_normalization", "config": {"mode": "lower"}}],
        field_name="supplier",
    )
    assert [step.capability_id for step in steps] == ["trim_extraction", "case_normalization"]
    assert steps[1].config == {"mode": "lower"}


@pytest.mark.parametrize("raw", [
    [{"capability": "unknown"}],
    [{"capability": "case_normalization"}],
    [{"capability": "trim_extraction", "config": []}],
])
def test_parse_cleanup_rejects_invalid_entries(raw: object) -> None:
    with pytest.raises(CleanupValidationError, match="INVALID_CLEANUP"):
        parse_cleanup(raw, field_name="supplier")
```

- [ ] **Step 2: Verify the tests fail**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/contract/test_cleanup.py -q`

Expected: import failure for the new cleanup module.

- [ ] **Step 3: Implement the immutable metadata**

```python
@attrs.frozen(slots=True)
class CleanupStep:
    capability_id: str
    config: Mapping[str, object] = attrs.field(converter=_freeze_config)


def parse_cleanup(raw: object, *, field_name: str) -> tuple[CleanupStep, ...]:
    # None -> (); otherwise require a list of mappings.
    # Permit only trim_extraction and case_normalization.
    # Require a supported string mode for case_normalization.
```

Add `cleanup_steps: tuple[CleanupStep, ...] = ()` to `CanonicalField` and validate that every entry is a `CleanupStep`.

- [ ] **Step 4: Verify the tests pass**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/contract/test_cleanup.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/paxman/contract/_cleanup.py src/paxman/contract/canonical.py src/paxman/contract/__init__.py tests/unit/contract/test_cleanup.py && git commit -m "feat(contract): add explicit cleanup metadata"`

### Task 2: Normalize adapter declarations

**Files:**
- Modify: `src/paxman/contract/adapters/dict_dsl.py`
- Modify: `src/paxman/contract/adapters/json_schema.py`
- Modify: `src/paxman/contract/adapters/pydantic.py`
- Test: `tests/unit/contract/test_dict_dsl_adapter.py`
- Test: `tests/unit/contract/test_json_schema_adapter.py`
- Test: `tests/unit/contract/test_pydantic_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

```python
def test_dict_dsl_cleanup_is_canonicalized() -> None:
    contract = DictDslAdapter().adapt({"id": "c", "fields": [
        {"name": "supplier", "type": "STRING", "required": True,
         "cleanup": [{"capability": "trim_extraction"}]},
    ]})
    assert contract.fields[0].cleanup_steps[0].capability_id == "trim_extraction"


def test_json_schema_cleanup_extension_is_canonicalized() -> None:
    contract = JsonSchemaAdapter().adapt({"title": "c", "type": "object", "properties": {
        "supplier": {"type": "string", "x-paxman-cleanup": [
            {"capability": "case_normalization", "config": {"mode": "lower"}}
        ]},
    }})
    assert contract.fields[0].cleanup_steps[0].config == {"mode": "lower"}
```

- [ ] **Step 2: Verify the tests fail**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/contract/test_dict_dsl_adapter.py tests/unit/contract/test_json_schema_adapter.py tests/unit/contract/test_pydantic_adapter.py -q`

Expected: assertions report no cleanup metadata.

- [ ] **Step 3: Implement both wire forms and exports**

```python
# Dict DSL field parser
cleanup_steps=parse_cleanup(raw.get("cleanup"), field_name=name)

# JSON Schema / Pydantic extension parser
cleanup_steps=self._extract_cleanup(name, schema_or_field_info, contract_identity)

# JSON Schema exporter
out["x-paxman-cleanup"] = [step.to_wire() for step in field.cleanup_steps]
```

Wrap `CleanupValidationError` as `InvalidContractError`, using the same context structure as `format_hints`. Do not edit `openapi.py`: it delegates schema adaptation/export to `JsonSchemaAdapter`.

- [ ] **Step 4: Verify the tests pass**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/contract/test_dict_dsl_adapter.py tests/unit/contract/test_json_schema_adapter.py tests/unit/contract/test_pydantic_adapter.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/paxman/contract/adapters/dict_dsl.py src/paxman/contract/adapters/json_schema.py src/paxman/contract/adapters/pydantic.py tests/unit/contract && git commit -m "feat(contract): parse cleanup declarations"`

### Task 3: Plan cleanup only after selected extraction

**Files:**
- Modify: `src/paxman/planner/heuristics.py`
- Test: `tests/unit/test_planner_heuristics_planner.py`

- [ ] **Step 1: Write failing planner tests**

```python
def test_build_capability_chain_appends_configured_cleanup_after_extractor() -> None:
    field = _field(
        format_hints=(FormatHint.CSV,),
        cleanup_steps=(CleanupStep("trim_extraction"),),
    )
    chain = build_capability_chain(field, _profile(), Policy(), None, _csv_registry())
    assert [step.capability_id for step in chain] == ["csv_extraction", "trim_extraction"]
    assert chain[1].config == {"input_from_candidate": True}


def test_cleanup_is_not_planned_without_a_matching_extractor() -> None:
    field = _field(cleanup_steps=(CleanupStep("trim_extraction"),))
    assert build_capability_chain(field, _profile(), Policy(), None, {}) == ()
```

- [ ] **Step 2: Verify the tests fail**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/test_planner_heuristics_planner.py -q`

Expected: the first test reports only `csv_extraction`.

- [ ] **Step 3: Append the guarded hand-off steps**

```python
chain = select_format_aware(field, registry)
if not chain:
    return ()
for cleanup in field.cleanup_steps:
    chain.append(FieldPlanStep(
        capability_id=cleanup.capability_id,
        capability_version="1.0",
        config={**cleanup.config, "input_from_candidate": True},
        note="configured post-extraction cleanup",
    ))
return tuple(chain)
```

- [ ] **Step 4: Verify the tests pass**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/test_planner_heuristics_planner.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/paxman/planner/heuristics.py tests/unit/test_planner_heuristics_planner.py && git commit -m "feat(planner): plan configured cleanup chains"`

### Task 4: Prove end-to-end normalization and document it

**Files:**
- Modify: `tests/fixtures/contracts/dict_dsl/with_cleanup_chain.py`
- Modify: `tests/integration/capabilities/test_cleanup_transforms_chain.py`
- Modify: `docs/specs/dict-dsl-spec.md`
- Modify: `docs/concepts/planning.md`

- [ ] **Step 1: Write the failing integration test**

```python
def test_normalize_applies_configured_csv_cleanup_chain() -> None:
    artifact = paxman.normalize(input_data=_load_csv(), contract=DICT_DSL_WITH_CLEANUP_CHAIN)
    assert artifact.normalized_data["supplier"] == "acme corp"
    evidence = artifact.field_results["supplier"].evidence_refs
    assert [ref.capability_id for ref in evidence] == [
        "csv_extraction", "case_normalization", "trim_extraction"
    ]
```

- [ ] **Step 2: Verify it fails**

Run: `PYTHONPATH=src:. python -m pytest tests/integration/capabilities/test_cleanup_transforms_chain.py::test_normalize_applies_configured_csv_cleanup_chain -q`

Expected: `supplier` is unresolved or unnormalized.

- [ ] **Step 3: Add fixture declaration and documentation**

```python
"format_hints": ["csv"],
"cleanup": [
    {"capability": "case_normalization", "config": {"mode": "lower"}},
    {"capability": "trim_extraction"},
],
```

Document `cleanup` and state that it is never inferred from a STRING field; it only runs after a selected format-aware extractor.

- [ ] **Step 4: Verify the integration suite passes**

Run: `PYTHONPATH=src:. python -m pytest tests/integration/capabilities/test_cleanup_transforms_chain.py -q`

Expected: PASS, including stable replay-hash coverage.

- [ ] **Step 5: Commit**

Run: `git add tests/fixtures/contracts/dict_dsl/with_cleanup_chain.py tests/integration/capabilities/test_cleanup_transforms_chain.py docs/specs/dict-dsl-spec.md docs/concepts/planning.md && git commit -m "test: cover configured cleanup normalization"`

### Task 5: Validate the sprint

**Files:**
- Verify only: changed Sprint 3 files

- [ ] **Step 1: Run focused tests**

Run: `PYTHONPATH=src:. python -m pytest tests/unit/contract tests/unit/test_planner_heuristics_planner.py tests/unit/executor tests/integration/capabilities/test_cleanup_transforms_chain.py -q`

Expected: PASS.

- [ ] **Step 2: Run static checks**

Run: `ruff check src/paxman tests && ruff format --check src/paxman tests && mypy --strict src/paxman`

Expected: PASS.

- [ ] **Step 3: Run coverage and thresholds**

Run: `pytest tests -q --cov=src/paxman --cov-branch --cov-report=term-missing && python scripts/check_subsystem_coverage.py`

Expected: all tests pass, total coverage is at least 90%, and every D7.15 subsystem threshold passes.

- [ ] **Step 4: Inspect final state**

Run: `git diff --check && git status --short && git log --oneline -5`

Expected: no whitespace errors and only intended Sprint 3 commits.

# Curated Contract Fixtures

This directory contains **hand-picked contracts** in every format Paxman supports. They are the **ground truth contracts** used in integration tests.

## What goes here

Each contract is **canonical**: it exercises a specific feature of the contract canonical model, a specific V1 field type, or a specific adapter behavior.

## File naming convention

- `invoice.py` (Pydantic) / `invoice.json` (JSON Schema) / `petstore_3_0.yaml` (OpenAPI)
- Snake_case; one contract per file; one file format per directory.
- Multi-word names use underscores (e.g., `multi_page.py`, `with_money.py`).

## V1 contracts (current)

The following fixtures are committed as of Sprint 2 (see [`docs/sprints/sprint-02-contract-subsystem.md`](../../docs/sprints/sprint-02-contract-subsystem.md) for the implementation plan and exit criteria):

| File | Format | What it exercises |
|---|---|---|
| `pydantic/invoice.py` ↔ `json_schema/invoice.json` ↔ `dict_dsl/invoice.py` | Pydantic / JSON Schema / Dict DSL | The canonical invoice use case (STRING, BOOLEAN, ARRAY, nested OBJECT) |
| `pydantic/with_money.py` ↔ `json_schema/with_money.json` ↔ `dict_dsl/with_money.py` | Pydantic / JSON Schema / Dict DSL | MONEY type coverage (the only MONEY fixture for V1) |
| `pydantic/all_v1_types.py` ↔ `json_schema/all_v1_types.json` ↔ `dict_dsl/all_v1_types.py` | Pydantic / JSON Schema / Dict DSL | Every V1 field type in one contract (STRING, INTEGER, DECIMAL, BOOLEAN, DATE, ENUM, OBJECT, ARRAY, MONEY) |

**Per-adapter fixture counts (as of Sprint 2):** 3 Pydantic, 3 JSON Schema, 3 Dict DSL — meeting the D2.10 "≥3 each" exit criterion.

## Planned (Sprint 3+)

The following fixtures are on the roadmap but not yet committed. Add them in
the appropriate sprint when the corresponding feature lands.

| File | Format | What it exercises | Sprint |
|---|---|---|---|
| `quotation.py` / `quotation.json` | Pydantic / JSON Schema | Quotation use case with MONEY | 7 |
| `procurement.py` / `procurement.json` | Pydantic / JSON Schema | Multi-currency procurement | 7 |
| `receipt.py` / `receipt.json` | Pydantic / JSON Schema | Receipts (smaller, simpler than invoices) | 7 |
| `multi_page.py` / `multi_page.json` | Pydantic / JSON Schema | Multi-page document contract | 7 |
| `deeply_nested.py` | Pydantic | OBJECT/ARRAY nesting | 7 |
| `empty_model.py` | Pydantic | Edge case: empty contract | 7 |
| `invalid_*.py` | Pydantic | Validator tests: invalid types, constraints | 7 |

## OpenAPI contracts (planned — Sprint 4)

| File | What it exercises |
|---|---|
| `petstore_3_0.yaml` | Canonical OpenAPI 3.0 |
| `petstore_3_1.yaml` | OpenAPI 3.1 (`$ref`, `oneOf`) |
| `procurement_api.yaml` | A more realistic OpenAPI example |

## Edge cases (planned — Sprint 7)

| File | What it exercises |
|---|---|
| `empty_model.py` | Empty contract |
| `deeply_nested.py` | 10+ levels of nesting |
| `with_money.py` | MONEY with multiple currencies |
| `all_v1_types.py` | One of every V1 type (already committed) |
| `invalid_*.py` | Validator tests |

## How to add a contract

1. Pick a name that describes the use case.
2. Place it in the right subdirectory (`pydantic/`, `json_schema/`, `dict_dsl/`, or `openapi/`).
3. Add a docstring describing what feature it exercises.
4. Reference it from the appropriate test file (e.g., `tests/unit/test_contract_dict_dsl.py`).
5. If it has a corresponding input, place that under `tests/fixtures/inputs/`.
6. If it has a corresponding expected artifact, place that under `tests/fixtures/artifacts/`.
7. **Paired fixtures must share their filename across formats.** When a contract has the same purpose in `pydantic/`, `json_schema/`, and `dict_dsl/` (a paired fixture), the filename (stem) must match exactly.

## See also

- [`tests/fixtures/contracts/AGENTS.md`](./AGENTS.md) — per-format conventions, anti-patterns.
- [`docs/TEST_DATA.md`](../../docs/TEST_DATA.md) — the full directory structure.
- [`docs/specs/dict-dsl-spec.md`](../../docs/specs/dict-dsl-spec.md) — the Dict DSL grammar (used by `dict_dsl/`).
- [`docs/sprints/sprint-02-contract-subsystem.md`](../../docs/sprints/sprint-02-contract-subsystem.md) — Sprint 2 (when these fixtures landed).
- [`TESTING_STRATEGY.md`](../../TESTING_STRATEGY.md) — how the fixtures are used in unit + property tests.

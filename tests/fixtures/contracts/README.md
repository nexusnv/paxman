# Curated Contract Fixtures

This directory contains **hand-picked contracts** in every format Paxman supports. They are the **ground truth contracts** used in integration tests.

## What goes here

Each contract is **canonical**: it exercises a specific feature of the contract canonical model, a specific V1 field type, or a specific adapter behavior.

## File naming convention

- `invoice.py` (Pydantic) / `invoice.json` (JSON Schema) / `petstore_3_0.yaml` (OpenAPI)
- Snake_case; one contract per file; one file format per directory.
- Multi-word names use underscores (e.g., `multi_page.py`, `with_money.py`).

## V1 contracts (planned)

| File | Format | What it exercises |
|---|---|---|
| `invoice.py` / `invoice.json` | Pydantic / JSON Schema | The canonical invoice use case |
| `quotation.py` / `quotation.json` | Pydantic / JSON Schema | Quotation use case with MONEY |
| `procurement.py` / `procurement.json` | Pydantic / JSON Schema | Multi-currency procurement |
| `receipt.py` / `receipt.json` | Pydantic / JSON Schema | Receipts (smaller, simpler than invoices) |
| `multi_page.py` / `multi_page.json` | Pydantic / JSON Schema | Multi-page document contract |
| `with_money.py` | Pydantic | MONEY type coverage |
| `all_v1_types.py` | Pydantic | Every V1 field type in one model |
| `deeply_nested.py` | Pydantic | OBJECT/ARRAY nesting |
| `empty_model.py` | Pydantic | Edge case: empty contract |
| `invalid_*.py` | Pydantic | Validator tests: invalid types, constraints |

## OpenAPI contracts (planned)

| File | What it exercises |
|---|---|
| `petstore_3_0.yaml` | Canonical OpenAPI 3.0 |
| `petstore_3_1.yaml` | OpenAPI 3.1 (`$ref`, `oneOf`) |
| `procurement_api.yaml` | A more realistic OpenAPI example |

## Edge cases (planned)

| File | What it exercises |
|---|---|
| `empty_model.py` | Empty contract |
| `deeply_nested.py` | 10+ levels of nesting |
| `with_money.py` | MONEY with multiple currencies |
| `all_v1_types.py` | One of every V1 type |
| `invalid_*.py` | Validator tests |

## How to add a contract

1. Pick a name that describes the use case.
2. Place it in the right subdirectory.
3. Add a docstring describing what feature it exercises.
4. Reference it from the appropriate test file.
5. If it has a corresponding input, place that under `tests/fixtures/inputs/`.
6. If it has a corresponding expected artifact, place that under `tests/fixtures/artifacts/`.

## See also

- [docs/TEST_DATA.md §3](../../docs/TEST_DATA.md) — the full directory structure
- [docs/TEST_DATA.md §8.2](../../docs/TEST_DATA.md) — the V1 curated fixtures plan
- [TESTING_STRATEGY.md §8 End-to-End Fixtures](../../TESTING_STRATEGY.md)

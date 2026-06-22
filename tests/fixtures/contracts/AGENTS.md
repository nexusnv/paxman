# tests/fixtures/contracts/

## OVERVIEW
Ground-truth contracts in every format Paxman supports (4 formats × ~10 contracts each). Layer 3 fixtures — hand-picked, committed, exercise every V1 field type and every V1 contract adapter behavior. These are the "ground truth" used in integration tests.

## STRUCTURE

```
contracts/
├── pydantic/                  # .py files (one model per file)
│   └── edge_cases/            # empty, deeply_nested, all_v1_types, with_money, invalid_*
├── json_schema/               # .json files
│   └── drafts/                # draft-04, -06, -07, -2019-09, -2020-12
├── dict_dsl/                  # internal escape hatch + test source of truth
│   └── edge_cases/
└── openapi/                   # EMPTY — optional, best-effort V1 adapter
    # planned: petstore_3_0.yaml, petstore_3_1.yaml, procurement_api.yaml
```

## WHERE TO LOOK

| Need | Directory |
|---|---|
| Canonical invoice use case | `pydantic/invoice.py` ↔ `json_schema/invoice.json` |
| MONEY type coverage | `pydantic/with_money.py` |
| Every V1 field type in one model | `pydantic/all_v1_types.py` |
| Deep OBJECT/ARRAY nesting | `pydantic/deeply_nested.py` |
| Edge case: empty contract | `pydantic/empty_model.py` |
| Validator error paths | `pydantic/invalid_*.py` |
| Adapter roundtrip across JSON Schema drafts | `json_schema/drafts/` |
| OpenAPI 3.0/3.1 coverage | `openapi/petstore_3_*.yaml` (planned) |
| Internal escape-hatch tests | `dict_dsl/` |

## CONVENTIONS

- **Snake_case filenames.** One contract per file. One format per directory.
- **Multi-word names use underscores:** `multi_page.py`, `with_money.py`.
- **A contract's filename matches across formats:** `pydantic/invoice.py` ↔ `json_schema/invoice.json` ↔ `dict_dsl/invoice.py` (paired fixtures).
- **Pydantic format uses `.py`; JSON Schema uses `.json`; OpenAPI uses `.yaml`.**
- **Each contract has a docstring describing what feature it exercises.**

## ANTI-PATTERNS

- **NEVER mix formats in one directory** — keep `pydantic/`, `json_schema/`, `dict_dsl/`, `openapi/` strictly separated.
- **NEVER add a contract that does not exercise a specific canonical-model feature, V1 field type, or adapter behavior.** Each fixture must have a reason.
- **NEVER use external/internal schema languages without an adapter** — only the 4 formats in V1 are accepted.
- **OpenAPI fixtures are optional/best-effort** — do not over-invest. A passing test suite is enough; full OpenAPI 3.1 coverage is not required (per ADR-0007).

## NOTES

- **As of `174d8dd`:** all subdirs are empty except the directory tree. No `.py`, `.json`, or `.yaml` contract fixtures exist yet — they will be created alongside the corresponding adapter implementation.
- **All 9 V1 field types must be covered:** `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`. The `all_v1_types.py` contract is the canonical coverage fixture.
- **MONEY coverage:** `with_money.py` exercises multi-currency, `CurrencyPolicy` (`STRICT_MATCH` / `ALLOW_FX` / `REJECT_WITHOUT_RATE`), and Decimal precision.
- **Per-adapter test rules** (see `tests/fixtures/README.md` + `TESTING_STRATEGY.md`):
  - **Unit tests** — adapter output for representative contracts.
  - **Golden tests** — frozen canonical snapshots.
  - **Property tests** — roundtrip: external format → canonical → external format (preserves structure within expressible subset).
  - **No I/O** in adapter tests (no network, no disk, no clock).

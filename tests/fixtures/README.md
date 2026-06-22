# Paxman Test Fixtures

> This directory contains **Layer 3 (curated)** and **Layer 4 (vendored)** test data for Paxman.

See **[docs/TEST_DATA.md](../../docs/TEST_DATA.md)** for the full test data policy, dataset catalog, and licensing rules.

## Directory structure

```text
fixtures/
├── README.md                          ← you are here
├── DATASET_LICENSES.md                ← attribution for every vendored file
│
├── contracts/                         ← curated contracts (Pydantic, JSON Schema, Dict DSL, OpenAPI)
│   ├── pydantic/
│   ├── json_schema/
│   ├── dict_dsl/
│   └── openapi/
│
├── inputs/                            ← raw inputs for normalization
│   ├── invoices/                      ← plain text, PDF, PNG
│   ├── receipts/
│   ├── quotations/
│   ├── procurement/
│   ├── multi_page/
│   └── adversarial/                   ← edge cases
│
├── artifacts/                         ← golden ExecutionArtifact JSON
│
└── generated/                         ← programmatic fixtures (gitignored)
```

## What goes where

- **`contracts/`** — hand-picked contracts in every supported format. These are the "ground truth" contracts used in integration tests. They exercise every V1 field type and every V1 contract adapter.

- **`inputs/`** — raw inputs in the formats Paxman accepts (text, PDF, PNG, CSV, JSON, HTML). Subdivided by use case. The `openapi/`, `cord/`, `alamgirqazi/`, etc. subdirectories hold vendored open-dataset samples.

- **`artifacts/`** — golden `ExecutionArtifact` JSON files used by replay-equality tests. See [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md).

- **`generated/`** — Layer 2 fixtures, generated at test time by `factory_boy` + `faker` + `hypothesis`. Gitignored. See [docs/TEST_DATA.md §7](../../docs/TEST_DATA.md).

## How to add a fixture

1. Pick the right directory based on whether it's a contract, an input, an adversarial edge case, or a golden artifact.
2. If it's a vendored open-dataset sample, see [docs/TEST_DATA.md §5 The Vendor Procedure](../../docs/TEST_DATA.md).
3. If it's a curated fixture, follow the format of existing fixtures.
4. Add the file.
5. Reference it from the appropriate test file.
6. Update `tests/fixtures/DATASET_LICENSES.md` if it's a vendored file.

## How to run the test suite

```bash
make test                    # all tests
make test-unit               # unit tests only
make test-integration        # integration tests (uses these fixtures)
make test-property           # property tests (uses programmatic fixtures)
```

See [DEVELOPMENT.md](../../DEVELOPMENT.md) for the full development workflow.

## License

The vendored data in this directory is licensed under its original terms. See [DATASET_LICENSES.md](./DATASET_LICENSES.md) for the full attribution catalog.

Paxman itself does not take copyright over vendored data; it merely provides a test bed for it. If you remove a vendored dataset from this directory, you remove Paxman's right to use it under the original license — but the dataset's license terms are independent of Paxman.

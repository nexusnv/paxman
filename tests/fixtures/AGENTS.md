# tests/fixtures/

## OVERVIEW
The Paxman test-data directory. Implements a **5-layer test data model** (see `docs/TEST_DATA.md`):

- **Layer 1:** Hand-written edge cases (committed) → `inputs/adversarial/`
- **Layer 2:** Programmatic (factory_boy + faker + hypothesis, **gitignored**) → `generated/`
- **Layer 3:** Curated golden fixtures (committed) → `contracts/`, `artifacts/`
- **Layer 4:** Vendored open-dataset samples (committed) → `inputs/*/` (invoices, receipts, etc.)
- **Layer 5:** Real production data (**NEVER committed**)

## STRUCTURE

```
tests/fixtures/
├── README.md, DATASET_LICENSES.md       # every vendored file must be attributed
├── contracts/                            # ground-truth contracts in 4 formats (Layer 3)
├── inputs/                               # raw inputs by use case (Layer 1 + Layer 4)
├── artifacts/                            # golden ExecutionArtifact JSON (Layer 3) — EMPTY
└── generated/                            # programmatic fixtures (Layer 2, gitignored)
```

## WHERE TO LOOK

| Need | Directory | Layer |
|---|---|---|
| Edge cases (empty, unicode, large, malformed) | `inputs/adversarial/` | L1 |
| Real invoice documents (PNG+JSON, MD+PDF+PNG+JSON) | `inputs/invoices/` | L4 (CORD, InvoiceBenchmark, alamgirqazi) |
| Real receipts | `inputs/receipts/` | L4 (wildreceipt) |
| Real quotations | `inputs/quotations/` | L4 (OQO) |
| Multi-page documents | `inputs/multi_page/` | L4 |
| Procurement data (CSV) | `inputs/procurement/` | L4 (Polish Tenders, TED) |
| Hand-written smoke inputs | `inputs/*/synthetic/` | L1 |
| Ground-truth contracts | `contracts/{pydantic,json_schema,dict_dsl,openapi}/` | L3 |
| Golden artifacts for replay-equality | `artifacts/` | L3 (none yet) |
| Programmatic fixtures | `generated/` | L2 (gitignored) |

## CONVENTIONS

- **Snake_case filenames.** One contract per file. One format per directory. (`tests/fixtures/contracts/README.md`)
- **Vendored files MUST be attributed in `DATASET_LICENSES.md`.** CI runs `python scripts/fetch_test_data.py --validate-licenses` and fails if any file is unattributed.
- **Allowed licenses for vendoring:** MIT, Apache-2.0, BSD, CC0, CC-BY-3.0, CC-BY-4.0. **No CC-BY-SA, no research-only, no CC-BY-NC.**
- **Goldens are written LAST.** They are bootstrapped from real implementations, never predicted.
- **Seeded reproducibility:** `factory.random.reseed_random(42)`, `hypothesis(derandomize=True)`, seed in `SEED.txt`.
- **Adversarial first:** edge-case fixtures exist before happy-path fixtures.
- **No real PII** in any committed fixture.

## ANTI-PATTERNS

- **NEVER add a vendored file without a `DATASET_LICENSES.md` entry.** CI fails.
- **NEVER commit real production data or PII.** Layer 5 is not committed.
- **NEVER vendor research-only datasets** (SROIE, INV-CDIP, FATURA). These are `--dev-only` and never exercised by CI.
- **NEVER commit generated fixtures** — `generated/` is gitignored. Outputs go there, not to `inputs/` or `artifacts/`.
- **NEVER predict golden artifacts.** Write them from a real run.
- **NEVER use an unattributed file in a test.** Verify with `make test-data-verify` first.

## NOTES

- **As of `174d8dd`:** `artifacts/` is empty (golden artifacts do not exist yet — no implementation to produce them). `inputs/adversarial/` has 4 of 10 planned edge cases. `inputs/{invoices,quotations}/synthetic/` has 5 small smoke inputs. All other subdirs are empty scaffolding.
- **Corpus growth roadmap:** 0 MB → 10 MB → 35 MB → 50 MB → 200 MB → 1 GB across V0.1 → V1.0 → V2 → V3.
- **Vendor procedure:** see `docs/TEST_DATA.md §5`.
- **Fetch command:** `python scripts/fetch_test_data.py` (currently stubbed — `vendor_one()` raises `NotImplementedError`).
- **10 vendorable datasets** in V1: CORD (CC-BY-4.0), InvoiceBenchmark (MIT), alamgirqazi (Apache-2.0), wildreceipt (Apache-2.0), OQO (CC-BY-4.0), petstore 3.0/3.1 (MIT), json-schema-test-suite (BSD-3-Clause), TED sample (Commission Decision 2011/833/EU), Polish Tenders (CC-BY-4.0).

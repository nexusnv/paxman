# tests/fixtures/inputs/

## OVERVIEW
Raw inputs to Paxman in every format it accepts (text, PDF, PNG, CSV, JSON, HTML, email body). Split by **use case** (invoices, receipts, quotations, procurement, multi_page) + an `adversarial/` directory for edge cases. Subdivided into `synthetic/` (hand-written, Layer 1) and vendor subdirs (Layer 4).

## STRUCTURE

```
inputs/
├── invoices/
│   ├── synthetic/             # 3 smoke inputs (Layer 1)
│   └── openapi/               # EMPTY (planned)
├── receipts/                  # EMPTY (planned: wildreceipt samples)
├── quotations/
│   ├── synthetic/             # 2 smoke inputs (Layer 1)
│   └── oqo/                   # EMPTY (planned: OQO samples)
├── procurement/               # EMPTY (planned: Polish Tenders, TED sample)
├── multi_page/                # EMPTY (planned)
├── adversarial/               # 4 edge cases (Layer 1)
└── README.md
```

## WHERE TO LOOK

| Need | Directory | Source |
|---|---|---|
| Smoke-test a plain-text invoice | `invoices/synthetic/invoice_plain.txt` | Layer 1 |
| Smoke-test an email-body invoice | `invoices/synthetic/invoice_email.txt` | Layer 1 |
| Smoke-test multi-currency CSV | `invoices/synthetic/invoice_csv.csv` | Layer 1 |
| Real receipt corpus (PNG+JSON) | `receipts/` | wildreceipt (Apache-2.0) |
| Real quotation corpus (JSON) | `quotations/oqo/` | OQO (CC-BY-4.0) |
| Procurement corpus (CSV) | `procurement/` | Polish Tenders (CC-BY-4.0) + TED sample |
| Multi-page PDF tests | `multi_page/` | TBD |
| Receipt-parsing + OCR noise | `invoices/cord/` (planned) | CORD (CC-BY-4.0) |
| MONEY / multi-currency / ground truth | `invoices/invoicebench/` (planned) | InvoiceBenchmark (MIT) |
| Broad field-label coverage | `invoices/alamgirqazi/` (planned) | alamgirqazi (Apache-2.0) |
| Empty input | `adversarial/empty_input.txt` | Layer 1 |
| Unicode-only input | `adversarial/unicode_only.txt` | Layer 1 |
| 10 MB input | `adversarial/extremely_large.txt` (planned) | Layer 1 |
| Truncated PDF | `adversarial/truncated_pdf.bin` (planned) | Layer 1 |
| Conflicting currencies | `adversarial/mismatched_currency.txt` | Layer 1 |
| Prompt-injection payload | `adversarial/prompt_injection.txt` | Layer 1 |

## CONVENTIONS

- **Subdivide by use case** (invoices, receipts, …) and source (synthetic, vendor).
- **Synthetic inputs live in `<use-case>/synthetic/`** with a fixed naming convention: `<use-case>_<scenario>.<ext>`.
- **Vendored inputs live in `<use-case>/<vendor-slug>/`** (e.g., `invoices/cord/`, `invoices/alamgirqazi/`).
- **Adversarial inputs live directly in `adversarial/`** (no synthetic subdir) — these are Layer 1 edge cases.
- **Filename describes the scenario**, not the contents (e.g., `mismatched_currency.txt`, not `usd_eur_conflict.txt`).
- **One source of truth for licenses: `tests/fixtures/DATASET_LICENSES.md`.** Every vendored file must have an entry. CI enforces this.

## ANTI-PATTERNS

- **NEVER vendor a file without adding it to `DATASET_LICENSES.md`.** CI rejects the PR.
- **NEVER commit real PII or production data** (no Layer 5).
- **NEVER vendor a file with a disallowed license** (no CC-BY-SA, no research-only, no CC-BY-NC). License gate in `scripts/fetch_test_data.py`.
- **NEVER put a vendored file directly under `adversarial/`** — adversarial is reserved for hand-written edge cases.
- **NEVER put a synthetic file under a vendor subdir** (no `invoices/cord/handmade.json`). Synthetics go in `*/synthetic/`.
- **Research-only datasets** (SROIE, INV-CDIP, FATURA) are **NOT** vendored. They require `--dev-only` for personal exploration; CI never touches them.

## NOTES

- **As of `174d8dd`:** 5 synthetic smoke inputs + 4 adversarial edge cases exist on disk. All vendor subdirs are empty. `make test-data-vendor` will populate them (~50 MB total across 10 vendored datasets).
- **Adversarial first** is the rule — 4 of 10 planned edge cases already exist before any happy-path corpus is vendored.
- **Per-dataset path and size targets** (see `tests/fixtures/inputs/README.md` "Vendored inputs" table):
  - CORD: 100 files, PNG+JSON, CC-BY-4.0
  - InvoiceBenchmark: 200 files, MD+PDF+PNG+JSON, MIT
  - alamgirqazi: 500 files (sampled), JSON+image, Apache-2.0
  - wildreceipt: 200 files, PNG+JSON, Apache-2.0
  - OQO: 72 files, JSON, CC-BY-4.0
  - TED sample: 100 files, JSON
  - Polish Tenders: 1000 files, CSV, CC-BY-4.0
- **Pair with contracts:** every input in `inputs/` should have a matching contract in `tests/fixtures/contracts/` and (eventually) a golden artifact in `tests/fixtures/artifacts/`.

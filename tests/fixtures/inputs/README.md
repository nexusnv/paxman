# Vendored and Synthetic Inputs

This directory contains **raw inputs** in every format Paxman accepts (text, PDF, PNG, CSV, JSON, HTML).

## Subdirectories

| Subdirectory | What it contains |
|---|---|
| `invoices/` | Invoice documents (text, PDF, PNG) |
| `receipts/` | Receipt documents (smaller, simpler) |
| `quotations/` | Quotation documents |
| `procurement/` | Procurement data (CSV, JSON) |
| `multi_page/` | Multi-page documents (PDF) |
| `adversarial/` | Edge cases (empty, unicode, large, malformed) |

Each subdirectory has a similar structure:

```text
invoices/
├── synthetic/            # small hand-written or generated inputs for smoke tests
│   ├── invoice_plain.txt
│   ├── invoice_email.txt
│   └── invoice_csv.csv
├── cord/                 # vendored CORD samples (CC-BY-4.0)
├── invoicebench/         # vendored InvoiceBenchmark (MIT)
├── alamgirqazi/          # vendored (Apache-2.0)
└── README.md
```

## Vendored inputs (V1)

See [tests/fixtures/DATASET_LICENSES.md](../../DATASET_LICENSES.md) for the full attribution catalog.

| Source | Files | Format | License |
|---|---|---|---|
| CORD | 100 | PNG + JSON | CC-BY-4.0 |
| InvoiceBenchmark | 200 | MD + PDF + PNG + JSON | MIT |
| alamgirqazi | 500 | JSON + image | Apache-2.0 |
| wildreceipt | 200 | PNG + JSON | Apache-2.0 |
| OQO | 72 | JSON | CC-BY-4.0 |
| TED sample | 100 | JSON | Commission Decision 2011/833/EU |
| Polish Tenders | 1000 | CSV | CC-BY-4.0 |

## Synthetic inputs (V1)

These are hand-written or generated inputs that exercise specific features. They live in `*/synthetic/` subdirectories.

| File | What it exercises |
|---|---|
| `invoice_plain.txt` | Plain-text invoice |
| `invoice_email.txt` | Invoice embedded in an email body |
| `invoice_csv.csv` | CSV with multi-currency lines |
| `quotation_simple.txt` | Simple quotation |
| `quotation_with_footnotes.txt` | Quotation with footnotes |
| `empty_input.txt` | Adversarial: empty input |
| `unicode_only.txt` | Adversarial: Unicode-only input |
| `extremely_large.txt` | Adversarial: 10 MB input |
| `truncated_pdf.bin` | Adversarial: truncated PDF |
| `mismatched_currency.txt` | Adversarial: conflicting currencies |
| `prompt_injection.txt` | Adversarial: prompt-injection payload |

## How to add an input

1. Pick the right subdirectory based on document type and source.
2. If it's a vendored file, follow the [vendor procedure](../../../../docs/TEST_DATA.md#5-the-vendor-procedure).
3. If it's a synthetic file, follow the naming convention and add it to the synthetic/ subdirectory.
4. Add it to [DATASET_LICENSES.md](../../DATASET_LICENSES.md) if it's vendored.
5. Reference it from the appropriate test file.

## See also

- [docs/TEST_DATA.md](../../../../docs/TEST_DATA.md) — test data policy
- [tests/fixtures/DATASET_LICENSES.md](../../DATASET_LICENSES.md) — attribution
- [tests/fixtures/contracts/README.md](../../contracts/README.md) — the contracts that pair with these inputs

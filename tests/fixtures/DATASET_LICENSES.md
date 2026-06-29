# Test Data Licenses & Attribution

> This file is the **single source of truth** for the license and attribution of every vendored dataset in `tests/fixtures/`.
> See **[docs/TEST_DATA.md §4 Licensing Policy](../../docs/TEST_DATA.md)** for the policy that governs this catalog.

## How to use this file

Every vendored dataset must have an entry in this file. The CI pipeline runs `python scripts/fetch_test_data.py --validate-licenses` to verify that:

1. Every file under `tests/fixtures/` is attributed here.
2. Every entry here corresponds to an existing file.
3. The license is in the allowed list (MIT, Apache-2.0, BSD, CC0, CC-BY-3.0, CC-BY-4.0).

If a file is found in `tests/fixtures/` that is **not** in this catalog, the CI check fails.

---

## Vendored Datasets (V1)

### CORD (Consolidated Receipt Dataset)

- **Source:** https://github.com/clovaai/cord
- **HuggingFace mirror:** https://huggingface.co/datasets/naver-clova-ix/cord-v1
- **Version:** v1
- **License:** CC-BY-4.0
- **Citation:** Park, S., Shin, S., Lee, B., Lee, J., Surh, J., Seo, M., & Lee, H. (2019). *CORD: A Consolidated Receipt Dataset for Post-OCR Parsing.* Document Intelligence Workshop at NeurIPS 2019.
- **Files vendored:** 100 (test split, sampled)
- **Path:** `tests/fixtures/inputs/invoices/cord/`
- **Vendored on:** _TBD_
- **V1 use:** Receipt-parsing end-to-end tests, OCR noise tests.

### jngb-labs/InvoiceBenchmark

- **Source:** https://huggingface.co/datasets/jngb-labs/InvoiceBenchmark
- **Version:** latest
- **License:** MIT
- **Files vendored:** 200 (full)
- **Path:** `tests/fixtures/inputs/invoices/invoicebench/`
- **Vendored on:** _TBD_
- **V1 use:** MONEY tests, multi-currency tests, deterministic ground truth.

### alamgirqazi/invoice-ocr-synthetic

- **Source:** https://huggingface.co/datasets/alamgirqazi/invoice-ocr-synthetic
- **Version:** latest
- **License:** Apache-2.0
- **Files vendored:** 500 (sampled)
- **Path:** `tests/fixtures/inputs/invoices/alamgirqazi/`
- **Vendored on:** _TBD_
- **V1 use:** Broad coverage of field labels, line items, multiple currencies.

### kaydee/wildreceipt

- **Source:** https://huggingface.co/datasets/kaydee/wildreceipt
- **Version:** latest
- **License:** Apache-2.0
- **Files vendored:** 200 (sampled)
- **Path:** `tests/fixtures/inputs/receipts/wildreceipt/`
- **Vendored on:** _TBD_
- **V1 use:** "In-the-wild" receipt tests, harder-than-CORD layout tests.

### OQO (Open-Quote Object)

- **Source:** https://github.com/APH123614/oqo
- **Version:** latest
- **License (code):** MIT
- **License (data):** CC-BY-4.0
- **Files vendored:** 72 (full sample)
- **Path:** `tests/fixtures/inputs/quotations/oqo/`
- **Vendored on:** _TBD_
- **V1 use:** Quotation use case, Open-Quote-Object JSON Schema validation.

### OpenAPI Petstore (v3.0)

- **Source:** https://github.com/OAI/OpenAPI-Specification/blob/main/examples/v3.0/petstore.yaml
- **Version:** 3.0.0
- **License:** MIT
- **Files vendored:** 1 (single YAML)
- **Path:** `tests/fixtures/contracts/openapi/petstore_3_0.yaml`
- **Vendored on:** _TBD_
- **V1 use:** OpenAPI adapter smoke test.

### OpenAPI Petstore (v3.1)

- **Source:** https://github.com/OAI/OpenAPI-Specification/blob/main/examples/v3.1/petstore.yaml (hand-rolled subset, 2026-06-29)
- **Version:** OAS 3.1.0
- **License:** MIT
- **Files vendored:** 1 (single YAML)
- **Path:** `tests/fixtures/contracts/openapi/petstore_3_1.yaml`
- **Vendored on:** 2026-06-29
- **V1 use:** OpenAPI 3.1 adapter smoke test, exercises `jsonSchemaDialect`, `$defs`, `type: [string, null]`, `webhooks`, and path-item `parameters` (the last two are accepted and ignored per V1.1.0 non-goal N3).

### JSON-Schema-Test-Suite

- **Source:** https://github.com/json-schema-org/JSON-Schema-Test-Suite
- **Version:** latest
- **License:** BSD-3-Clause + Apache-2.0 (per file; mixed)
- **Files vendored:** 2020-12 subset
- **Path:** `tests/fixtures/contracts/json_schema/drafts/`
- **Vendored on:** _TBD_
- **V1 use:** JSON Schema adapter validation, every draft.

### TED (Tenders Electronic Daily) — sample

- **Source:** https://ted.europa.eu/
- **HuggingFace mirror (sample):** https://huggingface.co/datasets/OpenMLDatasets/ted_2025_07_sample
- **Version:** July 2025 sample
- **License:** Commission Decision 2011/833/EU (TED); CC0 (sample enrichment)
- **Files vendored:** 100 (full sample)
- **Path:** `tests/fixtures/inputs/procurement/ted_sample/`
- **Vendored on:** _TBD_
- **V1 use:** Procurement use case, structured procurement metadata.

### atlasprzetargow/polish-tenders-dataset

- **Source:** https://github.com/atlasprzetargow/polish-tenders-dataset
- **Version:** latest
- **License (data):** CC-BY-4.0
- **License (code):** MIT
- **Files vendored:** 1000 (sampled)
- **Path:** `tests/fixtures/inputs/procurement/polish_tenders/`
- **Vendored on:** _TBD_
- **V1 use:** Multi-currency procurement tests, EU procurement structure.

---

## Research-Only Datasets (NOT vendored)

These datasets are referenced in the test suite but **not vendored** in the repo. They have research-only or non-commercial licenses that prevent redistribution. Developers may download them individually for local development using `python scripts/fetch_test_data.py --dataset <name>`, but CI does not use them.

### ICDAR 2019 SROIE

- **Source:** https://rrc.cvc.uab.es/?ch=13
- **License:** Research-only (per ICDAR-2019 terms)
- **V1 use:** Real scanned-receipt OCR noise tests. **Dev only.**

### salesforce/inv-cdip

- **Source:** https://github.com/salesforce/inv-cdip
- **License:** CC-BY-NC-4.0 (non-commercial)
- **V1 use:** Real-invoice tests. **Dev only; not vendored.**

### mathieu1256/FATURA

- **Source:** https://zenodo.org/record/8261508
- **License:** CC-BY-NC-4.0 (non-commercial)
- **V1 use:** Multi-layout invoice tests. **V2 only.**

### Urwashanza/europrocure-10-public-procurement

- **Source:** https://huggingface.co/datasets/Urwashanza/europrocure-10-public-procurement
- **License:** (Research)
- **V1 use:** Procurement-scale tests. **V2 only.**

### GTI Global Public Procurement Dataset (GPPD)

- **Source:** https://data.mendeley.com/datasets/w9mzf4vswh/3
- **License:** CC BY-NC 3.0 (non-commercial)
- **V1 use:** Procurement tests. **V2 only.**

---

## Datasets Considered and Rejected

| Dataset | License | Why rejected |
|---|---|---|
| Salesforce CUAD | CC-BY-4.0 | Multi-page, low priority for V1; revisit V2. |
| MP-DocVQA | MIT | V2 candidate. |
| lmms-lab/MP-DocVQA | MIT | V2 candidate. |
| MIDD (Baviskar et al.) | (Paper dataset, no clear license) | License unclear; skipped. |
| Voxel51/high-quality-invoice-images-for-ocr | Research | Not redistributable. V2 only if license changes. |
| Kaggle commercial datasets | Commercial | Not vendored. |
| Perplexity, OpenAI internal eval sets | Private | Not vendored. |

---

## Curated Fixtures (project-created, not vendored)

These files are hand-written or generated by the Paxman project as part of the test suite. 
They are **not** vendored from external datasets. They are created by Paxman contributors and
licensed under the same terms as the Paxman project itself.

### Adversarial Inputs

- **Path:** `tests/fixtures/inputs/adversarial/`
- **License:** MIT (Paxman project license)
- **Files:** 6 curated edge-case inputs: `empty_input.txt`, `extremely_large.txt`, `mismatched_currency.txt`, `prompt_injection.txt`, `truncated_pdf.bin`, `unicode_only.txt`
- **Purpose:** Layer 1 hand-written edge cases for Reconciler and Executor tests.

### Synthetic Inputs

- **Path:** `tests/fixtures/inputs/*/synthetic/`
- **License:** MIT (Paxman project license)
- **Files:**
  - `invoices/synthetic/` — `invoice_plain.txt`, `invoice_csv.csv`, `invoice_email.txt`
  - `receipts/synthetic/` — `receipt_plain.txt`, `receipt_thermal.txt`, `receipt_email.txt`
  - `quotations/synthetic/` — `quotation_simple.txt`, `quotation_multi_currency.txt`, `quotation_with_footnotes.txt`
- **Purpose:** Layer 1 hand-written smoke inputs for happy-path integration tests.

### Curated Contract Fixtures

- **Path:** `tests/fixtures/contracts/{pydantic,json_schema,dict_dsl}/`
- **License:** MIT (Paxman project license)
- **Files:**
  - `contracts/pydantic/` — `invoice.py`, `all_v1_types.py`, `with_money.py`
  - `contracts/json_schema/` — `invoice.json`, `all_v1_types.json`, `with_money.json`
  - `contracts/dict_dsl/` — `invoice.py`, `all_v1_types.py`, `with_money.py`
- **Purpose:** Layer 3 ground-truth contracts used by Contract adapter integration tests.

---

When adding a new vendored dataset, use this template:

```markdown
### <Dataset Name>

- **Source:** <URL>
- **HuggingFace mirror (if any):** <URL>
- **Version:** <version>
- **License:** <license>
- **Citation:** <paper or DOI, if any>
- **Files vendored:** <count>
- **Path:** `tests/fixtures/...`
- **Vendored on:** <YYYY-MM-DD>
- **V1 use:** <purpose>
- **Notes:** <any other relevant info, e.g., desensitization, PII handling>
```

---

## License-summary table

| Dataset | License | Files | Path |
|---|---|---|---|
| CORD | CC-BY-4.0 | 100 | `inputs/invoices/cord/` |
| InvoiceBenchmark | MIT | 200 | `inputs/invoices/invoicebench/` |
| alamgirqazi | Apache-2.0 | 500 | `inputs/invoices/alamgirqazi/` |
| wildreceipt | Apache-2.0 | 200 | `inputs/receipts/wildreceipt/` |
| OQO | MIT + CC-BY-4.0 | 72 | `inputs/quotations/oqo/` |
| OpenAPI Petstore 3.0 | MIT | 1 | `contracts/openapi/petstore_3_0.yaml` |
| OpenAPI Petstore 3.1 | MIT | 1 | `contracts/openapi/petstore_3_1.yaml` |
| JSON-Schema-Test-Suite | BSD-3 / Apache-2.0 | 2020-12 subset | `contracts/json_schema/drafts/` |
| TED sample | Commission Decision 2011/833/EU | 100 | `inputs/procurement/ted_sample/` |
| Polish Tenders | CC-BY-4.0 | 1000 | `inputs/procurement/polish_tenders/` |
| Adversarial Inputs | MIT (project) | 6 | `inputs/adversarial/` |
| Synthetic Inputs | MIT (project) | 9 | `inputs/*/synthetic/` |
| Curated Contract Fixtures | MIT (project) | 9 | `contracts/*/` |
| **Total** | (all allowed) | **~2,224 files** | (~50 MB) |

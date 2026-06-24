# OQO – Open-Quote Object

OQO ("Open-Quote Object") is a lightweight, open specification for representing quotes and proposals as structured JSON. The goal is to make it easy for contractors, suppliers and clients to exchange quote information in a consistent format without locking themselves into a particular vendor or proprietary system. By publishing the schema and providing sample data and validation tools, we hope to encourage interoperability and adoption across construction, procurement and service industries.

This repository contains the core JSON Schema, a realistic sample quote, validation tooling and an anonymised dataset. There is no application code here — just the specification and supporting artefacts. Feel free to fork the project, file issues or propose changes via pull request.

## Specification

The current version of the OQO schema (v2.0.0) lives in the [`open-schema/`](open-schema/) folder. It uses the **JSON Schema 2020-12** dialect. A hosted copy is available at:

```
https://tibr.ai/open-schema/oqo.json
```

### Top-level structure

| Field | Type | Description |
|---|---|---|
| `oqoVersion` | string | Schema version (currently `"2.0.0"`) |
| `quoteId` | string | Unique quote identifier |
| `quoteReference` | string | Human-readable reference code |
| `quoteVersion` | integer | Revision number |
| `name` | string | Short title for the quote |
| `status` | enum | `draft`, `sent`, `accepted`, `declined`, `archived` |
| `issuer` | object | Company or individual issuing the quote |
| `client` | object | Recipient — includes company info, contact, address, CRM fields |
| `siteAddress` | object | Physical location where work takes place |
| `project` | object | Project metadata — type, area, dates, lead time, drawing ref |
| `people` | object | Key personnel — sales, estimator, designer, project manager |
| `items` | array | **Hierarchical** line items (see below) |
| `currency` | string | ISO 4217 code (e.g. `GBP`, `USD`, `EUR`) |
| `totals` | object | `totalSell` and optional `totalBuy` |
| `discount` | object | Quote-level discount (percentage or fixed) |
| `dates` | object | `issueDate` and `validUntil` |
| `paymentTerms` | string | Payment terms text |
| `notes` | string | Free-text notes or T&Cs |
| `customText` | string | Optional custom text block for printed output |
| `metadata` | object | Arbitrary key-value pairs for system-specific extensions |

### Hierarchical items

Unlike flat line-item lists, OQO items form a **tree**. Each item has an `id` and an optional `parentId` that references another item. This allows quotes to be structured into sections, groups and sub-assemblies:

```
Section: Partitions & Drylining        (isGroup: true,  parentId: null)
  ├─ Metal stud partitions             (isGroup: false, parentId: "sec-2")
  │    ├─ 75mm C-stud framing          (parentId: "item-201")
  │    ├─ Plasterboard                 (parentId: "item-201")
  │    ├─ Acoustic insulation          (parentId: "item-201")
  │    └─ Labour                       (parentId: "item-201")
  └─ Glazed partition system           (isGroup: false, parentId: "sec-2")
```

Each line item carries:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique within this quote |
| `parentId` | string/null | Parent item ID (null = top level) |
| `text` | string | Description |
| `quantity` | number | Quantity |
| `unit` | string | Unit of measure (`each`, `m2`, `hours`, `lm`, `kg`, `weeks`, `lot`, etc.) |
| `buy` | number | Unit cost (internal) |
| `sell` | number | Unit selling price |
| `gpPercent` | number | Gross profit % |
| `totalBuy` | number | Extended cost (buy × qty) |
| `totalSell` | number | Extended sell (sell × qty) |
| `partNo` | string | SKU or product code |
| `status` | enum | `include`, `exclude`, `optional` |
| `isGroup` | boolean | Section header / grouping row |
| `comment` | string | Internal note |
| `dontPrintChildren` | boolean | Hide children on printed output |
| `metadata` | object | Arbitrary extra data |

### Reusable definitions

The schema defines reusable `$defs` for **party**, **contact** and **address** objects. Addresses use structured fields (`addressLine1`, `addressLine2`, `city`, `stateProvince`, `postalCode`, `country`) rather than a single string, making them machine-parseable.

## Example

The [`sample_quote.json`](sample_quote.json) file contains a realistic commercial fitout quote with:

- Full issuer and client details including contacts and addresses
- A site address separate from the client address
- Project metadata (type, area, dates, drawing reference)
- Named personnel (sales, estimator, designer, PM)
- 24 hierarchical line items across 6 sections including:
  - Grouped items with hidden children (partitions with material + labour breakdown)
  - An optional section not included in the total
  - Buy/sell/GP pricing throughout
- A percentage discount
- Payment terms and notes

```json
{
  "oqoVersion": "2.0.0",
  "quoteId": "Q-2025-0042",
  "name": "Riverside Office Fitout – Level 3",
  "status": "sent",
  "issuer": { "name": "Apex Interiors Ltd.", ... },
  "client": {
    "companyName": "Riverside Developments PLC",
    "contact": { "firstName": "James", "lastName": "Thornton", ... },
    "address": { "city": "London", ... }
  },
  "items": [
    { "id": "sec-1", "text": "Demolition & Strip-out", "isGroup": true, ... },
    { "id": "item-101", "parentId": "sec-1", "text": "Strip existing floor coverings",
      "quantity": 620, "unit": "m2", "buy": 4.50, "sell": 6.75, ... },
    ...
  ],
  "currency": "GBP",
  "totals": { "totalSell": 95771.00, "totalBuy": 66960.00 }
}
```

## Getting Started

1. **Clone** this repository.

2. **Validate** the sample quote against the schema:

   **Python** (requires `jsonschema`):
   ```bash
   pip install jsonschema
   python tools/validate_quote.py sample_quote.json open-schema/oqo.json
   ```

   **JavaScript** (browser — uses Ajv via CDN):
   See `tools/validate_quote.js` for an embeddable validator function.

3. **Explore** the dataset:
   Open `notebooks/sample_quotes_demo.ipynb` to load and preview the 72-row anonymised dataset.

## Tools

| File | Description |
|---|---|
| `tools/validate_quote.py` | Python CLI validator — checks a JSON file against the schema |
| `tools/validate_quote.js` | Browser-friendly JavaScript validator using Ajv 8 |
| `datasets/sample_quotes.csv` | 72 anonymised sample quotes with realistic fields |
| `notebooks/sample_quotes_demo.ipynb` | Jupyter notebook to load and explore the CSV |

## Datasets

- [Standardized Quote Dataset – JSON Schema (TIBR)](https://www.kaggle.com/datasets/drandrewharris/standardized-quote-dataset-json-schema-tibr)

## Contributing

We welcome contributions. Please open an issue to discuss enhancements or questions. When submitting a pull request, follow the existing conventions and include tests if you add new functionality.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## About TIBR

OQO is part of the **TIBR growth campaign**, an initiative to modernise estimating and quoting workflows in the construction and services industries. To learn more about TIBR's AI-powered estimating software, visit [tibr.ai](https://tibr.ai).

For questions or commercial enquiries, contact Team OQO at support@tibr.tech.

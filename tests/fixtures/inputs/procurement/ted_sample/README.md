---
language:
- en
tags:
- dataset
- procurement
- europe
- tenders
- machine-learning
- nlp
- financial-data
- public-sector
license: other
pretty_name: EU Public Procurement — July 2025
size_categories:
- 100K<n<1M
dataset_preview: ted_2025_07_sample.csv
---

# EU Public Procurement — July 2025 (Enriched CSV)

This dataset contains **all public procurement notices from July 2025**,  
parsed and enriched from the European Union's [TED (Tenders Electronic Daily)](https://ted.europa.eu/).

The **full dataset (200,000+ rows)** is available for purchase here: [Full Dataset on Gumroad](https://openmldatasets.gumroad.com/l/rexjp)

## Free Sample vs Full Dataset

| Feature            | Free Sample (this repo) | Full Dataset (Gumroad) |
|--------------------|--------------------------|--------------------------|
| Rows               | 100                      | 260,000+                 |
| File size          | ~50 KB                   | ~150 MB+                 |
| Format             | CSV (UTF-8)              | CSV (UTF-8)              |
| Columns            | 14 (see below)           | 14 (same schema)         |

## Contents
- Procurement notices parsed from official TED XML
- Normalized, analysis-ready columns:
  - `notice_id` — unique identifier of the notice
  - `publication_date` — publication date (ISO 8601, may include timezone offset)
  - `buyer_id` — anonymized buyer/organization ID
  - `cpv_code` — Common Procurement Vocabulary (CPV 2008, 8-digit)
  - `lot_id` — identifier for the procurement lot
  - `lot_name` — contract title (local language)
  - `lot_description` — contract description (local language)
  - `award_value` — contract award value (when available, numeric)
  - `final_value` — overall contract value at notice/result level (if present)
  - `best_value` — most reliable value selected among award, final, and estimated
  - `best_value_source` — which field the `best_value` came from
  - `currency` — contract currency
  - `source_file` — original TED XML file
  - `cpv_label` — CPV 2008 English description

## Added Value
While the raw TED data is free and open, this dataset provides:
- Parsed and normalized structure (from thousands of XML files → single CSV)
- Automatic CPV 2008 code enrichment with human-readable labels
- Multiple contract value fields (`award`, `final`, `best`) for flexible analysis
- Ready for machine learning pipelines and analytics without preprocessing

## Source & License
- Contains information from the EU’s TED portal.  
  © European Union. Reuse governed by **Commission Decision 2011/833/EU**.  
  No endorsement by the European Union is implied.  
- Enrichment (parsing, CPV mapping, packaging) © 2025 OpenML Datasets,  
  released under **Creative Commons Zero v1.0 Universal (CC0)**.

## Suggested Uses
- **Machine learning**: NER, classification, contract value forecasting
- **Market intelligence**: sector and supplier mapping
- **Procurement research**: transparency, competition, and cross-country studies
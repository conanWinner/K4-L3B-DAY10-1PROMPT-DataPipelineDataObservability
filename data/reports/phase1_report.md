# Phase 1 Report - Baseline Pipeline

_Generated at 2026-09-26T04:56:11.536809+00:00_

## 1. Source

- Source api: Crossref REST API
- Query: agentic retrieval augmented generation large language model
- Filter: from-pub-date:2026-03-30,has-abstract:true
- Raw records: 24
- Clean rows: 24
- Run date: 2026-09-26
- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- Collection: papers-baseline

## 2. Baseline Evaluation

| Metric | Value |
|---|---:|
| Samples | 10 |
| Retrieval Hit Rate | 1.0000 |
| Mean Token F1 | 1.0000 |
| Judge Accuracy | 1.0000 |
| Mean Judge Score (1-5) | 5 |

## 3. Data Quality Gate (Great Expectations 1.x)

- Rows checked: 24
- GX suite result: **PASS**
- Overall gate (GX + freshness): **PASS**

| Expectation | Column | Result | Unexpected |
|---|---|---|---|
| `expect_table_row_count_to_be_between` | (table) | PASS | observed=24 |
| `expect_column_values_to_not_be_null` | paper_id | PASS | 0 |
| `expect_column_values_to_be_unique` | paper_id | PASS | 0 |
| `expect_column_values_to_not_be_null` | title | PASS | 0 |
| `expect_column_value_lengths_to_be_between` | title | PASS | 0 |
| `expect_column_value_lengths_to_be_between` | summary | PASS | 0 |

## 4. Freshness SLA

- Latest published: 2026-07-22
- Oldest published: 2026-03-28
- Stale rows (age_days > 180): 1/24 (4.2%)
- SLA: at most 25% stale rows -> **PASS**

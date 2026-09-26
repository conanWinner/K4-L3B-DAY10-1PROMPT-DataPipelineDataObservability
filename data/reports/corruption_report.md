# Corruption Report - Baseline vs Corrupted vs Repaired

_Generated at 2026-09-26T13:39:17.822914+00:00_

## 1. RAG Metrics

| Metric | Baseline | Corrupted | Repaired | Corrupted vs Baseline | Repaired vs Baseline |
|---|---:|---:|---:|---:|---:|
| Retrieval Hit Rate | 1.0000 | 0.8000 | 1.0000 | -0.2000 | +0.0000 |
| Mean Token F1 | 1.0000 | 0.8000 | 1.0000 | -0.2000 | +0.0000 |
| Judge Accuracy | 1.0000 | 0.8000 | 1.0000 | -0.2000 | +0.0000 |
| Mean Judge Score (1-5) | 5 | 4.2000 | 5 | -0.8000 | +0.0000 |

## 2. Data Quality Gate

| State | Rows | GX suite | Freshness | Overall gate |
|---|---:|---|---|---|
| Corrupted | 23 | FAIL | FAIL | FAIL |
| Repaired | 24 | PASS | PASS | PASS |

### Corrupted batch expectations

| Expectation | Column | Result | Unexpected |
|---|---|---|---|
| `expect_table_row_count_to_be_between` | (table) | PASS | observed=23 |
| `expect_column_values_to_not_be_null` | paper_id | PASS | 0 |
| `expect_column_values_to_be_unique` | paper_id | FAIL | 4 |
| `expect_column_values_to_not_be_null` | title | PASS | 0 |
| `expect_column_value_lengths_to_be_between` | title | FAIL | 6 |
| `expect_column_value_lengths_to_be_between` | summary | FAIL | 4 |

### Repaired batch expectations

| Expectation | Column | Result | Unexpected |
|---|---|---|---|
| `expect_table_row_count_to_be_between` | (table) | PASS | observed=24 |
| `expect_column_values_to_not_be_null` | paper_id | PASS | 0 |
| `expect_column_values_to_be_unique` | paper_id | PASS | 0 |
| `expect_column_values_to_not_be_null` | title | PASS | 0 |
| `expect_column_value_lengths_to_be_between` | title | PASS | 0 |
| `expect_column_value_lengths_to_be_between` | summary | PASS | 0 |

## 3. Freshness SLA

**Corrupted**

- Latest published: 2026-06-25
- Oldest published: 2023-06-03
- Stale rows (age_days > 180): 9/23 (39.1%)
- SLA: at most 25% stale rows -> **FAIL**

**Repaired**

- Latest published: 2026-07-22
- Oldest published: 2026-03-28
- Stale rows (age_days > 180): 1/24 (4.2%)
- SLA: at most 25% stale rows -> **PASS**

## 4. Analysis

- **Retrieval Hit Rate** went from 1.0000 to 0.8000 on corrupted data, then fully recovered after repair.
- **Mean Token F1** went from 1.0000 to 0.8000 on corrupted data, then fully recovered after repair.
- **Judge Accuracy** went from 1.0000 to 0.8000 on corrupted data, then fully recovered after repair.
- **Mean Judge Score (1-5)** went from 5.0000 to 4.2000 on corrupted data, then fully recovered after repair.
- The quality gate caught the corruption: 3 expectations failed (`expect_column_values_to_be_unique`(paper_id), `expect_column_value_lengths_to_be_between`(title), `expect_column_value_lengths_to_be_between`(summary)).
- The freshness SLA also failed on the corrupted batch because of the backdated publication dates.
- After repairing from the raw snapshot the gate is **PASS**, so the repaired collection is safe to serve again.

# Phase 1 Report: Baseline Pipeline

Generated at: 2026-09-25T08:01:51.364878+00:00

## Source & Pipeline

| Item | Value |
|---|---|
| source_api | Crossref REST API |
| query | agentic retrieval augmented generation large language model |
| filter | from-pub-date:2026-03-29,has-abstract:true |
| raw_records | 24 |
| clean_rows | 24 |
| collection_name | papers-baseline |
| embedding_model | sentence-transformers/all-MiniLM-L6-v2 |
| llm | openai/gpt-4o-mini |
| test_set_size | 10 |

## Evaluation Metrics

| Metric | Value |
|---|---|
| Samples | 10 |
| Retrieval hit rate | 100.0% |
| Mean token F1 | 0.933 |
| LLM judge accuracy | 80.0% |
| Mean LLM judge score (1-5) | 4.60 |

Ragas: Set RUN_RAGAS=1 to enable the slower Ragas pass.

### Breakdown by question type

| Type | Samples | Hit rate | Token F1 | Judge accuracy |
|---|---|---|---|---|
| summary | 2 | 100.0% | 1.000 | 100.0% |
| authors | 2 | 100.0% | 1.000 | 100.0% |
| date | 2 | 100.0% | 1.000 | 100.0% |
| category | 2 | 100.0% | 1.000 | 100.0% |
| multi_hop | 2 | 100.0% | 0.667 | 0.0% |

### Per-question results

| ID | Type | Hit | Token F1 | Judge | Answer |
|---|---|---|---|---|---|
| q01 | summary | yes | 1.00 | 5 | Static benchmarks fail to capture domain drift in enterprise knowledge bases. |
| q02 | summary | yes | 1.00 | 5 | A single LLM is susceptible to confirmation bias when evaluating retrieved evide |
| q03 | authors | yes | 1.00 | 5 | Bao Do, Linh Ngo |
| q04 | authors | yes | 1.00 | 5 | Kien Duong, Vy Ly |
| q05 | date | yes | 1.00 | 5 | 2026-06-12 |
| q06 | date | yes | 1.00 | 5 | 2026-06-08 |
| q07 | category | yes | 1.00 | 5 | Artificial Intelligence, Information Retrieval |
| q08 | category | yes | 1.00 | 5 | Information Retrieval, Algorithms |
| q09 | multi_hop | yes | 0.67 | 3 | Huy Dinh, Trang Vo |
| q10 | multi_hop | yes | 0.67 | 3 | Duc Vu, Thao Dang |

## Data Quality Gate (Great Expectations)

- Engine: `great_expectations 1.18.0`
- Overall: **PASS** (6/6 expectations passed)

| Expectation | Column | Result | Observed | Unexpected |
|---|---|---|---|---|
| expect_table_row_count_to_be_between | - | PASS | 24 | - |
| expect_column_values_to_not_be_null | paper_id | PASS | - | 0 |
| expect_column_values_to_be_unique | paper_id | PASS | - | 0 |
| expect_column_values_to_not_be_null | title | PASS | - | 0 |
| expect_column_values_to_not_be_null | text_for_embedding | PASS | - | 0 |
| expect_column_value_lengths_to_be_between | summary | PASS | - | 0 |

## Freshness SLA

- Status: **FRESH**
- Stale rows (age > 180 days): 1/24 (4.2%, max allowed 25.0%)
- Published range: 2026-03-28 -> 2026-07-22

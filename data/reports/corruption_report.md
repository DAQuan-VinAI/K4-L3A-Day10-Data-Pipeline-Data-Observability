# Corruption Report: Baseline vs Corrupted vs Repaired

Generated at: 2026-09-25T08:10:23.846234+00:00

## 3-State Comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Data Quality Gate | PASSED (6/6) | FAILED (4/6) | PASSED (6/6) |
| Freshness SLA | FRESH (1/24 > 180d) | STALE (9/24 > 180d) | FRESH (1/24 > 180d) |
| Retrieval hit rate | 100.0% | 50.0% | 100.0% |
| Mean token F1 | 0.933 | 0.712 | 0.933 |
| LLM judge accuracy | 80.0% | 70.0% | 80.0% |
| Mean judge score | 4.60 | 4.20 | 4.60 |

### Delta vs baseline

| Metric | Corrupted | Repaired |
|---|---|---|
| Retrieval hit rate | -50.0 pp | +0.0 pp |
| Mean token F1 | -0.221 | +0.000 |
| LLM judge accuracy | -10.0 pp | +0.0 pp |

## Injected Corruption Scenarios

Seed `42` - rows 24 -> 24 (row count unchanged, so a simple volume check cannot detect the damage).

| Scenario | Affected rows | Description |
|---|---|---|
| drop_latest_records | 5 | Bo 5 bai bao moi nhat (20%) |
| blank_summary | 3 | Xoa trang summary |
| inject_text_noise | 3 | Chen ky tu rac vao summary/text_for_embedding |
| truncate_title | 3 | Cat title con 7 ky tu |
| stale_date | 6 | Lui published 1825 ngay (~5 nam) |
| duplicate_rows | 5 | Nhan doi ban ghi (trung paper_id) |

## What the Quality Gate Caught

- `expect_column_values_to_be_unique` on `paper_id`: 10 unexpected values
- `expect_column_value_lengths_to_be_between` on `summary`: 4 unexpected values
- Freshness: 9/24 rows older than 180 days (37.5%, limit 25.0%) -> STALE

## Silent Failure Evidence

4/10 questions retrieved the wrong document yet were still judged correct. The corpus contains near-duplicate 'Advanced Perspectives on ...' papers that share authors and categories with the dropped originals, so the RAG answers confidently from the wrong source and the LLM judge does not notice.

| ID | Type | Retrieved (top-1) | Expected | Token F1 | Judge | Answer |
|---|---|---|---|---|---|---|
| q01 | summary | 10.1145/3637528.3671824 | 10.1145/3637528.3671812 | 0.00 | 5 | (empty) |
| q02 | summary | 10.1145/3637528.3671820 | 10.1145/3637528.3671808 | 0.79 | 4 | An extended empirical study on single LLM is susceptible to  |
| q03 | authors | 10.1145/3637528.3671816 | 10.1145/3637528.3671804 | 1.00 | 5 | Bao Do, Linh Ngo |
| q04 | authors | 10.1145/3637528.3671819 | 10.1145/3637528.3671807 | 1.00 | 5 | Kien Duong, Vy Ly |

## Conclusion

- Answer-level metrics alone understate the damage: judge accuracy dropped far less than retrieval hit rate, so monitoring must include retrieval and data-level checks, not only answer grading.
- The GX quality gate and freshness SLA flagged the corrupted batch before indexing; enforcing the gate in the pipeline would have blocked it.
- Idempotent repair rebuilds the clean table from the raw snapshot with the same cleaning code, so it can be re-run safely any number of times.
- Repaired retrieval metrics match the baseline (hit rate 100.0%, token F1 0.933). LLM judge scores can vary slightly between runs because the judge is a live model.

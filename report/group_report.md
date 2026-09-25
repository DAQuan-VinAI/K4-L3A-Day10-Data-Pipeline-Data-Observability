# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | [Tên hoặc mã nhóm]     |
| Repository         | https://github.com/DAQuan-VinAI/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trần Thu Phương | 2A202602734 | Pha 2 — Ingestion, cleaning & quality gate owner | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/observability/quality.py`, `data/raw/`, `data/clean/`, `data/quality/` |
| 2 | Nguyễn Phương Nam | 2A202602869 | Pha 3 — Evaluation-set & vector index owner | `src/evaluation/testset.py`, `src/retrieval/index.py`, `data/eval/test_set.json`, ChromaDB `papers-baseline` |
| 3 | Đoàn Anh Quân | 2A202602803 | Pha 4, 5, 6 — Baseline orchestration, corruption, repair & comparison owner | `src/pipelines/phase1.py`, `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` (`evaluate_state`, `repair_from_raw`, `main`), `src/observability/reporting.py` (`generate_phase1_report`, `generate_corruption_report`) |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ hai luồng: baseline (`script/run_phase1.py`) và corruption → repair → comparison (`script/run_corruption_flow.py`); cả hai chạy với exit code 0. Baseline sinh đủ artifact: raw records, bảng sạch 24 dòng (`data/clean/`), ChromaDB collection `papers-baseline` 24 documents, test set cố định 10 câu (`data/eval/test_set.json`), báo cáo GX 1.x và freshness (`data/quality/`), metrics (`data/results/baseline_metrics.json`) và `data/reports/phase1_report.md`. Baseline đạt retrieval hit rate 100%, token F1 0.933, judge accuracy 80%.

Nhóm tiêm 6 kịch bản lỗi nhưng giữ nguyên số dòng (24 → 24). Kịch bản ảnh hưởng mạnh nhất là **drop latest records**: 5 bài mới nhất bị xóa đều là tài liệu ground truth của q01–q05, làm hit rate giảm từ 100% xuống 50%. Quality gate phát hiện được trùng `paper_id` và `summary` rỗng (FAILED 4/6), freshness chuyển sang STALE (9/24 bài quá 180 ngày). Điểm đáng chú ý là judge accuracy chỉ giảm 10 điểm phần trăm (80% → 70%): 4/10 câu lấy sai tài liệu nhưng vẫn được chấm đúng. Đây là bằng chứng rõ của silent failure.

Repair tái tạo dữ liệu từ `data/raw/crossref_records.json` và phục hồi 100% về baseline ở mọi chỉ số. Giới hạn lớn nhất: dữ liệu là snapshot offline có sẵn trong repo (không gọi live API), test set nhỏ (10 câu), và QA extractive không trả lời trọn câu multi-hop.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
data/raw/crossref_response.json (snapshot; live API khi REFRESH_SOURCE=1, fallback khi 429/mất mạng)
    -> parse_crossref_payload -> data/raw/crossref_records.json
    -> build_clean_dataframe -> data/clean/papers_clean.{csv,json}
    -> GX 1.x quality gate + freshness SLA -> data/quality/  (fail = dừng pipeline baseline)
    -> MiniLM embedding + ChromaDB (papers-baseline)
    -> test set cố định -> evaluate (hit rate, token F1, LLM judge) -> data/results/baseline_*.json
    -> data/reports/phase1_report.md
    -> corrupt_clean_dataframe (6 kịch bản) -> papers-corrupted -> re-evaluate
    -> repair_from_raw (từ raw records) -> papers-repaired -> re-evaluate
    -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref `/works` hoặc snapshot | Retry 3 lần với backoff 2^n giây cho 429/5xx, fallback snapshot, parse DOI/title/abstract/date | `data/raw/crossref_response.json`, `crossref_records.json` | Trần Thu Phương |
| Cleaning          | Raw records | Chuẩn hóa whitespace, bỏ thẻ JATS, loại dòng thiếu khóa, dedup theo `paper_id`, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.{csv,json}` | Trần Thu Phương |
| Embedding/index   | Clean dataframe | `all-MiniLM-L6-v2` (normalized), Chroma HNSW cosine, 1 collection mỗi trạng thái | `data/chroma/`, `data/embeddings/*.json` | Nguyễn Phương Nam |
| Evaluation        | Clean dataframe | 10 câu / 5 loại, hit rate + token F1 + LLM judge | `data/eval/test_set.json` (test set); `data/results/*_metrics.json` (chạy đánh giá) | Nguyễn Phương Nam (test set), Đoàn Anh Quân (chạy đánh giá) |
| Observability     | Clean dataframe | 6 expectations GX 1.x (ephemeral context), freshness 180 ngày / tối đa 25% stale | `data/quality/*.json` | Trần Thu Phương |
| Corruption/repair | Clean dataframe / raw records | 6 kịch bản lỗi (seed 42); repair tái tạo từ raw | `data/results/corruption_log.json`, `data/clean/papers_clean_{corrupted,repaired}.*` | Đoàn Anh Quân |
| Orchestration     | Tất cả ở trên | Thứ tự chạy, gate, lưu artifact, báo cáo | `data/reports/phase1_report.md`, `corruption_report.md` | Đoàn Anh Quân |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `openai`          |
| `LLM_MODEL`                | `gpt-4o-mini`     |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24                |
| Retrieval`top_k`           | 4                 |
| Freshness threshold          | 180 ngày, tối đa 25% bản ghi stale |
| Random seed, nếu có        | 42 (corruption)   |

### Lệnh cài đặt

```bash
uv sync
source .venv/bin/activate
```

### Lệnh chạy

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (exit code 0) | 2026-09-25 15:01 (GMT+7) | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (exit code 0) | 2026-09-25 15:10 (GMT+7) | `data/results/{corrupted,repaired}_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API `https://api.crossref.org/works`; lần chạy nộp bài dùng snapshot `data/raw/crossref_response.json` có sẵn trong repo |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:<hôm nay − 180 ngày>,has-abstract:true`, `rows=24` |
| Thời điểm lấy dữ liệu | Snapshot offline; raw records được parse lại lúc 2026-09-25 |
| Số record nhận được    | 24 items → 24 records hợp lệ |
| Cơ chế retry/backoff      | Tối đa 3 lần, nghỉ 2^n giây, chỉ retry với 429/500/502/503/504; hết lượt thì fallback snapshot |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | str | Có | DOI chuẩn hóa (lowercase, bỏ `https://doi.org/`) | Bỏ record |
| `title` | str | Có | Tiêu đề đã gộp whitespace | Bỏ record |
| `summary` | str | Có | Abstract đã bỏ thẻ JATS/HTML và unescape | Bỏ record |
| `published` | str (ISO date) | Có | Ưu tiên `published` → `published-print` → `published-online` → `issued` → `created` | Bỏ record |
| `authors` | list[str] | Không | `given family` hoặc `name` | List rỗng |
| `categories` / `primary_category` | list[str] / str | Không | Crossref `subject` | `Uncategorized` |
| `updated` | str (ISO date) | Không | `updated` → `indexed` → `published` | Dùng `published` |
| `age_days` | int | Có (clean) | `(run_date − published).days`, chặn dưới 0 | Tính lại mỗi lần chạy |
| `text_for_embedding` | str | Có (clean) | Ghép Title/Authors/Published/Categories/Summary | Tạo lại từ các cột trên |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record thiếu DOI/title/summary/published | Completeness | 0 | 24 raw → 24 clean |
| Bỏ thẻ `<jats:*>`/HTML trong summary | Validity | Tất cả summary có markup | `ExpectColumnValueLengthsToBeBetween(summary ≥ 30)` pass |
| Dedup theo `paper_id`, giữ bản `updated` mới nhất | Uniqueness | 0 | `ExpectColumnValuesToBeUnique(paper_id)` pass |
| Chuẩn hóa DOI về lowercase, bỏ prefix | Consistency | 24 | So `paper_id` giữa raw/clean/test set |

Document ID dùng DOI chuẩn hóa làm `paper_id` (ổn định giữa các lần chạy). Chroma record id là `<paper_id>::<row_index>` để collection bị corrupt vẫn nạp được bản ghi trùng. `age_days` tính theo UTC tại thời điểm chạy, nên cùng một dataset có thể chuyển từ fresh sang stale theo thời gian. `text_for_embedding` gồm 5 dòng `Title/Authors/Published/Categories/Summary`, để metadata cũng được embed và truy vấn theo tác giả hoặc ngày vẫn trúng.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10                          |
| Các`question_type`                    | `summary`, `authors`, `date`, `category`, `multi_hop` (mỗi loại 2 câu) |
| Ground-truth document ID                 | `paper_id` của bài được hỏi (multi_hop có 2 ID); hit nếu một ID nằm trong top-k |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB persistent, cosine; `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Retrieval`top_k`                       | 4                           |
| LLM provider/model                       | OpenAI `gpt-4o-mini` (LLM judge và agent demo) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (sha256 bắt đầu bằng `0551af7faa84c3d4`) |

Test set được sinh một lần từ dữ liệu sạch rồi đóng băng: `load_or_create_test_set` chỉ đọc lại file, trừ khi đặt `REFRESH_TEST_SET=1`. Nếu sinh lại từ dữ liệu corrupted thì câu hỏi và ground truth sẽ đổi theo lỗi, và phép so sánh không còn đo tác động của dữ liệu lên agent.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 items / 24 records |
| Cleaned dataset          | `data/clean/`                        | Có | 24 dòng, 16 cột |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | 3 manifest, 3 collection |
| Evaluation set           | `data/eval/`                         | Có | 10 câu |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json` |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality_report.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Có breakdown theo loại câu hỏi |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.000 | Cả 10 câu đều lấy được tài liệu đúng trong top-4 |
| `mean_token_f1`      |     0.933 | 8 câu single-hop khớp tuyệt đối; 2 câu multi_hop đạt 0.67 vì chỉ trả lời nửa đầu |
| `judge_accuracy`     |     0.800 | 2 câu multi_hop bị chấm 3/5 (thiếu ngày xuất bản) |
| `mean_judge_score`   |     4.60 | 8 câu 5/5, 2 câu 3/5 |
| Ragas, nếu có        | N/A | Không bật `RUN_RAGAS=1` vì chậm và tốn thêm lời gọi LLM |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Volume | 5–5000 dòng | Pass (24) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(paper_id, title, text_for_embedding)` | Completeness | 0 null | Pass (0 unexpected) | như trên |
| `ExpectColumnValuesToBeUnique(paper_id)` | Uniqueness | 0 trùng | Pass (0 unexpected) | như trên |
| `ExpectColumnValueLengthsToBeBetween(summary)` | Validity | ≥ 30 ký tự | Pass (0 unexpected) | như trên |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean dataset (`age_days`, `published`) trước khi index |
| Timestamp mới nhất       | 2026-07-22 (cũ nhất 2026-03-28) |
| Ngưỡng freshness         | `age_days > 180` bị tính stale; fresh nếu tỉ lệ stale ≤ 25% |
| Trạng thái baseline      | Fresh |
| Lý do                     | 1/24 bài (4.2%) quá 180 ngày, dưới ngưỡng 25% |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_records` | Xóa 20% bài có `published` mới nhất | 5 | Freshness (bài mới mất) | Mất ground truth của q01–q05, hit rate −50 pp | Tái tạo từ raw |
| `blank_summary` | Gán `summary = ""` | 3 | Summary length fail | `summary` fail 4 unexpected (3 + 1 bản duplicate) | Tái tạo từ raw |
| `inject_text_noise` | Chèn 6 token rác vào giữa summary | 3 | Không có check bắt được | Chạm tài liệu thứ hai của q10 nhưng câu đó hỏi ngày nên metric không đổi | Tái tạo từ raw |
| `truncate_title` | Cắt title còn 7 ký tự | 3 | Không có check bắt được | Làm hỏng tra cứu title chính xác của các bài song sinh | Tái tạo từ raw |
| `stale_date` | Lùi `published` 1825 ngày | 6 | Freshness STALE | 9/24 stale (37.5% > 25%) | Tái tạo từ raw |
| `duplicate_rows` | Nhân đôi bản ghi | 5 | Unique `paper_id` fail | 10 unexpected (5 cặp trùng) | Dedup trong cleaning khi tái tạo |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log có đủ 6 kịch bản, seed, số dòng vào/ra (24 → 24), danh sách `paper_id` bị tác động, cùng tham số từng kịch bản (chuỗi noise, title gốc, ngày gốc và ngày sau khi làm cũ).

`repair_from_raw` không vá từng lỗi trên bảng corrupted. Hàm bỏ hẳn bảng đó, đọc lại `data/raw/crossref_records.json` (bản raw không bao giờ bị ghi đè trong corruption flow) và chạy lại đúng `build_clean_dataframe`. Vì kết quả chỉ phụ thuộc vào raw snapshot, repair có tính idempotent: chạy lại bao nhiêu lần cũng ra cùng một bảng. Pipeline xác minh tập `paper_id` sau repair trùng với baseline (log `khop baseline paper_id: True`) rồi mới đánh giá lại trên collection riêng `papers-repaired`.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   | 1.000 | 0.500 | 1.000 | −0.500 | 100% | q01–q05 mất tài liệu ground truth |
| `mean_token_f1`        | 0.933 | 0.712 | 0.933 | −0.221 | 100% | q01 trả về rỗng, q05 sai ngày |
| `judge_accuracy`       | 0.800 | 0.700 | 0.800 | −0.100 | 100% | Giảm ít hơn nhiều so với hit rate |
| `mean_judge_score`     | 4.60 | 4.20 | 4.60 | −0.40 | 100% | |
| Quality checks pass/fail | 6/6 Pass | 4/6 Fail | 6/6 Pass | −2 checks | 100% | Fail: unique `paper_id`, độ dài `summary` |
| Freshness status         | Fresh (4.2%) | Stale (37.5%) | Fresh (4.2%) | +33.3 pp stale | 100% | |

1. **Drop latest records + stale date → freshness STALE (9/24) → hit rate 100% → 50%.** Năm bài mới nhất bị xóa chính là tài liệu được hỏi ở q01–q05. Retriever trả về bản "Advanced Perspectives on …" song sinh, có cùng tác giả và lĩnh vực, nên q03/q04 vẫn "đúng" câu trả lời, còn q01 (summary rỗng) và q05 (sai ngày) thì sai. Bằng chứng: `data/results/corrupted_answers.json`, mục *Silent Failure Evidence* trong `corruption_report.md`.
2. **Repair từ raw → quality 6/6 và freshness Fresh → hit rate, F1, judge về đúng baseline.** Cùng test set, cùng code cleaning, cùng model embedding nên metric khớp tuyệt đối (`repaired_metrics.json` = `baseline_metrics.json`).

Kết quả khác kỳ vọng: judge accuracy chỉ giảm 10 pp dù hit rate giảm 50 pp. Nhóm đã kiểm tra từng câu: 4/10 câu lấy sai tài liệu nhưng vẫn được chấm đúng, trong đó q01 có câu trả lời **rỗng** mà vẫn được 5/5. Vì vậy chỉ theo dõi điểm judge là không đủ để phát hiện dữ liệu hỏng.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Các lệnh kiểm tra CP2 của giảng viên báo lỗi: `AttributeError` với `s.paths.test_set_json`, `ts.samples`, và `TypeError: LocalEmbeddingIndex.__init__() missing 2 required positional arguments: 'documents' and 'persist_path'`.
- **Nguyên nhân:** Lệnh kiểm tra dùng một API khác starter code: tên path khác, test set là object có `.samples`, index khởi tạo bằng tên collection kèm `build_from_clean()`/`semantic_search()`.
- **Cách xử lý:** Bổ sung theo kiểu tương thích ngược, không đổi chữ ký cũ: property `Paths.test_set_json`, class `TestSet(list)` có `.samples`, `documents`/`persist_path` trở thành tùy chọn (tự nạp từ manifest của collection), thêm `build_from_clean()` và `semantic_search()`.
- **Cách xác minh:** Lệnh của giảng viên in `Test set gồm 10 câu hỏi` và `Tìm thấy 2 tài liệu liên quan`; các lệnh cũ (`build_test_set`, `LocalEmbeddingIndex.load`) và cả hai pipeline vẫn chạy với exit code 0.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Dữ liệu là snapshot offline, có nhiều cặp bài gần trùng ("Advanced Perspectives on …") | Che giấu một phần tác động của corruption | Chạy `REFRESH_SOURCE=1` với live API và so sánh hit rate |
| LLM judge chấm đúng cả câu trả lời rỗng (q01 corrupted) | `judge_accuracy` đánh giá quá cao | Bắt buộc judge trả 1 điểm khi câu trả lời rỗng, đo lại judge accuracy trên corrupted |
| QA extractive chỉ trả lời 1 ý | `multi_hop` luôn chỉ đạt 0.67 F1 | Dùng agent/LLM tổng hợp nhiều context, đo F1 riêng nhóm `multi_hop` |
| Không có check cho noise và title bị cắt | 2/6 kịch bản lọt qua quality gate | Thêm expectation độ dài title ≥ 15 và regex chặn token rác; kỳ vọng corrupted fail 6/8 |
| Test set 10 câu, Ragas chưa chạy | Độ tin cậy thống kê thấp | Tăng lên ≥ 30 câu, bật `RUN_RAGAS=1` |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [ ] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.

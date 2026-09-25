# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đoàn Anh Quân             |
| MSSV               | 2A202602803                |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | nhóm chót                 |
| Vai trò chính    | Baseline orchestration, corruption, repair & comparison owner (Pha 4, 5, 6 / CP3, CP4, CP5) |
| Repository         | https://github.com/DAQuan-VinAI/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Baseline pipeline end-to-end (Pha 4) | `src/pipelines/phase1.py`: `main`, `save_clean_artifacts`, `_load_records`, `_run_agent_demo` | Raw records, module cleaning/quality/index/testset/metrics của các thành viên khác | `data/clean/`, `papers-baseline`, `data/results/baseline_*.json`, `agent_demo_answers.json` | Hoàn thành |
| Báo cáo baseline | `src/observability/reporting.py`: `generate_phase1_report` | Metrics, answers, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Corruption suite (Pha 5) | `src/ingestion/corruption.py`: `corrupt_clean_dataframe` | `data/clean/papers_clean.json` | Dataframe corrupted, `data/results/corruption_log.json` | Hoàn thành |
| Đo suy giảm | `src/pipelines/corruption_flow.py`: `evaluate_state`, `state_paths` | Dataframe corrupted, test set cố định | `data/results/corrupted_metrics.json`, `corrupted_answers.json`, `data/quality/corrupted_*.json` | Hoàn thành |
| Idempotent repair (Pha 6) | `src/pipelines/corruption_flow.py`: `repair_from_raw` | `data/raw/crossref_records.json` | `data/clean/papers_clean_repaired.*`, `papers-repaired`, `data/results/repaired_metrics.json` | Hoàn thành |
| Corruption flow + báo cáo 3 trạng thái (Pha 6) | `corruption_flow.main`; `reporting.py`: `comparison_rows`, `generate_corruption_report` | Baseline artifacts, kết quả corrupted/repaired, corruption log | Bảng so sánh trên console, `data/reports/corruption_report.md` | Hoàn thành |

Phần của tôi là nửa sau của pipeline. Tôi nhận output của ingestion, cleaning và quality gate (Trần Thu Phương, Pha 2), test set và vector index (Nguyễn Phương Nam, Pha 3), rồi tự nối tiếp sang Pha 6: dùng lại `evaluate_state` cho trạng thái repaired và tổng hợp ba trạng thái vào báo cáo so sánh cuối cùng của nhóm.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Điền nếu có hỗ trợ thành viên khác; nếu không, xóa dòng này] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Ghép 6 bước baseline, dừng pipeline nếu quality gate fail | `src/pipelines/phase1.py` | 5 artifact bắt buộc của CP3 | `python script/run_phase1.py` → exit 0 |
| Báo cáo baseline có breakdown theo loại câu hỏi và theo từng câu | `generate_phase1_report` | `data/reports/phase1_report.md` | Đọc báo cáo, đối chiếu với `baseline_metrics.json` |
| 6 kịch bản corruption deterministic (seed 42), giữ nguyên số dòng | `src/ingestion/corruption.py` | `corruption_log.json` với đủ 6 kịch bản | Lệnh CP4 in `Corrupted 24 dòng` |
| Đánh giá trạng thái corrupted trên collection riêng | `evaluate_state` | `corrupted_metrics.json` | Hit rate 1.00 → 0.50 |
| Repair từ raw và xác minh tập `paper_id` khớp baseline | `repair_from_raw`, `corruption_flow.main` | `repaired_metrics.json` = `baseline_metrics.json` | `python script/run_corruption_flow.py` → log `khop baseline paper_id: True` |
| Báo cáo đối chiếu 3 trạng thái + bằng chứng silent failure | `generate_corruption_report`, `comparison_rows` | `data/reports/corruption_report.md` | Bảng console và bảng Markdown dùng chung `comparison_rows` nên luôn khớp |

Output cụ thể: `data/results/corrupted_metrics.json` cho thấy hit rate giảm từ 1.000 xuống 0.500 và token F1 từ 0.933 xuống 0.712, trong khi số dòng vẫn là 24. Đây là bằng chứng chính của CP4 rằng dữ liệu hỏng có thể lọt qua mọi kiểm tra dựa trên số lượng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pha 4: các module riêng lẻ đã chạy được, nhưng chưa có một lệnh nào tạo ra toàn bộ artifact baseline theo đúng thứ tự phụ thuộc: clean → gate → index → test set → evaluate → report. Pha 5: cần chứng minh bằng thực nghiệm rằng dữ liệu bẩn làm RAG trả lời sai trong im lặng, và đo được mức suy giảm đó. Pha 6: cần phục hồi dữ liệu mà không vá tay từng lỗi, rồi chứng minh bằng số liệu rằng hệ thống trở lại đúng trạng thái baseline.

### Cách triển khai

**Baseline (`phase1.py`):**
- Dùng raw records đã lưu trước (lineage), chỉ gọi API khi `REFRESH_SOURCE=1`, để lần chạy nào cũng dùng cùng nguồn dữ liệu.
- Lưu clean CSV/JSON bằng `save_clean_artifacts` (được tái sử dụng cho trạng thái corrupted và repaired).
- Chạy GX + freshness; nếu `success=False` thì `raise`, không cho dữ liệu hỏng vào Chroma.
- Build `papers-baseline`, tải test set cố định (`load_or_create_test_set`), đánh giá, rồi viết báo cáo.
- Agent demo (2 câu) nằm trong `try/except`: agent phụ thuộc LLM ngoài, nếu lỗi thì baseline vẫn phải hoàn tất.

**Corruption (`corruption.py`):**
- Tất cả ngẫu nhiên đi qua `random.Random(42)`, nên mỗi lần chạy tạo ra đúng cùng một bộ lỗi và so sánh giữa các lần chạy là công bằng.
- Drop 20% bài mới nhất (5 dòng). Các kịch bản 2–5 lấy mẫu **không chồng lấn** trên 15 dòng còn lại để log rõ dòng nào chịu lỗi nào: blank summary 3, noise 3, truncate title (7 ký tự) 3, stale date (−1825 ngày) 6.
- Duplicate 5 dòng, bù đúng số dòng đã xóa → vẫn 24 dòng.
- Tạo lại `summary_chars` và `text_for_embedding` để lỗi đi vào vector, không chỉ nằm ở cột metadata.

**Repair và so sánh (Pha 6):** `repair_from_raw` bỏ hẳn bảng corrupted, đọc lại `data/raw/crossref_records.json` và chạy lại đúng `build_clean_dataframe`. Kết quả chỉ phụ thuộc vào raw nên chạy lại bao nhiêu lần cũng giống nhau (idempotent). `main` kiểm tra tập `paper_id` sau repair khớp baseline, đánh giá trên `papers-repaired`, rồi gọi `generate_corruption_report`. Bảng so sánh trên console và trong Markdown cùng sinh từ `comparison_rows` để hai nơi không bao giờ lệch nhau. Báo cáo có thêm mục *Silent Failure Evidence*, tự liệt kê các câu lấy sai tài liệu nhưng vẫn được judge chấm đúng.

**Đo suy giảm (`evaluate_state`):** mỗi trạng thái có path và collection riêng (`papers-corrupted`), dùng cùng test set. Quality gate ở đây chỉ ghi nhận chứ không chặn, vì mục đích là quan sát chuyện gì xảy ra nếu dữ liệu bẩn lọt qua.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean dataframe theo `CLEAN_COLUMNS` (16 cột), `data/eval/test_set.json`, `Settings` |
| Output                         | Dataframe cùng schema; `corruption_log.json` gồm `seed`, `input_rows`, `output_rows`, `scenarios[]` (tên, mô tả, `paper_ids`, tham số); `*_metrics.json` gồm `samples`, `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` |
| Module phụ thuộc             | `ingestion.cleaning`, `observability.quality`, `retrieval.index`, `evaluation.testset`, `evaluation.metrics` |
| Module sử dụng output        | `corruption_flow.main` (repair + comparison), `generate_corruption_report` |
| Điều kiện lỗi cần xử lý | Quality gate fail ở baseline → dừng; thiếu baseline artifacts khi chạy corruption flow → báo chạy `run_phase1.py` trước; agent/LLM lỗi → ghi `{"error": ...}` và tiếp tục |

### Cách xác minh

```bash
python script/run_phase1.py
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Có đủ 5 artifact baseline; in `Corrupted 24 dòng`; log có 6 kịch bản; corrupted metrics giảm rõ so với baseline.
- **Kết quả thực tế:** Cả hai script exit 0. Baseline: hit 1.000 / F1 0.933 / judge 0.80. In `Tín hiệu hoàn thành: Corrupted 24 dòng`, `scenario_count: 6`. Corrupted: hit 0.500 / F1 0.712 / judge 0.70, GX 4/6, freshness STALE.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`, `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Kịch bản "drop latest records" làm giảm số dòng. Nếu chỉ xóa thì check `ExpectTableRowCountToBeBetween` hoặc một dashboard đếm dòng có thể phát hiện ngay, và thí nghiệm không còn mô phỏng *silent* failure.
- **Các phương án đã cân nhắc:** (a) chỉ xóa, để còn 19 dòng; (b) chèn dòng rác mới để bù; (c) nhân đôi đúng 5 dòng có sẵn để bù.
- **Phương án đã chọn:** (c), kết hợp stale date trên 6 dòng.
- **Lý do:** Số dòng giữ nguyên 24 nên tín hiệu về volume không phát hiện được. Bản ghi trùng lại là lỗi có thật trong ingestion (retry ghi hai lần), và nó kiểm tra đúng expectation unique `paper_id`. Số dòng stale được chọn là 6 để tỉ lệ stale (cộng 1 bài vốn đã cũ, rồi thêm các bản duplicate) vượt ngưỡng 25%, nhờ đó thí nghiệm chạm tới cả freshness SLA.
- **Bằng chứng quyết định phù hợp:** `corrupted_quality_report.json`: row count **pass** (24), nhưng unique `paper_id` **fail** (10 unexpected), freshness 9/24 = 37.5% → STALE. Chỉ những check đúng loại mới bắt được lỗi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lệnh kiểm tra quality của CP1 đọc `pd.read_json(s.paths.clean_json)` nhưng file `data/clean/papers_clean.json` không tồn tại; `phase1.py` ban đầu chỉ có `raise NotImplementedError("Student task: implement phase1 pipeline.")`.
- **Lệnh hoặc bước tái hiện:** Chạy lệnh kiểm tra `run_data_quality_checks` trên repo mới clone trước khi có baseline pipeline.
- **Nguyên nhân gốc:** Clean artifact chỉ được tạo trong orchestration (bước "Save clean CSV/JSON" của `phase1.py`), còn `build_clean_dataframe` chỉ trả về dataframe mà không ghi file. Các checkpoint trước vì vậy phụ thuộc ngầm vào Pha 4.
- **Cách xử lý:** Viết `save_clean_artifacts(df, csv_path, json_path)`, ghi JSON bằng `orient="records"` để `pd.read_json` đọc lại đúng schema, và gọi hàm này ngay sau bước cleaning trong `phase1.main`. Hàm này sau đó được dùng lại cho trạng thái corrupted và repaired.
- **Cách xác minh sau khi sửa:** Sau `python script/run_phase1.py`, lệnh kiểm tra CP1 in `Quality check status = True`; `pd.read_json` đọc lại được 24 dòng.
- **Điều học được:** Contract giữa các module phải bao gồm cả artifact trên đĩa, chứ không chỉ giá trị trả về. Nếu không, các bước kiểm tra riêng lẻ sẽ phụ thuộc vào thứ tự chạy.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. `crossref.py` lấy payload (live API, hoặc snapshot khi gặp 429/mất mạng), parse thành `PaperRecord` và lưu nguyên bản raw. `cleaning.py` chuẩn hóa, dedup theo DOI, tính `age_days` và ghép `text_for_embedding`. Cột này được MiniLM embed (đã normalize) rồi nạp vào ChromaDB với khoảng cách cosine.
2. Mỗi câu hỏi mang `ground_truth_doc_ids` là `paper_id` của bài được hỏi. Retrieval hit = một trong các ID đó nằm trong top-4. Chất lượng câu trả lời được đo bằng token F1 so với `ground_truth` và bằng LLM judge (1–5, đúng/sai).
3. Quality checks (GX) kiểm tra **cấu trúc và nội dung** của từng dòng tại một thời điểm: null, trùng, độ dài, số dòng. Freshness đo **tuổi** của dữ liệu so với thời điểm chạy, ở mức tỉ lệ toàn bảng. Một bảng có thể pass GX nhưng vẫn stale, và ngược lại.
4. Nếu test set thay đổi thì metric thay đổi vì câu hỏi khác, không phải vì dữ liệu. Giữ cố định test set (và seed, model, top_k) thì chênh lệch metric chỉ còn phản ánh tác động của dữ liệu.
5. Repair thành công khi `repaired_quality_report.json` pass 6/6, freshness trở lại Fresh, tập `paper_id` khớp baseline, và `repaired_metrics.json` bằng `baseline_metrics.json` (hit 1.000, F1 0.933).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.000 | 0.500 | 1.000 | 5 bài bị drop là ground truth của q01–q05 |
| `mean_token_f1`      | 0.933 | 0.712 | 0.933 | Giảm ít hơn hit rate vì bài song sinh có cùng tác giả |
| `judge_accuracy`     | 0.800 | 0.700 | 0.800 | Judge không nhận ra lấy sai nguồn |
| `mean_judge_score`   | 4.60 | 4.20 | 4.60 | q01 trả lời rỗng vẫn được 5/5 |
| Quality checks         | 6/6 | 4/6 | 6/6 | Bắt được duplicate và summary rỗng |
| Freshness status       | Fresh (4.2%) | Stale (37.5%) | Fresh (4.2%) | Bắt được stale date |

### Kết luận từ số liệu

1. **Drop 5 bài mới nhất + làm cũ 6 bài** → freshness 4.2% → 37.5% (STALE) → hit rate 1.000 → 0.500 và token F1 0.933 → 0.712, vì ground truth của q01–q05 không còn trong index.
2. **Repair từ raw records** → GX 6/6, freshness Fresh → hit rate, F1, judge về đúng giá trị baseline, vì cùng raw, cùng code cleaning và cùng test set.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest_records` gây toàn bộ 5 lần mất hit, vì test set chọn bài mới nhất làm câu hỏi (ưu tiên bản gốc, sắp theo `published` giảm dần). `blank_summary` gây thêm lỗi nặng nhất về câu trả lời: bài song sinh của q01 (3671824) bị xóa summary, nên hệ thống trả về chuỗi rỗng. `inject_text_noise` và `truncate_title` gần như không ảnh hưởng metric trong lần chạy này, vì chúng chủ yếu rơi vào các bài không được hỏi trực tiếp.

Kết quả nào khác với kỳ vọng ban đầu?

Tôi kỳ vọng judge accuracy giảm tương đương hit rate, nhưng thực tế chỉ giảm 10 pp. Giả thuyết: corpus có các cặp bài "X" / "Advanced Perspectives on X" dùng chung tác giả và lĩnh vực, nên khi bài gốc mất, retriever lấy bản song sinh và câu trả lời về tác giả vẫn đúng. Tôi kiểm tra bằng cách đọc `corrupted_answers.json`: q02–q04 có top-1 là bản song sinh (3671820, 3671816, 3671819) nhưng judge chấm đúng. Riêng q01 trả lời rỗng nhưng vẫn được 5/5, tức LLM judge cũng không đáng tin khi dữ liệu hỏng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Pipeline phải giữ raw bất biến và làm cho mọi bước sau có thể tái tạo từ raw. Nhờ vậy repair chỉ là "chạy lại", không phải vá tay.
2. Mỗi loại lỗi cần một loại tín hiệu riêng: đếm dòng không bắt được duplicate bù dòng, GX không bắt được dữ liệu cũ, còn noise và title bị cắt không có check nào bắt.
3. Điểm chất lượng câu trả lời có thể che lỗi dữ liệu: RAG trả lời tự tin từ sai nguồn và judge vẫn cho điểm cao. Phải giám sát cả retrieval (hit rate theo ground-truth ID), không chỉ answer score.

### Nếu có thêm thời gian

Thêm hai expectation: độ dài `title` ≥ 15 ký tự và regex chặn token rác (`@@##`, `0xDEADBEEF`, `<null>`) trong `summary`, rồi chạy lại corruption flow. Kỳ vọng: quality gate corrupted bắt được 4/6 kịch bản thay vì 2/6, còn baseline vẫn pass toàn bộ. Đo bằng số expectation fail trong `corrupted_quality_report.json` và `baseline_quality_report.json`.

## 10. Cam kết của thành viên

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đoàn Anh Quân
**Ngày xác nhận:** [YYYY-MM-DD]

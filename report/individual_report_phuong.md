# Báo cáo cá nhân - Day 10: Data Pipeline & Data Observability

> Các trường thông tin cá nhân cần được thay trước khi nộp. Các kết quả kỹ thuật bên dưới chỉ ghi những gì đã được kiểm chứng trong repository.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Thu Phương |
| MSSV | 2A202602734 |
| Khóa/Lớp | K4-L3-DAY10 |
| Tên nhóm | nhóm chót |
| Vai trò chính | Data Foundation & Recovery; hỗ trợ xác minh Quality Gate |
| Repository | https://github.com/DAQuan-VinAI/K4-L3A-Day10-Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Raw ingestion | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref payload hoặc snapshot local | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành và đã xác minh |
| Cleaning/data model | `src/ingestion/cleaning.py`: `build_clean_dataframe` | Raw `PaperRecord` | `data/clean/papers_clean.json`, `papers_clean.csv` | Hoàn thành và đã xác minh |
| Quality validation | `src/observability/quality.py`: `run_data_quality_checks` | Clean DataFrame và `Settings` | `data/quality/test_quality_report.json` | Hoàn thành và đã xác minh |

Việc hỗ trợ ngoài phạm vi chính: xác định lỗi môi trường Python 3.14/NumPy, cài project `src`-layout ở chế độ editable và kiểm tra lại các lệnh ingestion/quality.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Parse metadata Crossref | `src/ingestion/crossref.py` | Chuẩn hóa DOI, title, abstract JATS, authors, categories và ngày ISO | Parser snapshot trả về 24 records; summary không còn thẻ JATS |
| Cứu hộ offline | `src/ingestion/crossref.py`, `data/raw/crossref_response.json` | Retry API và fallback về snapshot khi lỗi mạng/429/5xx | Giả lập `RuntimeError('offline')`, fallback trả về 24 records |
| Tạo dữ liệu sạch | `src/ingestion/cleaning.py`, `data/clean/papers_clean.json` | 24 dòng, có `age_days` và `text_for_embedding` | Build DataFrame và ghi JSON/CSV thành công |
| Quality Gate | `src/observability/quality.py`, `data/quality/test_quality_report.json` | 6/6 expectations đạt, success 100% | `run_data_quality_checks` trả về `True` |

Output cụ thể: `data/quality/test_quality_report.json` ghi `row_count=24`, `successful_expectations=6`, `unsuccessful_expectations=0`, `success_percent=100.0`.

## 4. Giải thích phần kỹ thuật

### Vấn đề cần giải quyết

Pipeline cần bảo toàn dữ liệu nguồn, chuẩn hóa metadata không đồng nhất của Crossref và vẫn chạy được khi API bị giới hạn hoặc phòng lab mất mạng.

### Cách triển khai

Parser lấy DOI và chuẩn hóa về dạng lowercase không có tiền tố URL; title và summary được chuẩn hóa whitespace. Summary được unescape HTML và loại bỏ HTML/JATS tags. Authors được ghép từ `given` và `family`; categories lấy từ `subject`. Ngày được ưu tiên từ các trường published/issued và fallback về `created.date-time`, sau đó đưa về `YYYY-MM-DD`.

Fetcher gửi query, filter và số lượng dòng đến Crossref, retry các mã lỗi tạm thời. Khi request thất bại hoặc API quá tải, payload được đọc từ `data/raw/crossref_response.json`. Records đã parse được ghi riêng vào `data/raw/crossref_records.json` để giữ lineage.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref payload có `message.items`, hoặc JSON snapshot local |
| Output | `list[PaperRecord]`, raw response và raw records JSON |
| Module phụ thuộc | `core.config.Settings`, `core.utils` |
| Module sử dụng output | `ingestion.cleaning`, pipeline và quality checks |
| Điều kiện lỗi | Thiếu DOI/title/summary/ngày thì bỏ record; lỗi API thì dùng snapshot nếu tồn tại |

### Cách xác minh

```powershell
python -m pip install -e .
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print('Tín hiệu hoàn thành: Đã nạp {} bài báo'.format(len(r)))"
```

- **Kết quả thực tế:** Nạp 24 bài báo.
- **Kiểm tra fallback:** `parse + offline fallback: OK`, fallback trả về 24 records.
- **Artifact:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.json`, `data/clean/papers_clean.csv`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** API Crossref có thể trả 429 hoặc không truy cập được trong môi trường lab.
- **Phương án 1:** Dừng pipeline và yêu cầu chạy lại khi mạng ổn định.
- **Phương án 2:** Retry request rồi chuyển sang snapshot local đã lưu.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Giữ pipeline reproducible, không phụ thuộc hoàn toàn vào dịch vụ bên ngoài và vẫn bảo toàn raw lineage.
- **Bằng chứng:** Snapshot local parse được 24 records; test giả lập lỗi mạng chạy qua nhánh fallback thành công.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `ModuleNotFoundError: No module named 'core'`.
- **Lệnh tái hiện:** Chạy import từ project có `src`-layout trước khi cài package editable.
- **Nguyên nhân gốc:** `requirements.txt` chỉ cài dependencies, chưa cài project nên `src` không nằm trong import path.
- **Cách xử lý:** Chạy `python -m pip install -e .` trong `.venv`.
- **Xác minh:** Lệnh `fetch_source_records` chạy và nạp 24 bài báo.
- **Bài học:** Với project dùng `src`-layout, cần cài editable package hoặc cấu hình `PYTHONPATH` trước khi chạy module.

Một lỗi khác là xung đột nháy kép trong PowerShell tại `res["success"]`. Đã sửa bằng `format(res['success'])`; sau đó quality check chạy thành công.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được lưu nguyên bản, parse thành `PaperRecord`, làm sạch thành DataFrame, tạo `text_for_embedding`, sau đó embedding/index dùng dữ liệu sạch để phục vụ retrieval.
2. Evaluation set lưu câu hỏi cùng ground-truth document IDs; cùng các ID đó được dùng để tính hit rate và chất lượng câu trả lời.
3. Quality checks kiểm tra schema, null, uniqueness và độ dài summary tại thời điểm chạy. Freshness monitoring đo tuổi dữ liệu qua `age_days` và tỷ lệ record vượt ngưỡng 180 ngày.
4. Baseline, corrupted và repaired phải dùng cùng test set để khác biệt metric phản ánh chất lượng dữ liệu, không phản ánh bộ câu hỏi khác nhau.
5. Repair thành công khi dữ liệu repaired tạo lại được artifact hợp lệ, quality/freshness đạt yêu cầu và các metric retrieval/answer phục hồi so với baseline.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.500 | 1.000 | Corruption giảm 50 điểm phần trăm; repair phục hồi hoàn toàn |
| `mean_token_f1` | 0.933 | 0.712 | 0.933 | Corruption làm giảm 0.221; repair phục hồi về baseline |
| `judge_accuracy` | 0.800 | 0.700 | 0.800 | Giảm 10 điểm phần trăm khi corrupted |
| `mean_judge_score` | 4.60 | 4.20 | 4.60 | Phục hồi về baseline sau repair |
| Quality checks | 6/6, 100% | 4/6 | 6/6, 100% | GX bắt được duplicate và summary lỗi |
| Freshness status | Fresh, 1/24 stale | Stale, 9/24 stale | Fresh, 1/24 stale | Corruption vượt ngưỡng stale ratio 25% |

Chuỗi nguyên nhân-bằng chứng: corruption làm trống summary, nhân bản record và làm ngày xuất bản cũ đi; quality gate giảm từ 6/6 xuống 4/6, freshness chuyển từ Fresh sang Stale, retrieval hit rate giảm từ 100% xuống 50% và token F1 giảm từ 0.933 xuống 0.712. Repair dựng lại dữ liệu từ raw snapshot bằng cùng cleaning code; quality trở lại 6/6, freshness trở lại Fresh và các metric retrieval/answer trở lại đúng baseline.

Corruption ảnh hưởng rõ nhất là `drop_latest_records` kết hợp với `stale_date`: việc mất 5 record mới nhất tạo ra truy vấn sai tài liệu, còn 6 ngày xuất bản bị lùi 1.825 ngày làm stale ratio tăng lên 37.5%, vượt ngưỡng 25%. Đáng chú ý, judge accuracy chỉ giảm 10 điểm phần trăm, nhỏ hơn mức giảm retrieval, cho thấy chỉ đánh giá câu trả lời là chưa đủ để phát hiện silent failure.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot là điểm khôi phục và là nền tảng để truy vết mọi biến đổi dữ liệu.
2. Quality Gate và freshness là hai tín hiệu bổ sung: một bên kiểm tra tính hợp lệ cấu trúc/nội dung, một bên kiểm tra độ mới theo thời gian.
3. Một lỗi dữ liệu có thể không làm pipeline crash nhưng vẫn làm giảm chất lượng retrieval, vì vậy cần đo lường trên evaluation set cố định.

### Nếu có thêm thời gian

Có thể bổ sung test tự động cho DOI normalization, JATS stripping, date fallback và HTTP 429 fallback. Ngoài ra nên thêm quality gate bắt buộc trước bước indexing để batch corrupted bị chặn, thay vì chỉ ghi nhận lỗi sau khi đã đo retrieval.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end.
- [x] Các kết luận đã ghi đều có artifact hoặc lệnh xác minh.
- [x] Không ghi kết quả baseline/corruption/repaired khi chưa có bằng chứng.
- [x] Báo cáo không chứa API key, token hoặc secret.
- [x] Đã thay thông tin cá nhân và kiểm tra lần cuối trước khi nộp.

**Họ và tên:** Trần Thu Phương
**Ngày xác nhận:** 2026-09-25

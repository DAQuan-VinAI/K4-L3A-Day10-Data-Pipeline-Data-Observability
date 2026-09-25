# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `nhóm chót`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3A-Day10-Data-Pipeline-Data-Observability` (https://github.com/DAQuan-VinAI/K4-L3A-Day10-Data-Pipeline-Data-Observability)

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Trần Thu Phương | 2A202602734 | thuphuongchan1@gmail.com | Pha 2 — Data Foundation & Quality Gate (`crossref.py`, `cleaning.py`, `quality.py` GX 1.x, raw data) | `report/individual_report.md` |
| 2 | Nguyễn Phương Nam | 2A202602869 | namnp.vnua@gmail.com | Pha 3 — Evaluation set & Vector Index (`testset.py`, `retrieval/index.py`, ChromaDB) | [Chưa có] |
| 3 | Đoàn Anh Quân | 2A202602803 | doananhquan2607@gmail.com | Pha 4, 5, 6 — Pipeline Integrator, Corruption & Repair (`phase1.py`, `corruption.py`, `corruption_flow.py`, `reporting.py`) | `report/2A202602803_DoanAnhQuan.md` |

---

## # Cá nhân

### ## TranThuPhuong-2A202602734
- **Vai trò:** Phụ trách Ingestion, làm sạch dữ liệu & Quality Gate (Pha 2).
- **Công việc chi tiết đã hoàn thành:**
  - Thu thập Crossref với retry/backoff và fallback snapshot offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, dedup theo `paper_id`, tính `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Dựng Quality Gate GX 1.x (ephemeral context, 6 expectations) và Freshness SLA trong `src/observability/quality.py`.
- **Điều học được / Đóng góp chính:**
  - [Phương tự điền]

### ## NguyenPhuongNam-2A202602869
- **Vai trò:** Phụ trách Evaluation set & Vector Index (Pha 3).
- **Công việc chi tiết đã hoàn thành:**
  - Sinh test set 10 câu / 5 loại (`summary`, `authors`, `date`, `category`, `multi_hop`) trong `src/evaluation/testset.py`.
  - Mở rộng `LocalEmbeddingIndex` (`build_from_clean`, `semantic_search`, khởi tạo theo tên collection) và alias `test_set_json` trong config.
- **Điều học được / Đóng góp chính:**
  - [Nam tự điền]

### ## DoanAnhQuan-2A202602803
- **Vai trò:** Pipeline Integrator, Corruption & Repair (Pha 4, 5, 6).
- **Công việc chi tiết đã hoàn thành:**
  - Ghép baseline pipeline end-to-end trong `src/pipelines/phase1.py`, dừng pipeline khi Quality Gate fail, sinh `data/reports/phase1_report.md`.
  - Tiêm 6 kịch bản lỗi deterministic (seed 42, giữ nguyên 24 dòng) trong `src/ingestion/corruption.py`, ghi `data/results/corruption_log.json`.
  - Idempotent repair từ raw records và báo cáo đối chiếu 3 trạng thái trong `src/pipelines/corruption_flow.py`, `data/reports/corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Chỉ số chất lượng câu trả lời có thể che lỗi dữ liệu: hit rate giảm 50 pp nhưng judge accuracy chỉ giảm 10 pp, nên phải giám sát cả tầng dữ liệu và retrieval.

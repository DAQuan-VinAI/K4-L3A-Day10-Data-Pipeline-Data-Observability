# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Phương Nam |
| MSSV | 2A202602869 |
| Khóa/Lớp | K4-L3-DAY10 |
| Tên nhóm | nhóm Chót |
| Vai trò chính | RAG, Vector Database & Benchmark Evaluation Set Owner (Pha 3 / CP2, CP3) |
| Repository | https://github.com/DAQuan-VinAI/K4-L3A-Day10-Data-Pipeline-Data-Observability/tree/namnp/02869 |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Benchmark Test Set Generation & Freeze (Pha 3 / CP2) | `src/evaluation/testset.py`: `build_test_set`, `load_or_create_test_set`, `_pick_papers`, `_build_question`, `_item`, class `TestSet` | Clean DataFrame (`data/clean/papers_clean.json`), `Settings` | `data/eval/test_set.json` (10 câu hỏi chuẩn hóa qua 5 loại), class `TestSet` có thuộc tính `.samples` | Hoàn thành và đã xác minh |
| Vector Indexing & ChromaDB Management (Pha 3 / CP2) | `src/retrieval/index.py`: `LocalEmbeddingIndex` (`__init__`, `build`, `load`, `search`, `semantic_search`, `build_from_clean`, `lookup`), `_build_documents`, `_derive_collection_name`, `_manifest_path_for` | Clean DataFrame, embedding model `sentence-transformers/all-MiniLM-L6-v2`, `Settings` | ChromaDB collection `papers-baseline` trong `data/chroma/`, embedding manifest `data/embeddings/papers_embeddings.json` | Hoàn thành và đã xác minh |
| Quản lý đa Collection & Idempotent Indexing (Pha 5 & 6) | `src/retrieval/index.py`: cơ chế `delete_collection` trước khi re-index, tự động ánh xạ output path sang tên collection | Clean DataFrame (corrupted / repaired), `Settings` | Bộ collection cách ly `papers-corrupted`, `papers-repaired` cùng manifest JSON tương ứng | Hoàn thành và đã xác minh |
| Cấu hình tương thích hệ thống (Integration & Compatibility) | `src/core/config.py`: bổ sung property `test_set_json` trên class `Paths` (alias cho `eval_testset`) | Hệ thống cấu hình `Paths` | Đảm bảo tương thích ngược hoàn toàn với test script CP2 của giảng viên | Hoàn thành và đã xác minh |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| --- | --- | --- |
| Khớp nối Data Contract & Schema chuyển giao | Trần Thu Phương (`src/ingestion/cleaning.py`) | Thống nhất cấu trúc 16 cột của `CLEAN_COLUMNS`, đặc biệt là định dạng trường `text_for_embedding` (ghép Title/Authors/Published/Categories/Summary) để làm đầu vào chuẩn cho mô hình nhúng `all-MiniLM-L6-v2`. |
| Cố định Test Set cho đánh giá 3 trạng thái | Đoàn Anh Quân (`src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`) | Thiết kế cơ chế đóng băng `load_or_create_test_set` (không tái sinh câu hỏi khi file đã có) để cả Baseline, Corrupted và Repaired đều chạy trên cùng một bộ câu hỏi có SHA-256 cố định (`0551af7faa84c3d4...`). Nhờ đó, các chỉ số Hit Rate và Token F1 phản ánh chính xác sự cố dữ liệu. |
| Xây dựng cơ chế cô lập Vector Collections | Đoàn Anh Quân (`src/pipelines/corruption_flow.py`) | Hỗ trợ quản lý độc lập 3 collection `papers-baseline`, `papers-corrupted`, `papers-repaired` trong cùng một thư mục ChromaDB mà không bị xung đột hay lẫn lộn vector (ghost vectors). |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Sinh Benchmark Test Set 10 câu qua 5 nhóm nghiệp vụ | `src/evaluation/testset.py`: `build_test_set`, `_pick_papers`, `_build_question` | `data/eval/test_set.json` gồm 10 câu hỏi phủ đủ 5 loại (`summary`, `authors`, `date`, `category`, `multi_hop`, mỗi loại 2 câu), có ground truth text và danh sách ground truth doc IDs | `python -c "from core.config import load_settings; from evaluation.testset import load_or_create_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=load_or_create_test_set(df, s.paths.test_set_json); print(f'Tín hiệu hoàn thành: Test set gồm {len(ts.samples)} câu hỏi')"` → In đúng 10 câu hỏi |
| Đóng băng Test Set (Freeze Evaluation Benchmark) | `src/evaluation/testset.py`: `load_or_create_test_set` | File `data/eval/test_set.json` không bị ghi đè hay thay đổi khi chạy baseline pipeline và corruption flow; SHA-256 giữ nguyên | Hash SHA-256 trước và sau khi chạy pipeline khớp nhau (`0551af7faa84c3d4...`) |
| Xây dựng Vector Index ChromaDB & Manifest cho dữ liệu sạch | `src/retrieval/index.py`: `LocalEmbeddingIndex.build`, `LocalEmbeddingIndex.load` | Collection `papers-baseline` (24 docs, cosine distance) tại `data/chroma/`, manifest tại `data/embeddings/papers_embeddings.json` | `python -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; s=load_settings(); idx=LocalEmbeddingIndex(s, 'papers-baseline'); res=idx.semantic_search('retrieval evaluation', top_k=2); print(f'Tín hiệu hoàn thành: Tìm thấy {len(res)} tài liệu liên quan')"` → In đúng 2 tài liệu |
| Cơ chế xóa và tái lập Index Idempotent (chống Ghost Vectors) | `src/retrieval/index.py`: `build`, `_derive_collection_name` | Tự động xóa collection cũ trước khi nạp mới; hỗ trợ lưu độc lập `papers-corrupted` và `papers-repaired` | Chạy lại `build()` nhiều lần số lượng bản ghi trong collection luôn bằng đúng số dòng của DataFrame (24 docs), không bị tăng số lượng |
| Xử lý tương thích API cho Checkpoint CP2 | `src/core/config.py`: `Paths.test_set_json`, `src/evaluation/testset.py`: `TestSet`, `src/retrieval/index.py`: `semantic_search`, `build_from_clean` | Hệ thống đáp ứng trọn vẹn script chấm tự động của giảng viên mà không làm gãy contract nội bộ của repo | Lệnh kiểm tra CP2 của giảng viên chạy thành công với exit code 0 |

Output cụ thể: `data/eval/test_set.json` tồn tại với đúng 10 câu hỏi chuẩn hóa; ChromaDB lưu trữ thành công 24 vector documents 384 chiều của `papers-baseline`; lệnh Semantic Search mẫu trả về đúng top-2 tài liệu liên quan với khoảng cách cosine chuẩn hóa.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. **Yêu cầu đo lường định lượng trong RAG:** Không thể đánh giá chất lượng hệ thống RAG một cách cảm tính hoặc chỉ nhìn vào câu trả lời sinh ra của LLM. Cần một bộ câu hỏi kiểm thử chuẩn hóa (Golden Evaluation Set) bao quát đầy đủ các chiều kích nghiệp vụ: tra cứu tóm tắt (`summary`), tìm tác giả (`authors`), xác định ngày xuất bản (`date`), phân loại lĩnh vực (`category`) và suy luận kết hợp 2 văn bản (`multi_hop`).
2. **Tính tất định (Deterministic) và độ tin cậy của Test Set:** Bộ câu hỏi phải được sinh hoàn toàn tự động nhưng có thể tái lập 100%. Cần có cơ chế lọc bài thông minh: loại bỏ các bài báo phái sinh (bắt đầu bằng *"Advanced Perspectives on..."*) dễ gây nhiễu, loại bỏ các bài báo có chứa dấu nháy đơn (`'`) trong tiêu đề để tránh làm vỡ biểu thức chính quy (regex) của QA Agent downstream, và bảo đảm mỗi bài báo chỉ xuất hiện tối đa một lần trong bộ câu hỏi đơn mục tiêu.
3. **Đánh chỉ mục ngữ nghĩa (Semantic Indexing) với Dense Vector:** Cần chuyển đổi trường văn bản giàu ngữ cảnh `text_for_embedding` (kết hợp Title, Authors, Published, Categories, Summary) thành các dense vector 384 chiều bằng mô hình `sentence-transformers/all-MiniLM-L6-v2`, sau đó lưu trữ tối ưu trong ChromaDB với không gian khoảng cách Cosine (`{"hnsw": {"space": "cosine"}}`).
4. **Phòng chống Ghost Vectors & Đảm bảo tính Idempotent:** Khi pipeline chạy lại nhiều lần hoặc chuyển đổi giữa các trạng thái (Baseline $\rightarrow$ Corrupted $\rightarrow$ Repaired), nếu không có cơ chế dọn dẹp collection trước khi nạp, ChromaDB sẽ tích lũy vector rác (ghost vectors) hoặc trùng lặp dữ liệu, làm sai lệch nghiêm trọng kết quả retrieval.

### Cách triển khai

#### 1. Module Benchmark Test Set (`src/evaluation/testset.py`)
- **Bộ lọc chọn bài đại diện (`_pick_papers`):**
  Lọc DataFrame sạch theo các tiêu chí khắt khe: trường `authors_joined` và `categories_joined` không được rỗng; tiêu đề không chứa dấu `'`. Tạo cột phụ `is_derivative = title.str.startswith("Advanced Perspectives")` và sắp xếp ưu tiên: bài gốc trước (`is_derivative=False`), ngày xuất bản mới nhất (`published` giảm dần), sau đó đến `paper_id` tăng dần. Điều này đảm bảo danh sách bài được chọn là duy nhất và tất định trên cùng một tập dữ liệu.
- **Xây dựng câu hỏi chuẩn hóa (`_build_question` & `_item`):**
  Sinh 10 câu hỏi với định dạng chuẩn (`q01` đến `q10`), mỗi câu chứa trường `question_type`, câu hỏi `question`, câu trả lời chuẩn `ground_truth` và danh sách định danh tài liệu chuẩn `ground_truth_doc_ids` (chính là `paper_id` dạng DOI):
  - `summary`: Trích xuất câu đầu tiên của abstract bằng `first_sentence(first["summary"])` để câu trả lời súc tích.
  - `authors`: Lấy chuỗi `authors_joined`.
  - `date`: Lấy ngày ISO `published`.
  - `category`: Lấy chuỗi `categories_joined`.
  - `multi_hop`: Ghép 2 bài báo liên tiếp, hỏi tác giả bài thứ nhất và ngày xuất bản của bài thứ hai (`doc_ids = [first["paper_id"], second["paper_id"]]`).
- **Đóng băng Test Set (`load_or_create_test_set`):**
  Nếu file `test_set.json` đã tồn tại và tham số `refresh=False`, hàm sẽ đọc trực tiếp từ đĩa và bọc trong class `TestSet(list)` (có thuộc tính `.samples`), tuyệt đối không sinh lại để bảo toàn tính nhất quán cho cả 3 pha thực nghiệm.

#### 2. Module Vector Indexing (`src/retrieval/index.py`)
- **Tạo tài liệu và định danh duy nhất (`_build_documents`):**
  Mỗi bản ghi được gán `record_id = f"{paper_id}::{index}"`. Việc bổ sung chỉ số dòng `index` vào khóa chính cho phép ChromaDB tiếp nhận cả các bản ghi bị nhân bản (duplicate rows) trong kịch bản tiêm lỗi dữ liệu của Pha 5 mà không bị lỗi primary key collision. Metadata được lưu trọn vẹn 8 trường thông tin để phục vụ QA Agent hiển thị nguồn trích dẫn.
- **Xây dựng chỉ mục an toàn (`LocalEmbeddingIndex.build`):**
  Khởi tạo `chromadb.PersistentClient`. Thực hiện cơ chế xóa an toàn `client.delete_collection(name=collection_name)` trong khối `try/except` trước khi gọi `client.create_collection` với metric `cosine`. Nhúng toàn bộ tài liệu qua `MiniLMEmbeddings` và nạp đồng thời `ids`, `embeddings`, `documents`, `metadatas`. Xuất manifest tương ứng ra thư mục `data/embeddings/`.
- **Khởi tạo linh hoạt & Semantic Search (`search`, `semantic_search`, `build_from_clean`):**
  Cho phép khởi tạo nhanh `LocalEmbeddingIndex(settings, collection_name=...)` mà không bắt buộc truyền trước danh sách documents (hàm tự tìm đọc manifest JSON đã lưu). Hàm `search` chuyển hóa câu truy vấn thành embedding vector, truy vấn top-k kết quả gần nhất, tính điểm tương đồng `score = max(0.0, 1.0 - distance)` và đóng gói vào danh sách `SearchResult`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input nhận vào | Clean DataFrame (16 cột theo chuẩn `CLEAN_COLUMNS`), `Settings`, mô hình nhúng `all-MiniLM-L6-v2` |
| Output bàn giao | `data/eval/test_set.json` (10 câu hỏi benchmark kèm ground truth doc IDs); Chroma collections trong `data/chroma/`; Manifest files trong `data/embeddings/*.json` |
| Module phụ thuộc | `core.config.Settings`, `core.utils` (`read_json`, `write_json`, `first_sentence`, `safe_slug`), `retrieval.embeddings.MiniLMEmbeddings` |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, `evaluation.qa` (trả lời câu hỏi), `evaluation.metrics` (tính Hit Rate, Token F1), `observability.reporting` |
| Điều kiện lỗi cần xử lý | Số dòng dữ liệu nhỏ hơn `MIN_DOCUMENTS = 5` $\rightarrow$ raise `ValueError`; không đủ paper hợp lệ $\rightarrow$ báo lỗi thiếu bài; collection chưa build khi nạp $\rightarrow$ trả về danh sách rỗng an toàn |

### Cách xác minh

Các câu lệnh kiểm tra độc lập tại Checkpoint CP2:

```bash
# 1. Kiểm tra sinh và nạp Benchmark Test Set:
uv run python -c "from core.config import load_settings; from evaluation.testset import load_or_create_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=load_or_create_test_set(df, s.paths.test_set_json); print(f'Tín hiệu hoàn thành: Test set gồm {len(ts.samples)} câu hỏi')"

# 2. Kiểm tra khởi tạo và Semantic Search trên ChromaDB:
uv run python -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; s=load_settings(); idx=LocalEmbeddingIndex(s, 'papers-baseline'); res=idx.semantic_search('retrieval evaluation', top_k=2); print(f'Tín hiệu hoàn thành: Tìm thấy {len(res)} tài liệu liên quan')"
```

- **Kết quả mong đợi:**
  - Lệnh 1: Console in ra chuỗi `Tín hiệu hoàn thành: Test set gồm 10 câu hỏi`.
  - Lệnh 2: Console in ra chuỗi `Tín hiệu hoàn thành: Tìm thấy 2 tài liệu liên quan`.
- **Kết quả thực tế:** Cả hai lệnh thực thi hoàn hảo, trả về đúng số lượng 10 câu hỏi và 2 tài liệu truy vấn có điểm tương đồng cao nhất.
- **Artifacts kiểm chứng:** `data/eval/test_set.json`, `data/chroma/`, `data/embeddings/papers_embeddings.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp thiết kế bộ đánh giá benchmark (`test_set.json`) cho hệ thống RAG Agent.
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (Dynamic LLM Generation):* Dùng một mô hình LLM bên ngoài để đọc các bài báo và tự động sinh ngẫu nhiên các câu hỏi mở mỗi lần pipeline khởi chạy.
  - *Phương án 2 (Deterministic Rule-Based & Frozen Test Set):* Thiết lập bộ lọc bài tất định dựa trên metadata có sẵn, sinh câu hỏi theo 5 nhóm nghiệp vụ cố định (`summary`, `authors`, `date`, `category`, `multi_hop`), gán cứng `ground_truth_doc_ids` (mã DOI) và **đóng băng (freeze)** file JSON sau lần sinh đầu tiên.
- **Phương án đã chọn:** Phương án 2.
- **Lý do kỹ thuật:**
  1. *Tính hợp lệ và khách quan của thực nghiệm khoa học (Scientific Validity):* Mục tiêu tối thượng của bài lab là đo lường mức độ suy giảm khi dữ liệu bị lỗi (Pha 5) và khả năng hồi phục (Pha 6). Muốn so sánh công bằng giữa Baseline vs Corrupted vs Repaired thì "đề thi" (Test Set) bắt buộc phải là một hằng số bất biến. Nếu mỗi lần chạy đề thi lại đổi, sự sụt giảm của Hit Rate hay Token F1 sẽ bị nhiễu loạn do câu hỏi khác nhau chứ không phản ánh được tác động thực chất của dữ liệu bẩn.
  2. *Loại bỏ sự phụ thuộc vào mạng và Rate Limit:* Không tốn chi phí gọi LLM API, không lo gặp lỗi `429 Too Many Requests` khi chạy chấm điểm nhiều lần trong phòng lab.
  3. *Ground-truth Document IDs chính xác tuyệt đối:* Việc gắn mã DOI của tài liệu gốc vào `ground_truth_doc_ids` cho phép tính toán chỉ số `retrieval_hit_rate` hoàn toàn bằng toán học và logic (tài liệu đúng có nằm trong top-4 retrieved context hay không), không bị phụ thuộc vào phán đoán chủ quan của LLM Judge.
- **Bằng chứng quyết định phù hợp:** Trong Pha 5, khi Quân thực hiện kịch bản `drop_latest_records` (xóa 5 bài báo mới nhất), do Test Set được cố định và các câu hỏi từ q01 đến q05 nhắm thẳng vào các bài này, chỉ số `retrieval_hit_rate` lập tức rơi thẳng đứng từ **1.000 xuống đúng 0.500** (mất chính xác 5/10 câu). Đây chính là bằng chứng định lượng rõ ràng nhất chứng minh dữ liệu bị hư hại.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi chạy câu lệnh kiểm tra tự động của Checkpoint CP2 do giảng viên cung cấp, hệ thống liên tiếp gặp các lỗi:
  1. `AttributeError: 'Paths' object has no attribute 'test_set_json'`
  2. `AttributeError: 'list' object has no attribute 'samples'` khi gọi thuộc tính `ts.samples`
  3. `TypeError: LocalEmbeddingIndex.__init__() missing 2 required positional arguments: 'documents' and 'persist_path'` khi gọi cú pháp khởi tạo nhanh `LocalEmbeddingIndex(s, 'papers-baseline')`
  4. `AttributeError: 'LocalEmbeddingIndex' object has no attribute 'semantic_search'`
- **Lệnh tái hiện:** Chạy trực tiếp script kiểm tra CP2 trên starter code ban đầu:
  ```bash
  python -c "from core.config import load_settings; from evaluation.testset import load_or_create_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=load_or_create_test_set(df, s.paths.test_set_json); print(f'Tín hiệu hoàn thành: Test set gồm {len(ts.samples)} câu hỏi')"
  ```
- **Nguyên nhân gốc:** Có sự không đồng nhất giữa interface của starter code và script kiểm tra tự động của giảng viên:
  - Trong cấu hình `Paths`, đường dẫn được đặt tên là `eval_testset` chứ không có `test_set_json`.
  - Hàm `build_test_set` ban đầu trả về `list` thông thường nên không có thuộc tính `.samples`.
  - Class `LocalEmbeddingIndex` ban đầu bắt buộc truyền đủ 4 tham số vị trí (`settings`, `collection_name`, `documents`, `persist_path`) và chỉ có phương thức `search`, không có `semantic_search` hay `build_from_clean`.
- **Cách xử lý:** Triển khai giải pháp tương thích ngược (Backward Compatibility) mà không làm gãy code hiện có của nhóm:
  1. Trong `src/core/config.py`: bổ sung `@property def test_set_json(self) -> Path: return self.eval_testset` vào class `Paths`.
  2. Trong `src/evaluation/testset.py`: định nghĩa `class TestSet(list)` kế thừa từ `list` và cung cấp `@property def samples(self) -> list[dict[str, Any]]: return list(self)`.
  3. Trong `src/retrieval/index.py`: gán giá trị mặc định `None` cho `documents` và `persist_path`. Nếu `documents is None`, hàm tự động nạp documents từ manifest JSON tương ứng qua `_manifest_path_for`. Đồng thời bổ sung phương thức `build_from_clean()` và alias `semantic_search = search`.
- **Cách xác minh sau khi sửa:** Cả script kiểm tra CP2 của giảng viên lẫn kịch bản chạy chính `python script/run_phase1.py` và `python script/run_corruption_flow.py` đều thực thi trơn tru với exit code 0.
- **Bài học rút ra:** Khi làm việc trong các dự án phần mềm đa module hoặc tích hợp hệ thống kiểm thử ngoài, cần áp dụng triệt để nguyên lý Robustness Principle (*"Be conservative in what you send, be liberal in what you accept"*). Việc thiết kế API phòng thủ linh hoạt và tương thích ngược giúp hệ thống vận hành bền bỉ trước các caller khác nhau.

## 7. Hiểu biết về luồng end-to-end

1. **Từ Dữ liệu thô đến Không gian Vector:** Dữ liệu bắt đầu từ API Crossref (hoặc snapshot offline lưu tại `data/raw/crossref_response.json`). Module ingestion parse dữ liệu thành các `PaperRecord` nguyên bản. Module cleaning chuẩn hóa văn bản, gộp các trường thành chuỗi giàu ngữ nghĩa `text_for_embedding`. Dữ liệu này bắt buộc phải vượt qua chốt kiểm dịch Great Expectations 1.x và Freshness SLA trước khi được mô hình `all-MiniLM-L6-v2` nhúng thành dense vector và lưu vào ChromaDB.
2. **Cơ chế Benchmark đánh giá RAG:** Chất lượng của hệ thống RAG không chỉ được đo ở tầng sinh câu trả lời mà phải đo ngay từ tầng truy xuất tài liệu. Mỗi câu hỏi trong `test_set.json` đều gắn danh sách `ground_truth_doc_ids`. Hệ thống đo lường 3 chỉ số then chốt:
   - `retrieval_hit_rate`: Tỷ lệ câu hỏi mà ít nhất một tài liệu nguồn hợp lệ xuất hiện trong top-4 retrieved context.
   - `mean_token_f1`: Mức độ trùng lặp từ vựng giữa câu trả lời sinh ra và `ground_truth`.
   - `judge_accuracy` & `mean_judge_score`: Điểm đánh giá độc lập của LLM Judge (chấm điểm 1–5).
3. **Mối quan hệ giữa Quality Gate và Freshness SLA:** Quality Gate kiểm định cấu trúc và tính hợp lệ vi mô của dữ liệu tại một thời điểm (schema, không null, tính duy nhất của ID, độ dài chuỗi). Freshness SLA kiểm định tính cập nhật vĩ mô theo dòng thời gian (tỷ lệ bài quá 180 ngày). Một tập dữ liệu có thể pass toàn bộ kiểm tra cấu trúc nhưng vẫn bị cảnh báo STALE nếu dữ liệu không được làm mới định kỳ.
4. **Ý nghĩa sống còn của việc Đóng băng Test Set:** Nếu mỗi lần chạy pipeline lại sinh lại bộ test set mới thì mọi phép so sánh đều trở nên vô nghĩa, vì metric thay đổi do câu hỏi thay đổi chứ không phải do dữ liệu. Giữ cố định test set là điều kiện tiên quyết để định lượng chính xác tác động của 6 kịch bản tiêm lỗi dữ liệu.
5. **Bản chất của Idempotent Repair:** Phục hồi không phải là "vá tay" từng ô dữ liệu bẩn. Phục hồi an toàn là tái tạo toàn bộ dữ liệu từ nguồn sự thật bất biến (Immutable Raw Records `data/raw/crossref_records.json`), chạy lại quy trình làm sạch chuẩn và xóa/tạo mới lại collection trên ChromaDB. Tính Idempotent bảo đảm dù quy trình phục hồi có chạy lại bao nhiêu lần thì kết quả đầu ra luôn đồng nhất tuyệt đối.

## 8. Phân tích kết quả

### Bảng chỉ số đối chiếu 3 trạng thái

| Metric / Tín hiệu kiểm tra | Baseline (Dữ liệu sạch) | Corrupted (Dữ liệu lỗi) | Repaired (Sau phục hồi) | Nhận xét dưới góc độ Vector Index & Test Set |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | **1.000** (100%) | **0.500** (50.0%) | **1.000** (100%) | Giảm đúng 50 pp do 5 bài mới nhất bị xóa là ground truth của q01–q05 |
| `mean_token_f1` | **0.933** | **0.712** | **0.933** | Giảm ít hơn Hit Rate vì các bài phái sinh có cùng tên tác giả |
| `judge_accuracy` | **0.800** (80%) | **0.700** (70.0%) | **0.800** (80%) | Judge chỉ giảm 10 pp, bộc lộ rõ hiện tượng Silent Failure |
| `mean_judge_score` | **4.60** | **4.20** | **4.60** | LLM Judge vẫn chấm điểm cao dù truy xuất sai tài liệu |
| Data Quality Gate (GX 1.x) | **6/6 Pass** | **4/6 Fail** | **6/6 Pass** | Phát hiện lỗi trùng `paper_id` và `summary` bị xóa rỗng |
| Freshness Status | **Fresh** (4.2% stale) | **Stale** (37.5% stale) | **Fresh** (4.2% stale) | Phát hiện 9/24 bài bị lùi ngày quá hạn 180 ngày |

### Phân tích chuyên sâu từ góc độ RAG & Vector Search

#### 1. Vì sao Retrieval Hit Rate giảm chính xác từ 1.000 xuống 0.500?
Trong kịch bản tiêm lỗi `drop_latest_records`, nhóm đã loại bỏ 20% bài báo mới nhất (5 dòng). Do thuật toán sinh test set `_pick_papers` ưu tiên các bài báo mới nhất có đầy đủ metadata, toàn bộ 5 bài bị xóa này chính là tài liệu ground truth phục vụ trả lời cho các câu hỏi từ **q01 đến q05**. Khi 5 bài này biến mất khỏi ChromaDB, vector search hoàn toàn không thể tìm thấy tài liệu gốc trong top-4 retrieved context, dẫn đến 5/10 câu bị trượt hit rate ngay lập tức.

#### 2. Hiện tượng Silent Failure & Điểm mù nguy hiểm của LLM Judge:
Điều bất ngờ và sâu sắc nhất nằm ở độ lệch pha giữa **Retrieval Hit Rate** (giảm 50 pp) và **LLM Judge Accuracy** (chỉ giảm 10 pp, từ 80% xuống 70%):
- **Nguyên nhân trong không gian Vector:** Trong tập dữ liệu Crossref thu thập được, có tồn tại các cặp bài báo phái sinh (bản mở rộng mang tiêu đề *"Advanced Perspectives on..."*) có cùng tác giả và cùng danh mục nghiên cứu với các bài gốc. Khi bài gốc bị xóa khỏi ChromaDB, câu truy vấn ngữ nghĩa tìm thấy bài phái sinh gần nhất và đưa vào context.
- **Biểu hiện Silent Failure:** 
  - Tại câu **q03** và **q04** (hỏi về tác giả), hệ thống lấy nhầm tài liệu `...3671816` và `...3671819` thay vì `...3671804` và `...3671807`. Nhưng vì bài phái sinh có cùng tác giả (*"Bao Do, Linh Ngo"* và *"Kien Duong, Vy Ly"*), QA Agent vẫn trả lời đúng tên tác giả và LLM Judge vẫn chấm **5/5 điểm**!
  - Nghiêm trọng hơn, tại câu **q01**, tài liệu phái sinh bị dính thêm kịch bản lỗi `blank_summary`, khiến QA Agent trả về câu trả lời rỗng `(empty)`. Tuy nhiên, LLM Judge vẫn chấm câu trả lời này đạt **5/5 điểm**!
- **Kết luận:** Đây là bằng chứng thực nghiệm rõ ràng nhất cho thấy: **Nếu chỉ quan sát chất lượng câu trả lời ở tầng LLM (Answer Quality / Judge Score), toàn bộ đội ngũ kỹ thuật sẽ bị đánh lừa rằng hệ thống vẫn chạy tốt.** Chỉ có việc giám sát `retrieval_hit_rate` dựa trên `ground_truth_doc_ids` ở tầng Vector Database mới vạch trần được sự cố dữ liệu ngầm này.

#### 3. Kết quả phục hồi hoàn hảo (Repaired):
Sau khi chạy luồng `repair_from_raw`, quy trình làm sạch tái tạo lại 24 dòng dữ liệu chuẩn từ snapshot gốc, xóa sạch collection lỗi và re-index lại vào ChromaDB `papers-repaired`. Toàn bộ 10 câu hỏi trong test set tìm lại đúng tài liệu nguồn ban đầu, đưa `retrieval_hit_rate` trở lại mức **1.000** và `mean_token_f1` trở lại **0.933**, minh chứng cho năng lực tự phục hồi tự động của kiến trúc Idempotent Pipeline.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Benchmark Test Set có Ground-truth Document IDs là chốt chặn quan trọng nhất của RAG:** Không thể kiểm thử hệ thống RAG bằng các câu hỏi ngẫu nhiên không có căn cứ. Phải gắn chặt từng câu hỏi với mã định danh tài liệu chuẩn để đo lường năng lực Retrieval độc lập với năng lực Generation.
2. **Quản lý vòng đời Vector Index phải mang tính Idempotent:** Khi cập nhật dữ liệu, việc re-index phải đi kèm cơ chế dọn dẹp triệt để vector cũ (phân tách rõ các collection `papers-baseline`, `papers-corrupted`, `papers-repaired`). Nếu không quản lý tốt, hiện tượng ghost vectors sẽ làm sai lệch hoàn toàn kết quả tìm kiếm ngữ nghĩa.
3. **Cảnh giác tối đa với hiện tượng Silent Failure:** Đánh giá RAG bằng LLM Judge có thể tạo ra cảm giác an toàn giả tạo (False Sense of Security). Dữ liệu rác hoặc dữ liệu phái sinh có thể làm sai lệch căn cứ thông tin nhưng LLM vẫn sinh câu trả lời nghe rất thuyết phục. Data Observability ở tầng dữ liệu và tầng retrieval là bắt buộc đối với mọi hệ thống AI Production.

### Hướng cải thiện nếu có thêm thời gian

1. **Mở rộng quy mô và độ sâu của Benchmark Test Set:** Nâng quy mô bộ test từ 10 câu lên 50–100 câu hỏi. Tích hợp thêm các bộ chỉ số nâng cao của khung đánh giá Ragas (như *Faithfulness*, *Answer Relevance*, *Context Precision*) bằng cách thiết lập cờ `RUN_RAGAS=1` chạy bất đồng bộ với quota API lớn hơn.
2. **Tối ưu hóa bộ tìm kiếm bằng Hybrid Search:** Kết hợp Dense Vector Retrieval (ChromaDB + `all-MiniLM-L6-v2`) với Sparse Keyword Search (BM25 hoặc SPLADE) và Reciprocal Rank Fusion (RRF). Điều này sẽ giúp cải thiện đáng kể độ chính xác khi người dùng tra cứu các thực thể metadata chính xác (như mã số DOI, tên tác giả hiếm, hoặc ngày tháng xuất bản cụ thể).

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc, kết quả thực tế và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end từ Ingestion, Cleaning, Quality Gate, Indexing đến Evaluation và Repair.
- [x] Mọi kết luận và số liệu trong báo cáo đều có artifact và log kiểm chứng trên repository.
- [x] Tôi không ghi "đã chạy thành công" cho bất kỳ phần việc nào chưa được kiểm chứng.
- [x] Báo cáo không chứa file `.env`, API key, token hoặc secret.
- [x] Báo cáo này là sản phẩm làm việc cá nhân độc lập dựa trên phần phân công, không sao chép nguyên văn từ báo cáo của thành viên khác.

**Họ và tên:** Nguyễn Phương Nam  
**Ngày xác nhận:** 2026-09-25

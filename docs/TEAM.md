# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** Nhóm 1PROMPT
- **Mã Nhóm / Lớp:** K4 - L3B
- **Tên Repository Nộp Bài:** K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability
- **Repository URL:** https://github.com/conanWinner/K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability

---

## 1. Danh Sách Thành Viên & Phân Công Trách Nhiệm

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Đoàn Quang Thắng | 2A202602395 | doanquangthangqt04@gmail.com | Trưởng nhóm / Data Model & Evaluation Set Owner (`src/ingestion/cleaning.py`, `src/evaluation/testset.py`, Orchestration support) | [individual_2A202602395_DoanQuangThang.md](../report/individual_2A202602395_DoanQuangThang.md) |
| 2 | Phạm Minh Hiếu | 2A202602630 | danaccclonemi2@gmail.com | Source Owner (Raw Data Ingestion & Data Lineage: `src/ingestion/crossref.py`, Retry & Fallback mechanism) | [individual_2A202602630_PhamMinhHieu.md](../report/individual_2A202602630_PhamMinhHieu.md) |
| 3 | Đỗ Việt Hoàng | 2A202602882 | dohoang021203@gmail.com | Corruption & Integration Owner (`src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, ChromaDB Index) | [individual_2A202602882_ĐỖ VIỆT HOÀNG.md](../report/individual_2A202602882_ĐỖ%20VIỆT%20HOÀNG.md) |
| 4 | Kiều Đình Đoàn | 2A202602936 | he170794kieudinhdoan@gmail.com | Observability Owner (Data Quality Gate GX 1.x & Freshness SLA: `src/observability/quality.py`, `src/observability/reporting.py`) | [individual_2A202602936_KieuDinhDoan.md](../report/individual_2A202602936_KieuDinhDoan.md) |

---

## 2. Phần Tự Khai Báo Đóng Góp Chi Tiết Từng Thành Viên

### 2.1. Đoàn Quang Thắng - 2A202602395
- **Vai trò:** Trưởng nhóm, Data Model & Evaluation Set Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết kế và triển khai logic làm sạch dữ liệu trong `src/ingestion/cleaning.py`: bóc tách thẻ JATS XML (`<jats:p>`), chuẩn hóa khoảng trắng thừa, lowercase `paper_id` và khử trùng lặp bản ghi.
  - Xây dựng mô hình cấu trúc hóa dữ liệu văn bản `text_for_embedding` gồm 5 trường có nhãn (`Title`, `Authors`, `Categories`, `Published`, `Summary`) giúp tối ưu không gian vector ngữ nghĩa cho đa chiều truy vấn.
  - Tính toán trường dẫn xuất thời gian `age_days` làm căn cứ trực tiếp cho kiểm định Freshness SLA.
  - Thiết kế bộ đánh giá chuẩn hóa bất biến `data/eval/test_set.json` gồm 10 câu hỏi rải đều 4 khía cạnh nghiệp vụ (`summary`, `authors`, `date`, `categories`) kèm `ground_truth_doc_ids` chính xác.
  - Điều phối nhóm, rà soát tính nhất quán giữa các artifact kết quả và hoàn thiện báo cáo chung.
- **Điều học được / Đóng góp chính:**
  - Nắm vững nguyên lý bất biến (immutability) trong đánh giá RAG: bộ test set chuẩn là thước đo duy nhất để cô lập và so sánh khách quan tác động của chất lượng dữ liệu giữa các pha.

### 2.2. Phạm Minh Hiếu - 2A202602630
- **Vai trò:** Source Owner (Raw Data Ingestion & Data Lineage).
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref REST API trong `src/ingestion/crossref.py`: parse payload thô thành danh sách đối tượng `PaperRecord` gồm 11 trường thông tin.
  - Thiết lập cơ chế tải có khả năng chịu lỗi cao: retry tối đa 3 lần với exponential backoff cho mã lỗi mạng `429 Too Many Requests` và `5xx`.
  - Triển khai cơ chế Offline Fallback an toàn: ưu tiên đọc local snapshot `data/raw/crossref_response.json` khi mạng không ổn định hoặc chưa bật cờ `REFRESH_SOURCE=1`.
  - Đảm bảo trọn vẹn Data Lineage 2 tầng: lưu giữ payload nguyên bản `crossref_response.json` và bản ghi đã trích xuất `crossref_records.json` làm nguồn tin cậy tuyệt đối cho luồng phục hồi dữ liệu (Idempotent Repair).
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc vai trò của raw data immutability trong kiến trúc dữ liệu: raw snapshot bất biến là phòng tuyến cuối cùng để phục hồi hệ thống khi serving layer bị nhiễm bẩn dữ liệu.

### 2.3. Đỗ Việt Hoàng - 2A202602882
- **Vai trò:** Corruption & Pipeline Integration Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng bộ công cụ làm bẩn dữ liệu tổng hợp (Synthetic Data Corruption Suite) trong `src/ingestion/corruption.py` với 6 kịch bản lỗi: `drop_latest_records`, `blank_summary`, `inject_noise`, `truncate_title`, `stale_date`, `duplicate_rows` với `seed=42`.
  - Ghi nhật ký chi tiết các biến đổi dữ liệu ra `data/results/corruption_log.json`.
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2` và nạp chỉ mục vào 3 ChromaDB collection riêng biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Tích hợp và điều phối 2 luồng thực thi chính: `src/pipelines/phase1.py` (chạy baseline end-to-end) và `src/pipelines/corruption_flow.py` (chạy quy trình corrupt → evaluate → repair → verify).
- **Điều học được / Đóng góp chính:**
  - Trực tiếp quan sát và chứng minh hiện tượng Silent Failure trong RAG: dữ liệu bị hỏng không làm crash ứng dụng nhưng âm thầm kéo tụt Hit Rate từ 1.00 xuống 0.80 và làm sai lệch câu trả lời thời gian.

### 2.4. Kiều Đình Đoàn - 2A202602936
- **Vai trò:** Observability & Quality Assurance Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate tự động theo chuẩn **Great Expectations 1.x** (sử dụng fluent ephemeral context API) trong `src/observability/quality.py`.
  - Định nghĩa 6 expectations cốt lõi kiểm soát toàn diện schema: số lượng dòng bảng (`20-30`), giá trị không null (`paper_id`, `title`), tính duy nhất (`paper_id`), và độ dài chuỗi tối thiểu (`title >= 8`, `summary >= 50`).
  - Thiết lập cơ chế giám sát Freshness SLA: phát hiện và cảnh báo vi phạm khi tỷ lệ bài báo quá hạn (`age_days > 180`) vượt ngưỡng 25%.
  - Xây dựng module xuất báo cáo định lượng tự động trong `src/observability/reporting.py`: sinh bảng đối chiếu 3 trạng thái tại `data/reports/corruption_report.md` và `data/reports/phase1_report.md`.
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ sự khác biệt giữa Data Quality (kiểm soát cấu trúc, tính toàn vẹn cú pháp) và Freshness Monitoring (kiểm soát ngữ nghĩa thời gian), từ đó thiết lập chốt chặn kiểm dịch ngăn chặn triệt để dữ liệu lỗi đi vào vector store.

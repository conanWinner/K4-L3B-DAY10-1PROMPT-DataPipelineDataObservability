# Individual Role Reports Hub — Day 10: Data Pipeline & Data Observability

- **Tên Nhóm:** Nhóm 1PROMPT
- **Lớp / Khóa:** K4 - L3B
- **Tên Repository:** `K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability`
- **Repository URL:** https://github.com/conanWinner/K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability
- **Ngày hoàn thành:** 2026-09-26

---

## Danh Mục Báo Cáo Vai Trò Cá Nhân (Individual Reports)

Theo quy định tại [report/README.md](README.md) và [docs/RUBRIC.md](../docs/RUBRIC.md), mỗi thành viên trong nhóm hoàn thành một bản báo cáo cá nhân độc lập phản ánh đúng vai trò, phân công sở hữu module, các quyết định kỹ thuật, xử lý sự cố và phân tích số liệu thực nghiệm.

Dưới đây là danh sách báo cáo chi tiết của từng thành viên:

| STT | Họ và tên | MSSV | Vai trò chính | Module sở hữu | Báo cáo chi tiết |
|:---:|---|---|---|---|---|
| **1** | **Đoàn Quang Thắng** | `2A202602395` | Trưởng nhóm / Data Model & Evaluation Set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` | [📄 Xem Báo Cáo Thắng](individual_2A202602395_DoanQuangThang.md) |
| **2** | **Phạm Minh Hiếu** | `2A202602630` | Source Owner (Raw Ingestion & Lineage) | `src/ingestion/crossref.py`, `data/raw/` | [📄 Xem Báo Cáo Hiếu](individual_2A202602630_PhamMinhHieu.md) |
| **3** | **Đỗ Việt Hoàng** | `2A202602882` | Corruption & Integration Owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | [📄 Xem Báo Cáo Hoàng](individual_2A202602882_%C4%90%E1%BB%96%20VI%E1%BB%86T%20HO%C3%80NG.md) |
| **4** | **Kiều Đình Đoàn** | `2A202602936` | Observability Owner (GX 1.x & Freshness SLA) | `src/observability/quality.py`, `src/observability/reporting.py` | [📄 Xem Báo Cáo Đoàn](individual_2A202602936_KieuDinhDoan.md) |

---

## Tóm Tắt Đóng Góp & Trách Nhiệm Phân Công

### 1. Đoàn Quang Thắng (2A202602395)
- **Deliverables:**
  - Logic làm sạch văn bản, loại bỏ triệt để thẻ JATS XML (`<jats:p>`), chuẩn hóa khoảng trắng thừa trong `src/ingestion/cleaning.py`.
  - Cấu trúc hóa chuỗi 5 phần `text_for_embedding` (Title, Authors, Categories, Published, Summary).
  - Tính toán trường dẫn xuất `age_days` phục vụ Freshness SLA.
  - Xây dựng bộ test set 10 câu hỏi chuẩn hóa đa khía cạnh lưu tại `data/eval/test_set.json` (bất biến qua cả 3 trạng thái).
- **Chi tiết:** [individual_2A202602395_DoanQuangThang.md](individual_2A202602395_DoanQuangThang.md)

### 2. Phạm Minh Hiếu (2A202602630)
- **Deliverables:**
  - Thu thập Crossref REST API và cơ chế Retry có Exponential Backoff cho mã lỗi `429` / `5xx` trong `src/ingestion/crossref.py`.
  - Cơ chế Offline Fallback tự động đọc snapshot `data/raw/crossref_response.json` khi mạng không sẵn sàng.
  - Bảo toàn Data Lineage 2 tầng: payload gốc và records đã parse (`data/raw/crossref_records.json`).
  - Nạp lại raw records phục vụ luồng Idempotent Repair.
- **Chi tiết:** [individual_2A202602630_PhamMinhHieu.md](individual_2A202602630_PhamMinhHieu.md)

### 3. Đỗ Việt Hoàng (2A202602882)
- **Deliverables:**
  - Triển khai 6 kịch bản làm bẩn dữ liệu (Synthetic Data Corruption Suite) trong `src/ingestion/corruption.py` với `seed=42`.
  - Ghi nhật ký chi tiết các biến đổi ra `data/results/corruption_log.json`.
  - Quản lý mô hình vector `all-MiniLM-L6-v2` và 3 ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Tích hợp và điều phối thực thi `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
- **Chi tiết:** [individual_2A202602882_ĐỖ VIỆT HOÀNG.md](individual_2A202602882_%C4%90%E1%BB%96%20VI%E1%BB%86T%20HO%C3%80NG.md)

### 4. Kiều Đình Đoàn (2A202602936)
- **Deliverables:**
  - Xây dựng Quality Gate theo chuẩn mới **Great Expectations 1.x** (fluent ephemeral context API) trong `src/observability/quality.py`.
  - Cấu hình 6 expectations kiểm soát quy mô dòng, NOT NULL, tính duy nhất khóa chính và độ dài chuỗi tối thiểu.
  - Đo lường và giám sát Freshness SLA (cảnh báo STALE khi tỷ lệ bài quá 180 ngày vượt 25%).
  - Tự động sinh báo cáo đối chiếu định lượng 3 trạng thái tại `data/reports/corruption_report.md` và `data/reports/phase1_report.md`.
- **Chi tiết:** [individual_2A202602936_KieuDinhDoan.md](individual_2A202602936_KieuDinhDoan.md)

---

## Bảng Đối Chiếu Số Liệu Thực Nghiệm Thống Nhất

Toàn bộ 4 thành viên và báo cáo nhóm [group_report.md](group_report.md) thống nhất dựa trên cùng kết quả thực thi thực tế:

| Chỉ số / Signal | Trạng thái Baseline | Trạng thái Corrupted | Trạng thái Repaired | Tác động Corruption | Mức phục hồi |
|---|:---:|:---:|:---:|:---:|:---:|
| **Retrieval Hit Rate** | `1.0000` | `0.8000` | `1.0000` | -0.2000 | 100% |
| **Mean Token F1** | `1.0000` | `0.8000` | `1.0000` | -0.2000 | 100% |
| **Judge Accuracy** | `1.0000` | `0.8000` | `1.0000` | -0.2000 | 100% |
| **Mean Judge Score (1-5)** | `5.0000` | `4.2000` | `5.0000` | -0.8000 | 100% |
| **Data Quality Gate (GX 1.x)** | **PASS** (6/6) | **FAIL** (3/6) | **PASS** (6/6) | 3 vi phạm | 100% |
| **Freshness SLA** | **FRESH** (4.17%) | **STALE** (39.13%) | **FRESH** (4.17%) | +34.96% stale | 100% |
| **Số lượng bản ghi** | 24 dòng | 23 dòng | 24 dòng | -1 dòng ròng | 100% |

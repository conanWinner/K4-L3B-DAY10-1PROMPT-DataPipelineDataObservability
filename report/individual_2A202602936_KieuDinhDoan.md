# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Kiều Đình Đoàn             |
| MSSV               | 2A202602936                |
| Khóa/Lớp         | K4 - L3B                   |
| Tên nhóm         | Nhóm 1PROMPT               |
| Vai trò chính    | Observability Owner (Data Quality Gate & Freshness SLA: `src/observability/quality.py`, `src/observability/reporting.py`) |
| Repository         | https://github.com/conanWinner/K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Great Expectations 1.x Quality Gate | `src/observability/quality.py`: `_build_suite()`, `run_data_quality_checks()` | Clean/Corrupted/Repaired DataFrame, `Settings` | `data/quality/{baseline,corrupted,repaired}_quality_report.json` với 6 expectations chuẩn hóa | Hoàn thành |
| Freshness SLA Monitoring | `src/observability/quality.py`: `_freshness_summary()`, `build_freshness_report()` | DataFrame (cột `age_days`, `published`), `threshold_days=180`, `max_stale_ratio=0.25` | `data/quality/{freshness,corrupted_freshness,repaired_freshness}_report.json` | Hoàn thành |
| Automated Markdown Reporting | `src/observability/reporting.py`: `generate_phase1_report()`, `generate_corruption_report()`, `format_comparison_table()` | Metrics JSON, Quality report JSON, Freshness payload | `data/reports/phase1_report.md` và `data/reports/corruption_report.md` có bảng đối chiếu 3 trạng thái | Hoàn thành |

Phần việc của tôi tiếp nhận DataFrame từ module Cleaning (do Đoàn Quang Thắng phụ trách) và bàn giao chốt kiểm định chất lượng (Gate Pass/Fail) cho:
1. Module Vector Indexing & Orchestration (do Đỗ Việt Hoàng phụ trách): chỉ cho phép index và serving dữ liệu khi Quality Gate đạt `success: true`.
2. Hệ thống báo cáo toàn diện của dự án: tự động tổng hợp số liệu đo lường, phân tích suy thoái và phục hồi dữ liệu.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp chốt chặn Quality Gate vào luồng Repair | Đỗ Việt Hoàng / `src/pipelines/corruption_flow.py` | Bổ sung logic `if not repaired_quality["success"]: raise SystemExit(...)` để ngăn chặn triệt để dữ liệu lỗi quay lại serving layer |
| Thống nhất chuẩn trường thời gian cho Freshness SLA | Đoàn Quang Thắng / `src/ingestion/cleaning.py` | Xác định rõ ràng kiểu dữ liệu và công thức tính `age_days = (run_date.date() - published).days` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng Suite 6 Expectations theo Great Expectations 1.x fluent API | `src/observability/quality.py`: `_build_suite()` | Suite chuẩn: Table row count, Not null (id, title), Unique id, Min length (title, summary) | Chạy kiểm thử trên baseline DataFrame đạt 6/6 Pass |
| Thiết lập Ephemeral Context GX 1.x không phụ thuộc file hệ thống | `src/observability/quality.py`: `run_data_quality_checks()` | Khởi tạo in-memory context qua `gx.get_context(mode="ephemeral")`, add pandas data source và batch definition | Chạy không cần thư mục `gx/` trên đĩa, chạy mượt mà trên CI/CD và máy chấm thi |
| Đo lường Freshness SLA tự động | `src/observability/quality.py`: `_freshness_summary()` | Tính chính xác `stale_ratio = (age_days > 180) / total_rows`, so sánh với ngưỡng `0.25` | Baseline: 4.17% (Pass); Corrupted: 39.13% (Fail); Repaired: 4.17% (Pass) |
| Tự động sinh báo cáo đối chiếu định lượng 3 trạng thái | `src/observability/reporting.py`: `generate_corruption_report()` | `data/reports/corruption_report.md` với đầy đủ so sánh RAG Metrics, Quality Gate, Freshness SLA | Kiểm tra file markdown sinh ra khớp 100% các file JSON kết quả |

**Output cụ thể:** Bộ ba artifact kiểm định chất lượng:
- `data/quality/baseline_quality_report.json`: `gx_success: true`, `is_fresh: true`, `overall success: true`.
- `data/quality/corrupted_quality_report.json`: `gx_success: false` (3 expectations fail: unique id, title length, summary length), `is_fresh: false` (stale ratio 39.13% > 25%), `overall success: false`.
- `data/quality/repaired_quality_report.json`: `gx_success: true`, `is_fresh: true`, `overall success: true`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. **Nguy cơ Silent Data Corruption:** Trong hệ thống RAG, khi dữ liệu nguồn bị suy giảm chất lượng (bị xóa bài, bị cắt ngắn tiêu đề, bị rỗng tóm tắt hoặc bị làm giả ngày xuất bản), toàn bộ luồng nhúng vector và LLM vẫn có thể chạy bình thường mà không hề ném ra Exception (lỗi âm thầm). Người dùng chỉ nhận thấy hệ thống trả lời sai hoặc ảo giác. Cần một chốt chặn kiểm dịch tự động (Data Quality Gate) ngay tại tầng Ingestion/Cleaning để chặn đứng dữ liệu bẩn trước khi ghi vào ChromaDB.
2. **Sự khác biệt giữa Data Schema Integrity và Temporal Freshness:** Một bản ghi có thể hoàn hảo về mặt cấu trúc (đủ trường, đúng kiểu dữ liệu, không null) nhưng thông tin bên trong đã quá hạn hàng năm trời. Do đó, kiểm tra schema thông thường không thể phát hiện bài báo đã bị lùi ngày xuất bản (`stale_date`). Cần kết hợp song song cả Schema Validation và Freshness SLA Monitoring.
3. **Tính tương thích của thư viện (GX 1.x migration):** Great Expectations phiên bản 1.x có sự thay đổi mang tính đột phá (breaking changes) so với phiên bản 0.x cũ: loại bỏ các API cũ (`DataAssistant`, `ge_context`), yêu cầu chuyển sang Ephemeral Context kết hợp Fluent Data Source. Nếu viết theo cú pháp cũ sẽ gây crash chương trình ngay lập tức.

### Cách triển khai

- **Kiến trúc GX 1.x Ephemeral In-Memory:**
  Sử dụng mô hình ephemeral context giúp pipeline hoàn toàn độc lập, không cần khởi tạo thư mục cấu hình cồng kềnh `great_expectations/` trên ổ đĩa:
  ```python
  context = gx.get_context(mode="ephemeral")
  data_source = context.data_sources.add_pandas(name="papers_source")
  data_asset = data_source.add_dataframe_asset(name="papers_asset")
  batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
  batch = batch_def.get_batch(batch_parameters={"dataframe": df})
  ```
- **Xây dựng bộ 6 Expectations cốt lõi (`_build_suite`):**
  1. `ExpectTableRowCountToBeBetween(min_value=20, max_value=30)`: Kiểm soát quy mô tập dữ liệu tải về.
  2. `ExpectColumnValuesToNotBeNull(column="paper_id")`: Đảm bảo khóa chính định danh không bị rỗng.
  3. `ExpectColumnValuesToBeUnique(column="paper_id")`: Khử trùng lặp khóa chính, ngăn chặn vector store bị ô nhiễm bản ghi trùng lặp.
  4. `ExpectColumnValuesToNotBeNull(column="title")`: Đảm bảo tiêu đề luôn tồn tại.
  5. `ExpectColumnValueLengthsToBeBetween(column="title", min_value=8)`: Phát hiện tiêu đề bị cắt cụt do lỗi parse hoặc kịch bản `truncate_title`.
  6. `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=50)`: Phát hiện tóm tắt rác hoặc bị xóa trắng do kịch bản `blank_summary`.
- **Cơ chế Freshness SLA Monitoring (`_freshness_summary`):**
  - Chuyển đổi cột `published` sang datetime và tính toán số ngày tuổi `age_days = (run_date - published).days`.
  - Đếm số lượng bài báo quá hạn: `stale_rows = (age_days > 180).sum()`.
  - Tính tỷ lệ: `stale_ratio = stale_rows / total_rows`.
  - Thiết lập trạng thái `is_fresh = (stale_ratio <= 0.25)`: Nếu trên 25% bài báo trong kho dữ liệu cũ hơn 6 tháng, hệ thống kích hoạt cảnh báo vi phạm SLA.
- **Quy tắc Overall Gate:**
  `overall_success = gx_success and freshness["is_fresh"]`. Dữ liệu chỉ được coi là đạt chuẩn khi và chỉ khi đồng thời vượt qua 100% expectations của Great Expectations và đạt chuẩn Freshness SLA.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `df: pd.DataFrame`, `settings: Settings`, `report_name: str` (`"baseline"`, `"corrupted"`, `"repaired"`) |
| Output                         | `dict[str, Any]` (chứa `gx_success`, `expectations[]`, `failed_expectations[]`, `freshness{}`, `success`), file JSON lưu tại `data/quality/{report_name}_quality_report.json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils.now_utc`, `core.utils.write_json`, `great_expectations` (v1.23.2) |
| Module sử dụng output        | `pipelines.phase1`, `pipelines.corruption_flow`, `observability.reporting` |
| Điều kiện lỗi cần xử lý | DataFrame rỗng, trường `age_days` hoặc `published` chứa giá trị NaN, cột bắt buộc bị thiếu trong DataFrame |

### Cách xác minh

Chạy kiểm tra độc lập Quality Gate trên môi trường Python:

```bash
uv run python -c "
import pandas as pd
from core.config import load_settings
from observability.quality import run_data_quality_checks

s = load_settings()
df = pd.read_json(s.paths.clean_json)
res = run_data_quality_checks(df, s, 'test_run')

print(f'Overall Success: {res[\"success\"]}')
print(f'GX Success: {res[\"gx_success\"]}')
print(f'Freshness is_fresh: {res[\"freshness\"][\"is_fresh\"]}')
print(f'Stale ratio: {res[\"freshness\"][\"stale_ratio\"]}')
print(f'Total expectations: {len(res[\"expectations\"])}')
"
```

- **Kết quả mong đợi:** Overall Success: True, GX Success: True, Freshness is_fresh: True, Stale ratio: 0.0417, Total expectations: 6.
- **Kết quả thực tế:** Khớp 100% kết quả mong đợi.
- **Artifact kiểm chứng:** `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức triển khai Great Expectations 1.x giữa việc duy trì thư mục cấu hình tĩnh (`great_expectations/great_expectations.yml` trên ổ đĩa) hay cấu hình động hoàn toàn trong bộ nhớ (`gx.get_context(mode="ephemeral")`).
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (File-system Context):* Tạo thư mục cấu hình `great_expectations/` qua CLI `great_expectations init`. Quản lý Data Sources, Checkpoints và Expectation Suites qua các tệp YAML lưu trên đĩa.
  - *Phương án 2 (Ephemeral In-Memory Context):* Khởi tạo context động qua mã nguồn Python với `gx.get_context(mode="ephemeral")`, đăng ký Pandas Data Asset trực tiếp từ `pd.DataFrame` hiện hữu trong bộ nhớ và thực thi validate tức thì.
- **Phương án đã chọn:** Phương án 2 (Ephemeral Context).
- **Lý do:**
  - *Tính độc lập và tiện lợi:* Khi nộp bài hoặc chạy trong môi trường CI/CD (hoặc trên máy chấm thi của Trợ giảng), việc phụ thuộc vào thư mục cấu hình cục bộ rất dễ gây lỗi đường dẫn tuyệt đối (vi phạm quy chế trừ điểm của Rubric) hoặc lỗi phiên bản format YAML giữa các máy.
  - *Hiệu năng:* Ephemeral context không phát sinh I/O đọc/ghi tệp cấu hình thừa thãi trên đĩa, giảm độ trễ thực thi của toàn bộ pipeline xuống dưới 1 giây.
  - *Khả năng tùy biến:* Cho phép dễ dàng tạo ra các bộ Suite độc lập cho từng trạng thái (`baseline`, `corrupted`, `repaired`) một cách linh hoạt bằng mã Python.
- **Bằng chứng quyết định phù hợp:**
  - Lệnh `uv run python script/run_phase1.py` và `uv run python script/run_corruption_flow.py` chạy trơn tru, không gặp bất kỳ lỗi `DataContextError` hay lỗi path nào, xuất đầy đủ báo cáo JSON trong `data/quality/`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  Khi nâng cấp lên Great Expectations 1.x, việc gọi API cũ `ge.from_pandas(df)` hoặc `batch.validate(expectation_suite)` theo cú pháp GX 0.18 bị cảnh báo deprecated hoặc báo lỗi:
  `AttributeError: 'Batch' object has no attribute 'validate'` (hoặc `TypeError: ExpectationSuite takes no arguments`).
- **Lệnh hoặc bước tái hiện:** Chạy hàm `run_data_quality_checks` với đoạn mã khởi tạo kế thừa từ các bài lab cũ GX 0.x.
- **Nguyên nhân gốc:**
  GX 1.x đã tái cấu trúc hoàn toàn hệ thống thực thi theo Fluent API:
  - `ExpectationSuite` trong GX 1.x không truyền trực tiếp vào batch cũ mà phải được thêm vào context (`context.suites.add(suite)`).
  - Đối tượng `Batch` được tạo thông qua chuỗi: `context.data_sources -> dataframe_asset -> batch_definition -> get_batch(batch_parameters={"dataframe": df})`.
  - Phép kiểm thử được thực thi qua `batch.validate(suite)`.
- **Cách xử lý:**
  - Tái cấu trúc lại hàm `_build_suite()` và `run_data_quality_checks()` tuân thủ 100% cú pháp mới nhất của GX 1.x:
    ```python
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(_build_suite(f"papers_{report_name}_suite"))
    validation = batch.validate(suite)
    ```
  - Bổ sung hàm tiện ích `_plain()` để làm phẳng các kiểu dữ liệu `numpy` / `pandas` trước khi xuất JSON, tránh lỗi `TypeError: Object of type int64 is not JSON serializable`.
- **Cách xác minh sau khi sửa:**
  Chạy kiểm định end-to-end, toàn bộ 6 expectations chạy thành công, trích xuất đầy đủ `unexpected_count` và `unexpected_percent` ra file JSON báo cáo.
- **Điều học được:** Thư viện Data Engineering (đặc biệt là Great Expectations) phát triển và thay đổi API rất nhanh. Cần thường xuyên tra cứu tài liệu chính thức (Official 1.x Documentation) thay vì sao chép các mẫu code trôi nổi từ các phiên bản cũ.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu bắt đầu từ Crossref REST API (hoặc snapshot offline), qua `parse_crossref_payload()` để chuẩn hóa thành các `PaperRecord`. Module Cleaning bóc tách thẻ HTML/XML, làm sạch khoảng trắng, dedupe theo ID và kết xuất ra DataFrame 24 dòng sạch với cột `text_for_embedding`. Tại đây, dữ liệu bắt buộc phải vượt qua Quality Gate của Great Expectations và Freshness SLA. Sau khi Gate xác nhận `success: true`, DataFrame mới được chuyển sang cho mô hình `all-MiniLM-L6-v2` tính toán vector 384 chiều và nạp vào collection ChromaDB phục vụ truy vấn.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Bộ câu hỏi gồm 10 câu hỏi mẫu rải đều trên 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`). Mỗi câu hỏi có gắn `ground_truth_doc_ids` (mã DOI của bài báo mang câu trả lời đúng). Khi Agent thực hiện truy xuất, hệ thống đối chiếu top-4 kết quả trả về từ ChromaDB: nếu mã của bài báo nằm trong top-4 thì tính là `hit`. Tiếp đó, câu trả lời sinh ra được so khớp với `ground_truth` văn bản để tính `token_f1`, và được chấm bởi Heuristic Judge để tính độ chính xác.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks (GX 1.x):* Đóng vai trò là chốt kiểm soát cú pháp và tính toàn vẹn cấu trúc (Syntactic & Structural Integrity): kiểm tra số dòng, ràng buộc NOT NULL, tính duy nhất của khóa chính, độ dài chuỗi ký tự.
   - *Freshness monitoring (SLA):* Đóng vai trò là chốt kiểm soát tính thời sự và ngữ nghĩa thời gian (Temporal Semantic Integrity): kiểm tra xem bài báo có bị cũ quá 180 ngày so với hiện tại hay không.
   - *Điểm khác biệt then chốt:* Khi bị tiêm lỗi `stale_date` (lùi ngày 3 năm), dữ liệu vẫn hoàn toàn đúng schema, không bị null, không bị trùng (GX pass 100%), nhưng Freshness SLA ngay lập tức báo FAIL (stale ratio tăng vọt lên 39.13%). Cả hai chốt chặn này bổ trợ chặt chẽ cho nhau.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Đây là nguyên tắc vàng trong khoa học thực nghiệm: Cô lập biến số (Controlled Experiment). Khi câu hỏi và đáp án mẫu được đóng băng cố định (với mã băm SHA-256 `bd5480e5c6fc`), biến số duy nhất thay đổi giữa 3 pha chính là chất lượng của dữ liệu được nạp vào vector store. Mọi sự thay đổi về điểm số (Hit Rate từ 1.00 tụt xuống 0.80 và hồi phục về 1.00) phản ánh trung thực 100% tác động của chất lượng dữ liệu, loại bỏ hoàn toàn nhiễu do độ khó của câu hỏi gây ra.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - *Về mặt kiểm soát chất lượng (Artifact):* Tệp `data/quality/repaired_quality_report.json` và `repaired_freshness_report.json` đều phải ghi nhận `success: true` (pass 6/6 expectations của GX và Freshness SLA đạt chuẩn).
   - *Về mặt hiệu năng (Metric):* Tệp `data/results/repaired_metrics.json` chứng minh toàn bộ các chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi 100% về mức tuyệt đối 1.00 (khớp với baseline).
   - *Về mặt dữ liệu (Data Diff):* Tệp `data/clean/papers_clean_repaired.json` trùng khớp hoàn toàn với bản gốc `papers_clean.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      0.80 |     1.00 | Giảm 20% do drop_latest_records làm mất tài liệu nguồn (q01, q02), phục hồi 100% sau repair |
| `mean_token_f1`      |     1.00 |      0.80 |     1.00 | Giảm do q01 mất tài liệu (F1=0) và q03 bị lệch mốc thời gian (F1=0), phục hồi trọn vẹn |
| `judge_accuracy`     |     1.00 |      0.80 |     1.00 | Tương quan trực tiếp với chất lượng ngữ cảnh được truy xuất |
| `mean_judge_score`   |     5.00 |      4.20 |     5.00 | Điểm đánh giá trung bình suy giảm từ 5.0 xuống 4.2 khi dữ liệu bị lỗi |
| Quality checks         | 6/6 PASS | 3/6 PASS | 6/6 PASS | Bắt chính xác 3 vi phạm: trùng lặp ID (4 rows), title ngắn (6 rows), summary rỗng (4 rows) |
| Freshness status       |    FRESH |     STALE |    FRESH | Tỷ lệ stale tăng vọt từ 4.17% lên 39.13% (> 25%), kích hoạt vi phạm SLA |

### Kết luận từ số liệu

1. **Chuỗi suy thoái (Corruption Impact):**
   - Kịch bản `drop_latest_records` xóa bỏ 3 bài báo mới nhất → 2 câu hỏi trong test set (`q01` và `q02`) bị mất tài liệu gốc trong kho vector → `retrieval_hit_rate` giảm trực tiếp từ 1.00 xuống 0.80.
   - Kịch bản `stale_date` lùi ngày 7 bài báo làm tỷ lệ bài cũ tăng lên 39.13% (vi phạm SLA Freshness max 25%), khiến câu hỏi `q03` trả lời sai năm xuất bản (2023 thay vì 2026), kéo `mean_token_f1` giảm từ 1.00 xuống 0.80.
   - Kịch bản `duplicate_rows` tạo 2 bản ghi nhân bản, vi phạm `expect_column_values_to_be_unique(paper_id)` (4 dòng vi phạm).
   - Kịch bản `truncate_title` làm tiêu đề bị cắt cụt dưới 8 ký tự, vi phạm `expect_column_value_lengths_to_be_between(title)` (6 dòng vi phạm).
   - Kịch bản `blank_summary` xóa rỗng abstract, vi phạm `expect_column_value_lengths_to_be_between(summary)` (4 dòng vi phạm).
2. **Chuỗi phục hồi (Repair Efficacy):**
   - Quá trình Idempotent Repair tái tạo sạch toàn bộ dữ liệu từ snapshot nguyên bản `data/raw/crossref_records.json` → Khôi phục đầy đủ 24 bài báo với metadata chuẩn xác.
   - Cổng Quality Gate kiểm định lại: Vượt qua 6/6 expectations, Freshness quay về mức 4.17% Stale (FRESH). Chốt kiểm dịch cho phép nạp dữ liệu vào ChromaDB collection `papers-repaired`.
   - Kết quả đánh giá trên cùng bộ test set cho thấy: Toàn bộ 10/10 câu hỏi truy xuất đúng tài liệu và trích xuất đúng thông tin, đưa `retrieval_hit_rate` và `mean_token_f1` phục hồi 100% về mức 1.00.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
- `drop_latest_records` ảnh hưởng trực tiếp và nghiêm trọng nhất lên hiệu năng retrieval vì nó gây ra lỗi mất thông tin vĩnh viễn (Missing Data Failure). Khi tài liệu không có trong vector index, mô hình retrieval dù hiện đại đến đâu cũng không thể trả về kết quả đúng.
- `stale_date` là lỗi âm thầm nguy hiểm nhất (Silent Hallucination Failure): Bản ghi vẫn tồn tại, retrieval vẫn hit, nhưng thông tin thời gian bị sai lệch khiến câu trả lời của mô hình sai sự thật mà không gây ra bất kỳ cảnh báo lỗi nào ở tầng code nếu thiếu Freshness SLA.

**Kết quả nào khác với kỳ vọng ban đầu?**
- Ban đầu tôi dự đoán expectation kiểm tra số lượng dòng (`ExpectTableRowCountToBeBetween`) sẽ phát hiện được việc xóa 3 bài báo ở kịch bản `drop_latest_records`.
- Tuy nhiên trên thực tế expectation này vẫn đạt **PASS** (quan sát được 23 dòng, vẫn nằm trong ngưỡng 20–30 dòng). Lý do là vì kịch bản `duplicate_rows` đã nhân bản thêm 2 dòng, bù trừ vào số dòng bị mất (24 - 3 + 2 = 23).
- Lỗi này chỉ bị vạch trần nhờ expectation kiểm tra tính duy nhất `ExpectColumnValuesToBeUnique(paper_id)`. Phát hiện này chứng minh một nguyên tắc thiết kế quan trọng: Không bao giờ được phép chỉ dựa vào số lượng dòng (Row count) để khẳng định tính toàn vẹn của dữ liệu!

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data Observability là phòng tuyến bắt buộc cho AI Systems:** Trong các hệ thống RAG và LLM Agents, dữ liệu lỗi không làm sập chương trình mà tạo ra Silent Failures (ảo giác, câu trả lời sai lệch). Chốt chặn Data Quality Gate (Great Expectations) kết hợp Freshness SLA phải được đặt ngay sau tầng Ingestion để ngăn chặn dữ liệu bẩn xâm nhập vào vector store.
2. **Kiểm định đa chiều (Defense in Depth):** Không có một chỉ số đơn lẻ nào có thể phản ánh toàn bộ sức khỏe của dữ liệu. Cần kết hợp đồng thời kiểm tra cấu trúc (row count, not null, uniqueness, string length bounds) và kiểm tra ngữ nghĩa thời gian (freshness distribution).
3. **Tính tái lập và tự phục hồi (Idempotent Self-Healing):** Để một pipeline có khả năng tự phục hồi, dữ liệu thô ban đầu (Raw Snapshot) phải được bảo toàn bất biến. Nhờ có `crossref_records.json` nguyên vẹn, quy trình repair mới có thể tái lập trạng thái sạch 100% mà không bị phụ thuộc vào tính bất định của API bên ngoài.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ triển khai **Automated Drift Detection & Real-time Alerting Webhook**:
- **Cải thiện:**
  1. Tích hợp thư viện Evidently AI hoặc Great Expectations Profiler để tự động phát hiện độ trôi phân phối ngữ nghĩa (Embedding Semantic Drift) của vector text theo thời gian.
  2. Xây dựng Slack/Discord Alert Webhook: Khi Quality Gate hoặc Freshness SLA bị FAIL, hệ thống tự động bắn cảnh báo kèm chi tiết các bản ghi vi phạm tới kênh trực vận hành của đội ngũ kỹ thuật.
- **Cách đo lường cải thiện:** Mô phỏng sự cố tiêm lỗi, kiểm chứng webhook gửi thông báo tức thì trong vòng < 2 giây kèm danh sách 3 expectations vi phạm, và hệ thống tự động kích hoạt luồng Rollback về collection an toàn trước đó.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Kiều Đình Đoàn  
**Ngày xác nhận:** 2026-09-26

# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đoàn Quang Thắng           |
| MSSV               | 2A202602395                |
| Khóa/Lớp         | K4 - L3B                   |
| Tên nhóm         | Nhóm 1PROMPT               |
| Vai trò chính    | Data model & evaluation-set owner (`src/ingestion/cleaning.py`, `src/evaluation/testset.py`) |
| Repository         | https://github.com/conanWinner/K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Cleaning & Modeling | `src/ingestion/cleaning.py`: `build_clean_dataframe()`, `add_derived_columns()`, `build_text_for_embedding()`, `clean_text()`, `_clean_list()` | `list[PaperRecord]` từ Ingestion, `run_date: datetime` | DataFrame sạch 24 dòng, 16 cột chuẩn `CLEAN_COLUMNS`, xuất ra `data/clean/papers_clean.csv` và `papers_clean.json` | Hoàn thành |
| Benchmark Evaluation Set | `src/evaluation/testset.py`: `build_test_set()`, `_question_for()`, `QUESTION_PLAN` | Clean DataFrame 24 dòng | Bộ 10 câu hỏi chuẩn hóa 4 nhóm nghiệp vụ lưu tại `data/eval/test_set.json` (sha256 prefix `bd5480e5c6fc`) | Hoàn thành |
| Evaluation Contract & Metrics Support | `src/evaluation/metrics.py`, `src/retrieval/qa.py` (phần tích hợp hit rate, ground-truth doc IDs) | Test set JSON, retrieval results | `retrieval_hit_rate`, `mean_token_f1`, logging answer | Hoàn thành |

Phần việc của tôi nhận đầu vào từ module Ingestion (`list[PaperRecord]` do Phạm Minh Hiếu phụ trách) và bàn giao DataFrame sạch cho:
1. Module Vector Index & Embedding (`src/retrieval/index.py` do Đỗ Việt Hoàng phụ trách).
2. Module Data Quality Gate & Observability (`src/observability/quality.py` do Kiều Đình Đoàn phụ trách).
3. Bộ test set do tôi thiết kế là thước đo duy nhất và bất biến được dùng chung cho cả 3 trạng thái baseline, corrupted và repaired trong toàn bộ pipeline.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đảm bảo tính bất biến của test set | Đỗ Việt Hoàng / `pipelines/phase1.py`, `pipelines/corruption_flow.py` | Cố định cơ chế nạp `data/eval/test_set.json`, tránh sinh lại ngẫu nhiên giữa các pha để đảm bảo cách ly hoàn toàn biến số đánh giá |
| Rà soát và hoàn thiện báo cáo nhóm | Toàn bộ nhóm / `report/group_report.md` | Đồng bộ bảng so sánh 3 trạng thái, xác thực số liệu Hit Rate, Token F1 giữa các file JSON kết quả |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Làm sạch văn bản, loại bỏ JATS XML tag, chuẩn hóa khoảng trắng thừa | `src/ingestion/cleaning.py`: `clean_text()` | 24/24 bản ghi sạch tag `<jats:p>`, không còn ký tự điều khiển | Kiểm tra trực tiếp trên `data/clean/papers_clean.json`, 0 thẻ XML còn sót |
| Khử trùng lặp `paper_id` và chuẩn hóa ID | `src/ingestion/cleaning.py`: `build_clean_dataframe()` | `paper_id` được chuyển về chữ thường, deduplication giữ bản ghi đầu | Great Expectations `ExpectColumnValuesToBeUnique(paper_id)` đạt Pass (0 trùng) |
| Tính toán các trường phái sinh (`age_days`, joined columns) và mô hình hóa `text_for_embedding` | `src/ingestion/cleaning.py`: `add_derived_columns()`, `build_text_for_embedding()` | Đủ 16 cột trong `CLEAN_COLUMNS`; `text_for_embedding` có đủ 5 phần Title/Authors/Categories/Published/Summary | Đọc DataFrame qua pandas, xác nhận 24 dòng không rỗng ở các cột bắt buộc |
| Xây dựng bộ test set 10 câu hỏi bao phủ 4 khía cạnh thông tin | `src/evaluation/testset.py`: `build_test_set()` | `data/eval/test_set.json` gồm 10 câu hỏi (3 summary, 3 authors, 2 date, 2 categories) kèm `ground_truth_doc_ids` | Script kiểm thử `build_test_set`, xác nhận 10 câu hỏi rải đều theo phân phối thời gian |

**Output cụ thể:** Artifact `data/eval/test_set.json` gồm 10 câu hỏi chuẩn hóa, kèm ground-truth document IDs và ground-truth text. Đây là tài sản đo lường then chốt của dự án:
- Phủ đủ 4 loại truy vấn (`summary`, `authors`, `date`, `categories`).
- Được lưu cố định với mã băm SHA-256 (tiền tố `bd5480e5c6fc`), cho phép đo lường chính xác mức độ sụt giảm từ 1.00 xuống 0.80 khi dữ liệu bị lỗi và phục hồi 100% về 1.00 sau khi repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. **Chất lượng dữ liệu phi cấu trúc:** Dữ liệu thu thập từ Crossref chứa nhiều tạp âm: abstract bị bao bọc bởi thẻ JATS XML (`<jats:p>`), khoảng trắng ngắt dòng bất thường, DOI viết hoa/thường lẫn lộn dẫn đến nguy cơ trùng lặp bản ghi ngầm. Nếu nạp trực tiếp vào embedding model, các thẻ markup này sẽ gây nhiễu không gian vector ngữ nghĩa.
2. **Thiếu hụt trường thông tin cho Retrieval:** Nếu chỉ embed trường `summary` (abstract), vector search sẽ hoàn toàn thất bại khi người dùng hỏi về tác giả (`authors`), ngày xuất bản (`published`) hoặc phân loại khoa học (`categories`). Cần một phương pháp mô hình hóa dữ liệu văn bản trước khi embed (`pre-embed modeling`) để gói gọn đa chiều thông tin vào một đoạn văn bản có cấu trúc.
3. **Độ tin cậy của Benchmark:** Để quan sát được tác động thực sự của lỗi dữ liệu (Data Corruption) lên mô hình RAG, bộ câu hỏi đánh giá phải có độ bao phủ cao, lấy mẫu đại diện và quan trọng nhất là phải có `ground_truth_doc_ids` chính xác làm căn cứ tính Hit Rate.

### Cách triển khai

- **Khử nhiễu và chuẩn hóa dữ liệu (`clean_text`, `_clean_list`):**
  - Sử dụng biểu thức chính quy `re.sub(r"<[^>]+>", " ", value)` loại bỏ toàn bộ các thẻ markup XML/HTML trong abstract và tiêu đề, sau đó chuẩn hóa các khoảng trắng liên tiếp về dấu cách đơn.
  - Chuẩn hóa toàn bộ `paper_id` thành chữ thường (`paper_id.str.lower()`) để loại bỏ sai lệch case-sensitive trước khi thực hiện `drop_duplicates(subset="paper_id", keep="first")`.
  - Làm sạch danh sách tác giả và categories: loại bỏ phần tử trùng lặp nội bộ và chuỗi rỗng.
- **Tính toán trường dẫn xuất (`add_derived_columns`):**
  - Chuyển đổi chuỗi ngày `published` thành định dạng chuẩn `YYYY-MM-DD`.
  - Tính toán `age_days = (run_date.date() - published).days` làm cơ sở trực tiếp cho kiểm tra Freshness SLA.
  - Tạo các chuỗi ghép gọn `authors_joined` và `categories_joined` bằng dấu phẩy cách nhau.
- **Mô hình hóa `text_for_embedding`:**
  - Thiết kế cấu trúc 5 phần rõ ràng phân tách bằng ký tự xuống dòng:
    ```text
    Title: {title}
    Authors: {authors_joined}
    Categories: {categories_joined}
    Published: {published}
    Summary: {summary}
    ```
  - Cấu trúc này giúp embedding model (`all-MiniLM-L6-v2`) học được mối tương quan ngữ nghĩa giữa ngữ cảnh bài báo và các metadata thực thể quan trọng.
- **Xây dựng bộ Test Set thông minh (`build_test_set`):**
  - Quy định kế hoạch phân bổ 10 câu hỏi (`QUESTION_PLAN`) theo tỉ lệ: 3 câu tóm tắt (`summary`), 3 câu tác giả (`authors`), 2 câu thời gian (`date`), và 2 câu thể loại (`categories`).
  - Sắp xếp DataFrame sạch theo `published` giảm dần và `paper_id` tăng dần, sau đó lấy mẫu với bước nhảy đều `step = len(ordered) / len(QUESTION_PLAN)`. Việc này đảm bảo 10 câu hỏi được rải đều trên toàn bộ phân phối thời gian của kho dữ liệu (từ bài mới nhất 2026-07-22 đến bài cũ nhất 2026-03-28).
  - Tự động sinh câu hỏi tự nhiên theo template và trích xuất câu trả lời chuẩn (`ground_truth`) cùng `ground_truth_doc_ids` tương ứng của bản ghi.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `list[PaperRecord]` từ Ingestion; `run_date: datetime`; `output_path: Path` |
| Output                         | `pd.DataFrame[CLEAN_COLUMNS]` (24 dòng sạch); file `data/clean/papers_clean.{csv,json}`; file `data/eval/test_set.json` (10 items) |
| Module phụ thuộc             | `src/core/config.py`, `src/core/utils.py`, `src/ingestion/crossref.py` (`PaperRecord`) |
| Module sử dụng output        | `src/retrieval/index.py` (tạo ChromaDB), `src/observability/quality.py` (chạy GX suite), `src/pipelines/phase1.py` & `corruption_flow.py` (đánh giá) |
| Điều kiện lỗi cần xử lý | Abstract chứa HTML rác, `paper_id` trùng khác hoa thường, ngày xuất bản lỗi format, thiếu trường bắt buộc, DataFrame đầu vào không đủ số lượng tối thiểu (`< 10`) |

### Cách xác minh

Chạy kiểm tra độc lập các hàm làm sạch và sinh test set:

```bash
python -c "
from datetime import datetime, timezone
from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set

s = load_settings()
records = load_raw_records(s.paths.raw_records_json)
df = build_clean_dataframe(records, datetime.now(timezone.utc))
test_set = build_test_set(df, s.paths.test_set_json)

print(f'Clean records: {len(df)} rows, Unique IDs: {df[\"paper_id\"].nunique()}')
print(f'Test set generated: {len(test_set)} questions')
print(f'Columns check: {all(c in df.columns for c in [\"text_for_embedding\", \"age_days\"])}')
"
```

- **Kết quả mong đợi:** Clean records: 24 rows, Unique IDs: 24; Test set generated: 10 questions; Columns check: True.
- **Kết quả thực tế:**
  ```text
  Clean records: 24 rows, Unique IDs: 24
  Test set generated: 10 questions
  Columns check: True
  ```
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/eval/test_set.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn nội dung để đưa vào trường vector hóa `text_for_embedding` và phương thức lấy mẫu câu hỏi cho bộ đánh giá.
- **Các phương án đã cân nhắc:**
  - *Phương án 1:* Chỉ đưa `title` và `summary` (abstract) vào `text_for_embedding`. Với test set, chọn 10 câu hỏi ngẫu nhiên (`random.sample`) tập trung hoàn toàn vào nội dung tóm tắt của bài báo.
  - *Phương án 2:* Đưa có cấu trúc cả 5 trường (`Title`, `Authors`, `Categories`, `Published`, `Summary`) vào `text_for_embedding`. Với test set, chia đều 4 nhóm nghiệp vụ và lấy mẫu trải đều theo mốc thời gian xuất bản.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:**
  - Về vector search: Người dùng hệ thống RAG không chỉ tìm bài báo theo nội dung mà thường xuyên truy vấn theo tác giả ("Ai viết bài này?"), ngày xuất bản ("Bài này công bố khi nào?"), hoặc danh mục ngành. Nếu chọn Phương án 1, các câu hỏi về tác giả và ngày tháng sẽ có vector query nằm ngoài không gian đặc trưng của abstract, dẫn đến hiện tượng trượt tìm kiếm (miss retrieval).
  - Về benchmark: Chọn mẫu ngẫu nhiên sẽ khiến test set thiên lệch (có thể rơi vào toàn bài cũ hoặc toàn bài mới) và không tái lập được giữa các lần chạy. Việc lấy mẫu rải đều theo phân phối thời gian giúp kiểm chứng được cả các kịch bản lỗi thời gian (`stale_date`) và xóa bài mới (`drop_latest_records`).
- **Bằng chứng quyết định phù hợp:**
  - Nhờ cấu trúc 5 phần, baseline đạt `retrieval_hit_rate = 1.00` trên toàn bộ 10 câu hỏi thuộc cả 4 nhóm.
  - Khi áp dụng kịch bản corruption `stale_date`, câu hỏi `q03` (loại date) ngay lập tức phát hiện câu trả lời bị sai lệch năm từ 2026 về 2023 (`token_f1 = 0.0`), chứng minh test set phản ánh cực kỳ nhạy bén sự suy thoái dữ liệu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi chạy lại pipeline ở pha đánh giá corruption hoặc sau khi chỉnh sửa testset, kết quả hit rate và câu trả lời vẫn nạp dữ liệu câu hỏi cũ; hoặc nếu sinh lại ngẫu nhiên thì điểm số giữa baseline và corrupted không thể so sánh được vì câu hỏi bị thay đổi.
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` sau đó chạy `python script/run_corruption_flow.py`.
- **Nguyên nhân gốc:**
  - Trong `src/pipelines/phase1.py`, cơ chế caching test set cần được kiểm soát chặt chẽ: nếu luôn tự động sinh lại mà không có seed và không sort cố định thì mỗi lần chạy bộ test sẽ khác nhau. Ngược lại, nếu lưu cứng mà không có cơ chế `REFRESH_TEST_SET`, việc cập nhật logic câu hỏi sẽ bị bỏ qua.
  - Trong `src/evaluation/testset.py`, hàm lấy mẫu ban đầu nếu không sort rõ ràng cả 2 khóa `published` và `paper_id` sẽ dẫn đến hiện tượng không ổn định thứ tự khi các bài báo có cùng ngày xuất bản.
- **Cách xử lý:**
  - Cập nhật hàm `build_test_set()`: Bắt buộc sắp xếp xác định 2 tầng: `df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)`.
  - Phối hợp với bạn phụ trách Pipeline thiết lập quy ước: Test set được sinh chuẩn ở Phase 1 và lưu vào `data/eval/test_set.json`. Trong `corruption_flow.py`, bắt buộc tái sử dụng đúng tệp này (nếu đã tồn tại) để đảm bảo tính bất biến tuyệt đối của bộ đề thi (Golden Benchmark).
- **Cách xác minh sau khi sửa:**
  - Kiểm tra mã hash SHA-256 của `data/eval/test_set.json` luôn bắt đầu bằng `bd5480e5c6fc` qua các lần chạy.
  - Cả 3 file kết quả `baseline_metrics.json`, `corrupted_metrics.json` và `repaired_metrics.json` đều tham chiếu chính xác cùng danh sách 10 mã câu hỏi từ `q01` đến `q10`.
- **Điều học được:** Đánh giá hệ thống RAG bản chất là một thực nghiệm khoa học. Muốn cô lập và đo lường được tác động của một biến số duy nhất (ở đây là chất lượng dữ liệu sạch vs lỗi vs phục hồi), toàn bộ môi trường đánh giá và bộ đề benchmark phải được đóng băng (immutable).

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô JSON từ Crossref API (`works`) hoặc snapshot được nạp vào, qua `parse_crossref_payload()` để bóc tách thành danh sách `PaperRecord`. Module cleaning tiếp nhận, loại bỏ rác markup XML, chuẩn hóa khoảng trắng, dedupe theo `paper_id` viết thường, tính trường thời gian `age_days` và hợp nhất metadata thành chuỗi 5 dòng `text_for_embedding`. Chuỗi này cùng metadata tương ứng được đưa vào mô hình `sentence-transformers/all-MiniLM-L6-v2` để sinh vector nhúng 384 chiều và lưu vào collection ChromaDB tương ứng (`papers-baseline`, `papers-corrupted`, hoặc `papers-repaired`).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `build_test_set()` sinh ra 10 câu hỏi chuẩn từ dữ liệu sạch kèm theo `ground_truth_doc_ids` (chứa `paper_id` của bài báo chứa thông tin trả lời). Khi đánh giá retrieval, hệ thống lấy top-k (k=4) văn bản trả về từ ChromaDB; nếu `ground_truth_doc_ids` nằm trong top-k thì ghi nhận lượt truy xuất thành công (Hit). Với câu trả lời sinh ra, `ground_truth` được dùng để so khớp độ trùng khớp từ vựng qua `token_f1` và làm ngữ cảnh chuẩn cho LLM Judge chấm điểm độ chính xác.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks (Great Expectations 1.x)* tập trung vào tính toàn vẹn về mặt cấu trúc và cú pháp của dữ liệu (Syntactic & Structural Integrity): kiểm tra số lượng dòng (20–30), các cột khóa không null, tính duy nhất của ID, độ dài tối thiểu của tiêu đề và tóm tắt.
   - *Freshness monitoring (SLA)* tập trung vào tính kịp thời và độ tươi mới về mặt thời gian của dữ liệu (Temporal Relevance): đo lường tỷ lệ các bài báo có tuổi đời `age_days > 180` ngày so với ngày chạy hiện tại (nếu vượt quá 25% thì kích hoạt cảnh báo STALE). Dữ liệu có thể hoàn hảo về mặt schema nhưng vẫn vi phạm Freshness nếu bài báo đã quá cũ.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để thực hiện nguyên tắc cô lập biến số (Isolation of Variables). Nếu thay đổi câu hỏi giữa các pha, sự thay đổi của các chỉ số (Hit Rate, F1, Judge Score) có thể do câu hỏi dễ hơn hoặc khó hơn gây ra. Việc giữ nguyên 100% câu hỏi và ground truth giúp khẳng định chắc chắn rằng mọi sự suy giảm hay phục hồi chỉ số hoàn toàn bắt nguồn từ sự thay đổi chất lượng của dữ liệu bên trong vector store.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Về mặt kiểm soát chất lượng (Artifact): `data/quality/repaired_quality_report.json` và `repaired_freshness_report.json` phải đạt trạng thái `success: true` (vượt qua toàn bộ 6 expectations của GX và SLA Freshness).
   - Về mặt hiệu năng (Metric): `data/results/repaired_metrics.json` chứng minh các chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi hoàn toàn về mức ban đầu (từ 0.80 lên lại 1.00), và nội dung file `papers_clean_repaired.json` khớp hoàn toàn với bản gốc.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      0.80 |     1.00 | Giảm 20% ở pha corrupt do mất tài liệu nguồn, phục hồi 100% sau repair |
| `mean_token_f1`      |     1.00 |      0.80 |     1.00 | Rơi tự do ở các câu hỏi mất văn bản và lệch mốc thời gian, phục hồi trọn vẹn |
| `judge_accuracy`     |     1.00 |      0.80 |     1.00 | Phản ánh chính xác sự tương quan với chất lượng ngữ cảnh truy xuất |
| `mean_judge_score`   |     5.00 |      4.20 |     5.00 | Điểm đánh giá trung bình suy giảm từ 5.0 xuống 4.2 khi dữ liệu bị lỗi |
| Quality checks         | 6/6 pass | 3/6 pass | 6/6 pass | Gate bắt chính xác 3 vi phạm: trùng lặp ID, cắt ngắn title, rỗng summary |
| Freshness status       |    Fresh |     Stale |    Fresh | Tỷ lệ stale tăng vọt từ 4.17% lên 39.13% (> 25%), kích hoạt vi phạm SLA |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **Chuỗi suy thoái (Corruption Impact):**
   Kịch bản `drop_latest_records` xóa bỏ 3 bài báo mới nhất trong tập dữ liệu → 2 câu hỏi trong test set (`q01` về summary và `q02` về authors) bị mất tài liệu gốc trong kho vector → `retrieval_hit_rate` sụt giảm trực tiếp từ 1.00 xuống 0.80. Kèm theo đó, kịch bản `stale_date` lùi ngày 7 bài báo làm tỷ lệ cũ tăng lên 39.13% (vi phạm SLA Freshness), khiến câu hỏi `q03` trả lời sai năm xuất bản (2023 thay vì 2026), kéo `mean_token_f1` giảm từ 1.00 xuống 0.80.
2. **Chuỗi phục hồi (Repair Efficacy):**
   Thực thi cơ chế Idempotent Repair tái tạo sạch toàn bộ dữ liệu từ snapshot gốc `data/raw/crossref_records.json` → Khôi phục đầy đủ 24 bài báo với metadata chuẩn xác → Cổng Quality Gate pass 6/6 expectations và Freshness quay về mức 4.17% Stale (Fresh) → Toàn bộ 10/10 câu hỏi truy xuất đúng tài liệu và trích xuất đúng thông tin, đưa `retrieval_hit_rate` và `mean_token_f1` phục hồi 100% về mức 1.00.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
- Ảnh hưởng trực tiếp và nghiêm trọng nhất lên chỉ số RAG là **`drop_latest_records`**. Khi bản ghi bị xóa khỏi vector store, mô hình hoàn toàn không có cách nào truy xuất được tài liệu đúng (Missing Information Failure), dẫn tới Hit Rate của các câu hỏi tương ứng tụt về 0.
- Về mặt thời gian, **`stale_date`** gây ra lỗi Silent Hallucination: câu hỏi vẫn tìm được bài báo nhưng thông tin năm xuất bản bị sai lệch hoàn toàn, làm suy giảm F1 score mà nếu chỉ nhìn vào Hit Rate sẽ không phát hiện ra.

**Kết quả nào khác với kỳ vọng ban đầu?**
- Ban đầu tôi dự đoán các kịch bản như `blank_summary`, `inject_noise` và `truncate_title` sẽ làm giảm điểm retrieval của toàn bộ 10 câu hỏi.
- Tuy nhiên kết quả thực tế cho thấy các câu hỏi khác vẫn đạt Hit Rate do đặc tính của phép tìm kiếm ngữ nghĩa (Semantic Dense Retrieval) có khả năng chịu lỗi từ khóa nhất định, và một số bản ghi bị làm bẩn không rơi trúng vào 10 bài báo được chọn làm câu hỏi trong test set.
- Hiện tượng này chứng minh tầm quan trọng cốt tử của **Data Quality Gate**: Nếu chỉ nhìn vào metric đầu ra của RAG agent, các lỗi dữ liệu bẩn (như summary rỗng hay title bị cắt cụt) sẽ bị che giấu (Silent Failure). Cần phải chặn đứng dữ liệu bẩn bằng Great Expectations ngay tại tầng Ingestion/Cleaning trước khi cho phép lập chỉ mục vector.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline & Modeling:** Tiền xử lý dữ liệu và cấu trúc hóa trường embed (`text_for_embedding`) là yếu tố quyết định "trần chất lượng" của hệ thống RAG. Một mô hình LLM tiên tiến đến đâu cũng sẽ trả lời sai nếu tầng dữ liệu phía dưới bị nhiễu thẻ XML, thiếu ngày tháng hoặc trùng lặp thực thể.
2. **Về Data Quality & Observability:** Cần phải thiết lập hệ thống quan sát đa tầng. Quality checks kiểm soát tính toàn vẹn cú pháp/cấu trúc, trong khi Freshness SLA kiểm soát tính kịp thời của thông tin. Không thể trông chờ vào việc kiểm tra thủ công hay chỉ dựa vào metric của agent để phát hiện lỗi dữ liệu.
3. **Về RAG Evaluation Methodology:** Đánh giá RAG đòi hỏi tính kỷ luật cao về phương pháp luận: bộ test benchmark phải mang tính đại diện, đa dạng các nhóm câu hỏi và bắt buộc phải bất biến (immutable) để làm hệ quy chiếu tin cậy giữa các trạng thái dữ liệu.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ triển khai **Dynamic Synthetic Test Set Generation kết hợp với Ragas framework**:
- **Lý do:** Hiện tại bộ test set gồm 10 câu hỏi được sinh theo rule-based template cố định. Dù đảm bảo tính ổn định tuyệt đối nhưng độ phức tạp ngôn ngữ chưa bằng các câu hỏi thực tế của người dùng.
- **Cách đo lường cải thiện:** Tích hợp bộ sinh câu hỏi đa tầng (Simple, Reasoning, Multi-context) và đo lường đồng thời 4 chỉ số chuẩn của Ragas (`Faithfulness`, `Answer Relevance`, `Context Precision`, `Context Recall`) trên một LLM Judge thực thụ (như Gemini 2.5 Flash), so sánh độ nhạy của bộ metric này trước 6 kịch bản corruption so với heuristic benchmark hiện tại.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đoàn Quang Thắng  
**Ngày xác nhận:** 2026-09-26

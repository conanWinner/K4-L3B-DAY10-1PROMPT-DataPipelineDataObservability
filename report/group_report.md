# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4 - L3B                   |
| Tên nhóm         | Nhóm 1PROMPT               |
| Repository         | https://github.com/conanWinner/K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Phạm Minh Hiếu | 2A202602630 | Source owner | `src/ingestion/crossref.py`, `data/raw/` |
| 2 | Đoàn Quang Thắng | 2A202602395 | Data model & evaluation-set owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| 3 | Kiều Đình Đoàn | 2A202602936 | Observability owner | `src/observability/quality.py`, `src/observability/reporting.py` |
| 4 | Đỗ Việt Hoàng | 2A202602882 | Corruption & integration owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành pipeline end-to-end từ Crossref snapshot đến báo cáo đối chiếu 3 trạng thái. Pha baseline
ingest 24 bài báo, làm sạch thành 24 dòng (bỏ tag JATS `<jats:p>`, chuẩn hóa khoảng trắng, dedupe theo `paper_id`,
tính `age_days`, sinh `text_for_embedding` 5 phần), index 24 document vào ChromaDB collection `papers-baseline`
bằng `all-MiniLM-L6-v2` và đánh giá trên bộ test 10 câu (summary/authors/date/categories). Baseline đạt hit rate
1.00, token F1 1.00; Quality Gate GX 1.x pass 6/6 expectations và Freshness SLA pass (1/24 bài quá 180 ngày).

Tiêm 6 loại lỗi (seed 42, 24 → 23 dòng) làm hit rate và token F1 cùng giảm còn 0.80 mà pipeline không phát sinh
exception nào (silent failure). Ảnh hưởng rõ nhất là **drop_latest_records** (2 câu mất tài liệu đúng) và
**stale_date** (câu hỏi ngày xuất bản trả lời sai năm 2023 thay vì 2026). Quality Gate bắt được 3 expectation fail
(unique `paper_id`, độ dài title, độ dài summary) và Freshness SLA fail (stale ratio 0.3913 > 0.25). Repair rebuild từ
`data/raw/crossref_records.json` cho ra dataset giống hệt baseline, gate pass và mọi metric về lại 1.00.

Giới hạn chính: chạy với `LLM_PROVIDER=mock`, nên judge dùng heuristic fallback và agent demo bị bỏ qua; Ragas chưa chạy.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref snapshot data/raw/crossref_response.json   (REFRESH_SOURCE=1 -> gọi Crossref API, retry 429/5xx)
    -> parse_crossref_payload -> data/raw/crossref_records.json
    -> build_clean_dataframe -> data/clean/papers_clean.{csv,json}
    -> MiniLM + ChromaDB (papers-baseline) -> data/chroma/, data/embeddings/papers_embeddings.json
    -> build_test_set (10 câu) -> data/eval/test_set.json
    -> evaluate_pipeline -> data/results/baseline_{metrics,answers}.json
    -> GX 1.x quality gate + freshness -> data/quality/baseline_quality_report.json, freshness_report.json
    -> data/reports/phase1_report.md
    -> corrupt_clean_dataframe (6 lỗi) -> data/clean/papers_clean_corrupted.* + data/results/corruption_log.json
    -> re-index (papers-corrupted) + evaluate + quality gate -> corrupted_metrics.json, corrupted_quality_report.json
    -> repair: rebuild từ raw records -> quality gate (chặn nếu fail) -> papers_clean_repaired.*
    -> re-index (papers-repaired) + evaluate -> repaired_metrics.json
    -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API / snapshot | Gọi API với retry + backoff (429/500/502/503/504), fallback snapshot, parse DOI/title/abstract/author/subject/dates | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Phạm Minh Hiếu |
| Cleaning          | `PaperRecord` list | Bỏ tag markup, chuẩn hóa khoảng trắng, lọc row thiếu field, dedupe `paper_id`, tính `age_days` | `data/clean/papers_clean.{csv,json}` | Đoàn Quang Thắng |
| Embedding/index   | Clean dataframe | `all-MiniLM-L6-v2` (normalized), ChromaDB cosine, 1 collection / trạng thái | `data/chroma/`, `data/embeddings/*.json` | Đỗ Việt Hoàng |
| Evaluation        | Clean dataframe | 10 câu, 4 loại; hit rate, token F1, judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Đoàn Quang Thắng |
| Observability     | Dataframe | 6 expectations GX 1.x + Freshness SLA (180 ngày, ≤ 25% stale) | `data/quality/*.json` | Kiều Đình Đoàn |
| Corruption/repair | Clean dataframe / raw records | 6 kịch bản lỗi seed 42; repair từ raw, chặn serve nếu gate fail | `data/results/corruption_log.json`, `data/clean/papers_clean_{corrupted,repaired}.*` | Đỗ Việt Hoàng |
| Orchestration     | Settings        | `phase1.py` → `corruption_flow.py` | `data/reports/*.md` | Đỗ Việt Hoàng |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `mock` |
| `LLM_MODEL`                | `gemini-2.5-flash` (không dùng khi mock) |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval`top_k`           | 4 |
| Freshness threshold          | 180 ngày; SLA tối đa 25% bản ghi stale |
| Random seed, nếu có        | 42 (corruption) |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

Cần cài dạng editable để package trong `src/` (`core`, `ingestion`, `pipelines`...) import được từ `script/`.

### Lệnh chạy

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Trên Windows nên `set PYTHONUTF8=1` trước khi chạy các lệnh in tiếng Việt.

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (exit 0) | 2026-09-26 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (exit 0) | 2026-09-26 | `data/results/{corrupted,repaired}_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API `https://api.crossref.org/works`; mặc định đọc snapshot `data/raw/crossref_response.json` |
| Query/filter                | `agentic retrieval augmented generation large language model`; `from-pub-date:<ngày chạy − 180 ngày>,has-abstract:true`; `rows=24` |
| Thời điểm lấy dữ liệu | Snapshot có sẵn trong repo; pipeline chạy 2026-09-26 |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Tối đa 3 lần, backoff 1s, 2s cho 429/500/502/503/504. Nếu API lỗi hoặc không trả record hợp lệ thì fallback snapshot; snapshot chỉ bị ghi đè khi API trả về dữ liệu dùng được. |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | str (DOI lowercase) | Có | Document identity ổn định | Thiếu → bỏ record; trùng → giữ bản đầu tiên |
| `title` | str | Có | Tiêu đề | Thiếu → bỏ record |
| `summary` | str | Có | Abstract đã bỏ tag JATS | Thiếu → bỏ record |
| `authors` | list[str] | Không | `given family` hoặc `name` | Rỗng → `authors_joined = ""` |
| `categories` | list[str] | Không | Crossref `subject` | Rỗng → `primary_category = ""` |
| `published` | str `YYYY-MM-DD` | Có | `published` → `published-print` → `published-online` → `issued` | Không có ngày → bỏ record |
| `updated` | str `YYYY-MM-DD` | Không | `created.date-time` | Fallback = `published` |
| `age_days` | int | Có | `run_date − published` (ngày) | Không tính được → bỏ record |
| `summary_chars` | int | Có | Độ dài summary | Suy ra |
| `text_for_embedding` | str | Có | Title / Authors / Categories / Published / Summary | Suy ra |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ tag `<jats:p>` / markup khỏi abstract | Validity | 24 | `papers_clean.json` không còn tag trong `summary` |
| Chuẩn hóa khoảng trắng thừa | Consistency | 1 | So sánh raw response với clean |
| Dedupe theo `paper_id` | Uniqueness | 0 | GX `expect_column_values_to_be_unique(paper_id)` pass |
| Loại record thiếu id / title / summary / ngày | Completeness | 0 | Raw 24 → clean 24 |

`text_for_embedding` ghép 5 dòng `Title / Authors / Categories / Published / Summary`, nên câu hỏi về tác giả, ngày
và category cũng khớp được về mặt ngữ nghĩa chứ không chỉ khớp nội dung abstract. Document ID là DOI viết thường,
ổn định giữa các lần chạy. `age_days = (run_date.date() − published).days`.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 |
| Các`question_type`                    | summary ×3, authors ×3, date ×2, categories ×2 |
| Ground-truth document ID                 | `paper_id` (DOI) của paper được chọn rải đều từ mới nhất đến cũ nhất |
| Embedding model                          | `all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB cosine: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval`top_k`                       | 4 |
| LLM provider/model                       | `mock` (judge = heuristic fallback theo token F1) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (sha256 prefix `bd5480e5c6fc`) |

Test set được sinh một lần từ dữ liệu sạch ở phase 1; `corruption_flow.py` đọc lại đúng file đó cho cả corrupted và
repaired. Vì câu hỏi và ground truth không đổi, mọi chênh lệch metric giữa 3 trạng thái chỉ đến từ dữ liệu được index.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 items / 24 records |
| Cleaned dataset          | `data/clean/`                        | Có | 24 dòng |
| Embedding manifest/index | `data/embeddings/`                   | Có | 3 manifest, 3 collection |
| Evaluation set           | `data/eval/`                         | Có | 10 câu |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | |
| Quality/freshness        | `data/quality/`                      | Có | baseline/corrupted/repaired |
| Baseline report          | `data/reports/phase1_report.md`      | Có | |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.00 | Cả 10 câu đều retrieve đúng paper (title trong câu hỏi khớp exact lookup) |
| `mean_token_f1`      | 1.00 | Câu trả lời trích xuất từ metadata khớp hoàn toàn ground truth |
| `judge_accuracy`     | 1.00 | Heuristic judge (mock provider) |
| `mean_judge_score`   | 5 | Heuristic judge (mock provider) |
| Ragas, nếu có        | N/A | Không bật `RUN_RAGAS=1` |

Baseline đạt tuyệt đối vì câu hỏi chứa nguyên title và câu trả lời được trích trực tiếp từ metadata. Đây là mốc
tham chiếu để đo suy giảm, không phải thước đo năng lực LLM.

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | 20–30 dòng | Pass (24) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(paper_id)` | Completeness | 0 null | Pass (0) | như trên |
| `ExpectColumnValuesToBeUnique(paper_id)` | Uniqueness | 0 trùng | Pass (0) | như trên |
| `ExpectColumnValuesToNotBeNull(title)` | Completeness | 0 null | Pass (0) | như trên |
| `ExpectColumnValueLengthsToBeBetween(title)` | Validity | ≥ 8 ký tự | Pass (0) | như trên |
| `ExpectColumnValueLengthsToBeBetween(summary)` | Validity | ≥ 50 ký tự | Pass (0) | như trên |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean dataset (cột `age_days`) |
| Timestamp mới nhất       | 2026-07-22 (cũ nhất 2026-03-28) |
| Ngưỡng freshness         | `age_days > 180` là stale; `is_fresh` khi stale ratio ≤ 25% |
| Trạng thái baseline      | Fresh |
| Lý do                     | 1/24 bài stale (stale ratio 0.0417) |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| drop_latest_records | Bỏ 3 bài mới nhất | 3 | Row count giảm | q01, q02 mất tài liệu đúng (hit = False); q01 F1 = 0 | Rebuild từ raw |
| blank_summary | `summary = ""` | 4 | Summary length fail | Summary length fail 4 dòng; không trúng câu summary nào trong test set | Rebuild từ raw |
| inject_noise | Chèn token rác (`#@!`, `lorem`, `NaN`...) vào abstract | 4 | Không có expectation riêng | Không bị gate phát hiện; q04, q07 vẫn trả lời đúng | Rebuild từ raw |
| truncate_title | Cắt title còn 6 ký tự | 5 | Title length fail | Title length fail 6 dòng (5 + 1 bản duplicate); q07 vẫn đúng nhờ semantic search | Rebuild từ raw |
| stale_date | Lùi `published` 1095 ngày | 7 | Freshness fail | Stale ratio 0.3913; q03 trả lời `2023-06-13` thay vì ngày 2026 → F1 = 0 | Rebuild từ raw |
| duplicate_rows | Nhân bản 2 dòng | 2 | Unique `paper_id` fail | 4 dòng vi phạm unique; bù số dòng nên row count vẫn pass | Rebuild từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: ghi đủ 6 loại, mô tả, số dòng và `affected_paper_ids`, seed 42, `input_rows` 24 → `output_rows` 23.

Repair không vá từng dòng lỗi mà rebuild toàn bộ clean dataset từ `data/raw/crossref_records.json` (raw snapshot không
bị corruption chạm vào) bằng đúng hàm `build_clean_dataframe` của baseline. Dữ liệu repaired phải pass quality gate
trước khi được lưu và index; nếu fail, `corruption_flow.py` dừng với thông báo từ chối serve. Kết quả lần chạy này:
`papers_clean_repaired.json` giống hệt `papers_clean.json`.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   | 1.00 | 0.80 | 1.00 | −0.20 | 100% | q01, q02 mất tài liệu do drop latest |
| `mean_token_f1`        | 1.00 | 0.80 | 1.00 | −0.20 | 100% | q01 (summary) và q03 (date) F1 = 0 |
| `judge_accuracy`       | 1.00 | 0.80 | 1.00 | −0.20 | 100% | Heuristic judge |
| `mean_judge_score`     | 5.00 | 4.20 | 5.00 | −0.80 | 100% | Heuristic judge |
| Quality checks pass/fail | 6/6 pass | 3/6 pass | 6/6 pass | −3 | 100% | Fail: unique `paper_id`, title length, summary length |
| Freshness status         | Fresh (0.0417) | Stale (0.3913) | Fresh (0.0417) | +0.35 stale ratio | 100% | |

Kết luận nhân quả:

1. stale_date lùi `published` của 7 bài → stale ratio 0.0417 → 0.3913, Freshness SLA fail → q03 trả lời ngày
   `2023-06-13` thay vì ngày 2026 thật → token F1 của nhóm câu date giảm từ 1.00 còn 0.50.
2. drop_latest_records xóa 3 bài mới nhất → 2/10 câu hỏi không còn tài liệu đúng trong index → hit rate 1.00 → 0.80.
   Row count không báo lỗi (23 vẫn trong khoảng 20–30) vì 2 dòng duplicate bù lại; chỉ uniqueness check lộ ra vấn đề.
3. Repair rebuild từ raw → 6/6 expectations pass, stale ratio về 0.0417 → mọi metric về lại đúng baseline.

Quan sát thêm:

- q02 (authors) mất tài liệu đúng nhưng vẫn trả lời đúng `Bao Do, Linh Ngo` vì corpus có paper khác cùng tác giả.
  Metric câu trả lời có thể che giấu lỗi retrieval, nên cần theo dõi đồng thời hit rate và quality gate.
- blank_summary, inject_noise và truncate_title không làm giảm metric trong test set này vì không trúng câu hỏi
  tương ứng (hoặc semantic search vẫn tìm đúng), nhưng quality gate vẫn bắt được blank và truncate. Đây đúng là lý do
  cần gate ở tầng dữ liệu thay vì chỉ dựa vào metric của RAG.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Chạy lại `run_phase1.py` sau khi thay đổi `testset.py` vẫn cho ra bộ câu hỏi cũ.
- **Nguyên nhân:** `phase1.py` ưu tiên tải `data/eval/test_set.json` đã có (để 3 trạng thái dùng chung một test set)
  và chỉ sinh lại khi `REFRESH_TEST_SET=1`.
- **Cách xử lý:** Xóa `data/eval/test_set.json` (hoặc đặt `REFRESH_TEST_SET=1`) rồi chạy lại cả `run_phase1.py` và
  `run_corruption_flow.py` để baseline, corrupted và repaired cùng dùng test set mới.
- **Cách xác minh:** `data/eval/test_set.json` có sha256 prefix `bd5480e5c6fc`, 10 câu; baseline hit rate 1.00 và
  corruption report được sinh lại từ cùng test set.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Chạy `LLM_PROVIDER=mock` | Judge là heuristic, agent demo bị bỏ qua | Đặt `GOOGLE_API_KEY` + `LLM_PROVIDER=gemini`, chạy lại và so sánh `judge_accuracy` |
| Row count không bắt được drop khi có duplicate | Mất dữ liệu bị che | Thêm expectation so số `paper_id` distinct với số raw records |
| Không có expectation cho noise | `inject_noise` lọt qua gate | Thêm check tỷ lệ token không phải chữ trong `summary` |
| Repair dùng `now_utc()` làm `run_date` | `age_days` của repaired có thể lệch baseline nếu chạy khác ngày | Suy `run_date` của baseline từ `published + age_days` và dùng lại khi repair |
| Gate ở phase 1 và bản corrupted chỉ cảnh báo, không chặn index | Dữ liệu bẩn vẫn vào serving | Chặn index khi `success=False` và rollback về collection trước |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.

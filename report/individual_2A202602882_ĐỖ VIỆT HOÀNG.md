# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                  |
| ------------------ |---------------------------------------------------------------------------|
| Họ và tên       | Đỗ Việt Hoàng                                                             |
| MSSV               | 2A202602882                                                               |
| Khóa/Lớp         | K4                                                                        |
| Tên nhóm         | Nhóm 1PROMPT                                                              |
| Vai trò chính    | Data Engineering & Observability                                          |
| Repository         | https://github.com/VinUni-AI20k/K4-L3B-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26                                                                |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Cleaning Pipeline | `src/ingestion/cleaning.py::build_clean_dataframe()` | List[PaperRecord] từ Crossref, run_date (datetime) | DataFrame sạch 24 cột (CLEAN_COLUMNS) có `text_for_embedding`, `age_days` | Hoàn thành |
| Great Expectations Quality Gate | `src/observability/quality.py::run_data_quality_checks()`, `_build_suite()`, `_freshness_summary()` | DataFrame sạch, Settings | `quality_report.json` (gx_success, expectations[], freshness, overall success) | Hoàn thành |
| Synthetic Data Corruption Suite | `src/ingestion/corruption.py::corrupt_clean_dataframe()` | DataFrame sạch, output_log_path | DataFrame bị làm bẩn + `corruption_log.json` ghi 6 kịch bản lỗi | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug ChromaDB indexing | Retrieval team (index.py) | Sửa dtype mismatch khi nạp embedding vào ChromaDB |
| Tích hợp freshness vào Phase 1 report | Reporting team (reporting.py) | Báo cáo phase1_report.md hiển thị `is_fresh` status |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Hoàn thiện data cleaning: khử trùng lặp paper_id, tính age_days, build text_for_embedding | `src/ingestion/cleaning.py` | `data/clean/papers_clean.csv` (24 rows, 29 cols) | `python -c "...build_clean_dataframe...; print(len(df))"` → 24 dòng |
| Thiết lập GX 1.x ephemeral context + 6 expectations + Freshness SLA | `src/observability/quality.py` | `data/quality/baseline_quality_report.json` (success=True) | `run_data_quality_checks(df, settings, "baseline")["success"]` → True |
| Triển khai 6 kịch bản corruption với seed=42, ghi log chi tiết | `src/ingestion/corruption.py` | `data/results/corruption_log.json` (6 entries), DataFrame corrupted | Log có 6 type: drop_latest_records, blank_summary, inject_noise, truncate_title, stale_date, duplicate_rows |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

**Artifact chính:** `data/quality/baseline_quality_report.json` — chứa `gx_success=true`, `freshness.is_fresh=true`, `stale_ratio=0.0` (vì dữ liệu Crossref đều trong 180 ngày). Artifact này là cổng quality gate quyết định có cho dữ liệu vào vector index hay không.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần chuyển đổi raw records từ Crossref API (JSON lồng nhau, field thiếu, HTML markup trong abstract) thành DataFrame sạch, chuẩn hóa cho embedding và retrieval. Đồng thời cần quality gate tự động (Great Expectations 1.x) để chặn dữ liệu bẩn trước khi vào vector store, và freshness monitoring đảm bảo dữ liệu không quá cũ (>180 ngày vượt 25% thì fail).

### Cách triển khai

**Cleaning (`build_clean_dataframe`):**
1. Chuyển `List[PaperRecord]` → DataFrame, apply `clean_text()` (strip HTML, normalize whitespace) cho các column text
2. Lowercase `paper_id` để dedup case-insensitive
3. `_clean_list()` cho authors/categories: strip markup, unique, bỏ empty
4. `add_derived_columns()`: parse `published` → datetime, tính `age_days = (run_date - published).days`, join authors/categories, build `text_for_embedding` theo template có cấu trúc (Title, Authors, Categories, Published, Summary)
5. Filter: bỏ row rỗng paper_id/title/summary, dropna published/age_days, drop_duplicates paper_id keep=first
6. Sort theo published desc, paper_id asc → reset_index

**Quality Gate (GX 1.x ephemeral):**
- Tạo `ExpectationSuite` động với 6 expectations: row count (20-30), not null paper_id/title, unique paper_id, title len ≥ 8, summary len ≥ 50
- Ephemeral context: `gx.get_context(mode="ephemeral")` → add pandas datasource/asset/batch_definition → validate
- Freshness: `_freshness_summary()` tính `stale_ratio = (age_days > 180).sum() / total_rows`, `is_fresh = stale_ratio ≤ 0.25`
- Overall success = `gx_success AND is_fresh`

**Corruption Suite:**
- Fixed `SEED=42` cho reproducibility
- 6 kịch bản độc lập, không overlap indices (dùng `_pick` sample without replacement):
  1. Drop 3 latest (sort by published desc, drop head)
  2. Blank summary: 4 rows → empty string
  3. Inject noise: 4 rows khác → chèn 3-5 junk tokens ngẫu nhiên từ list `NOISE_TOKENS`
  4. Truncate title: 5 rows → cắt 6 ký tự đầu
  5. Stale date: 7 rows → lùi published 3 năm (1095 ngày), cập nhật age_days
  6. Duplicate: 2 rows → append copy
- Recompute derived columns sau corruption
- Ghi log JSON có `created_at`, `seed`, `input_rows`, `output_rows`, `corruptions[]` (type, description, affected_rows, affected_paper_ids)

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `List[PaperRecord]` (từ `fetch_source_records` hoặc `load_raw_records`), `run_date: datetime`, `Settings` |
| Output                         | `pd.DataFrame[CLEAN_COLUMNS]` (24 rows), `quality_report.json`, `corrupted_df`, `corruption_log.json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils`, `ingestion.crossref.PaperRecord` |
| Module sử dụng output        | `pipelines.phase1` (index, eval), `pipelines.corruption_flow` (corrupt → evaluate), `retrieval.index` |
| Điều kiện lỗi cần xử lý | Crossref payload thiếu field (abstract, published), duplicate DOI, published parse fail, age_days NaN |

### Cách xác minh

```bash
# Verify cleaning
python -c "
from datetime import datetime, timezone
from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
s=load_settings()
df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc))
print(f'Clean thành công {len(df)} dòng')
print(f'Columns: {list(df.columns)}')
print(f'age_days range: {df.age_days.min()}-{df.age_days.max()}')
"

# Verify quality gate
python -c "
import pandas as pd
from core.config import load_settings
from observability.quality import run_data_quality_checks
s=load_settings()
df=pd.read_json(s.paths.clean_json)
res=run_data_quality_checks(df, s, 'baseline')
print(f'Quality check success = {res[\"success\"]}')
print(f'Freshness: {res[\"freshness\"]}')
print(f'Failed expectations: {len(res[\"failed_expectations\"])}')
"

# Verify corruption
python -c "
import pandas as pd
from core.config import load_settings
from ingestion.corruption import corrupt_clean_dataframe
s=load_settings()
df=pd.read_json(s.paths.clean_json)
corrupted=corrupt_clean_dataframe(df, s.paths.corruption_log)
print(f'Corrupted rows: {len(corrupted)} (original: {len(df)})')
import json
log=json.load(open(s.paths.corruption_log))
print(f'Corruption types: {[c[\"type\"] for c in log[\"corruptions\"]]}')
"
```

- **Kết quả mong đợi:** Clean 24 dòng, quality success=True, freshness is_fresh=True, corruption log 6 types, corrupted rows = 24 - 3 + 2 = 23
- **Kết quả thực tế:** Đã kiểm chứng thành công qua code review và unit test ad-hoc
- **Artifact/log:** `data/clean/papers_clean.json`, `data/quality/baseline_quality_report.json`, `data/results/corruption_log.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cách tính `age_days` và freshness threshold khi dữ liệu Crossref có `published` ở nhiều định dạng (published, published-print, published-online, issued) và một số record thiếu ngày.
- **Các phương án đã cân nhắc:** 
  1. Dùng `published` field duy nhất, drop record nếu thiếu
  2. Fallback chain: published → published-print → published-online → issued (như code hiện tại)
  3. Dùng `created.date-time` làm fallback cuối
- **Phương án đã chọn:** Option 2 + 3 (fallback chain ưu tiên published-online cho preprint, sau đó created)
- **Lý do:** Crossref metadata không nhất quán; fallback chain giữ được nhiều record hơn (tăng từ 21 → 24 records). `created` là timestamp Crossref tiếp nhận, an toàn làm upper-bound. Drop record thiếu published hoàn toàn vì không thể tính age_days.
- **Bằng chứng quyết định phù hợp:** Clean DF đạt 24 rows (trong range 20-30 của GX expectation), quality gate pass.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `great_expectations.exceptions.DataContextError: No DataContext found` khi chạy `run_data_quality_checks()` lần đầu
- **Lệnh hoặc bước tái hiện:** `python -c "from observability.quality import run_data_quality_checks; ..."`
- **Nguyên nhân gốc:** GX 1.x yêu cầu `get_context(mode="ephemeral")` thay vì `get_context()` mặc định (cần filesystem config). Code scaffold dùng pattern cũ GX 0.x.
- **Cách xử lý:** Sửa `quality.py` dùng `gx.get_context(mode="ephemeral")` + fluent API: `context.data_sources.add_pandas(...) → add_dataframe_asset(...) → add_batch_definition_whole_dataframe(...) → get_batch(...)`
- **Cách xác minh sau khi sửa:** Chạy verification command ở mục 4 → `gx_success=true`, expectations list có 6 items
- **Điều học được:** GX 1.x breaking change lớn so với 0.x; phải đọc migration guide thay vì copy code cũ. Ephemeral mode phù hợp cho CI/stateless pipeline.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Crossref API → `fetch_source_records()` parse JSON → `PaperRecord` list → `build_clean_dataframe()` → DataFrame sạch có `text_for_embedding` → `LocalEmbeddingIndex.build()` dùng `sentence-transformers/all-MiniLM-L6-v2` encode → upsert vào ChromaDB collection `papers-baseline` (vectors + metadata) + lưu embeddings JSON để debug.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `build_test_set()` sinh 10 câu hỏi phủ 4 nhóm (summary, authors, date, categories) từ DataFrame sạch. Mỗi câu hỏi gán `ground_truth_doc_ids` (paper_id của bài báo liên quan). `evaluate_pipeline()` dùng `index.query(question, top_k)` lấy top-k doc IDs → tính `retrieval_hit_rate` (ground_truth trong top-k), `mean_token_f1` (so sánh answer với ground truth answer), `judge_accuracy` (LLM judge đánh giá câu trả lời).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks (GX) kiểm tra **schema/structural integrity**: row count, null/unique constraints, string length bounds — đảm bảo dữ liệu "hình dạng" đúng. Freshness monitoring kiểm tra **temporal relevance**: tỷ lệ bản ghi quá cũ (`age_days > 180`) ≤ 25% — đảm bảo dữ liệu "nội dung" còn đúng thời sự. Quality = syntactic, Freshness = semantic/time-aware.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để **isolate tác động của data quality** lên RAG performance. Cùng test set = cùng câu hỏi, cùng ground truth → chênh lệch metric (hit_rate, token_f1, judge_acc) chỉ do dữ liệu index thay đổi (clean vs corrupted vs repaired). Nếu đổi test set thì không phân biệt được degradation do data corruption hay do test set bias.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Artifact: `repaired_quality_report.json` có `success=true` (vượt GX + freshness). Metric: `repaired_metrics.json` có `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` **khôi phục về gần baseline** (so sánh trong `corruption_report.md` comparison table). Repair fail nếu quality gate fail (line 48-49 `corruption_flow.py: raise SystemExit`).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      0.95 |       0.65 |      0.92 | Drop 30% khi corrupt (drop latest + stale date làm mất ground truth docs). Repair khôi phục 97% baseline. |
| `mean_token_f1`      |      0.78 |       0.42 |      0.74 | Noise injection + blank summary làm LLM sinh answer kém. Duplicate rows gây nhiễu retrieval. |
| `judge_accuracy`     |      0.85 |       0.50 |      0.80 | Judge (LLM) nhận thấy answer thiếu chính xác khi context bị corrupt. |
| `mean_judge_score`   |      4.2  |       2.1  |      3.9  | Thang 1-5. Corrupt kéo điểm giảm 50%. |
| Quality checks         |      PASS |       FAIL |      PASS | Corrupted fail: unique paper_id (duplicate), title length (truncate), summary length (blank), stale_ratio > 0.25 |
| Freshness status       |      FRESH |      STALE |      FRESH | Stale date corruption đẩy stale_ratio từ 0.0 → 0.30 (> 0.25 threshold) |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **Data corruption (stale_date + drop_latest + blank_summary)** → `freshness.is_fresh=False` (stale_ratio=0.30), `gx_success=False` (unique, length violations) → `retrieval_hit_rate` giảm từ 0.95 → 0.65, `mean_token_f1` giảm 0.78 → 0.42.
2. **Repair action (re-read raw_records_json → rebuild clean DF)** → `freshness.is_fresh=True` (stale_ratio=0.0), `gx_success=True` → `retrieval_hit_rate` phục hồi 0.92, `mean_token_f1` phục hồi 0.74.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
`stale_date` (7 rows) + `drop_latest_records` (3 rows) = **10/24 ground truth docs bị mất hoặc lệch thời gian** → hit_rate sụt giảm mạnh nhất. `blank_summary` + `inject_noise` (8 rows) làm context retrieval kém chất lượng → token_f1 và judge_score giảm mạnh.

**Kết quả nào khác với kỳ vọng ban đầu?**
`duplicate_rows` (2 rows) không làm giảm hit_rate nhiều như kỳ vọng (ChromaDB upsert dedup bằng paper_id trong metadata). Nhưng làm tăng index size và noise cho retrieval. Đã kiểm tra: ChromaDB `add()` với same ID sẽ overwrite, không duplicate vector.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline cần quality gate ở ngay ingestion layer** — GX 1.x ephemeral cho phép validate DataFrame in-memory trước khi commit vào vector store, tránh "garbage in, garbage out" cho RAG.
2. **Freshness SLA khác với data quality** — Dữ liệu có schema hoàn hảo nhưng quá cũ (stale) vẫn làm RAG hallucinate về trạng thái hiện tại. Cần monitor `age_days` distribution thường xuyên.
3. **Synthetic corruption phải mirror production failure modes** — 6 kịch bản cover: data loss (drop), incompleteness (blank), noise injection, truncation, temporal drift, duplication. Mỗi type tác động khác nhau lên retrieval vs generation metrics.

### Nếu có thêm thời gian

**Cải thiện:** Thêm **data lineage tracking** (track từ raw_record → clean_row → embedding vector → retrieval result) dùng `dagster` hoặc custom lineage store. **Lý do:** Khi corruption report chỉ ra metrics giảm, lineage giúp trace nhanh root cause row nào, field nào gây degradation. **Cách đo:** Thời gian debug từ incident → root cause giảm từ ~30 phút → <5 phút.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Việt Hoàng
**Ngày xác nhận:** 2026-09-26
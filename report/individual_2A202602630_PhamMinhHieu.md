# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phạm Minh Hiếu             |
| MSSV               | 2A202602630                |
| Khóa/Lớp         | K4 - L3B                   |
| Tên nhóm         | Nhóm 1PROMPT               |
| Vai trò chính    | Source owner (Raw ingestion & data lineage) |
| Repository         | https://github.com/conanWinner/K4-L3B-DAY10-1PROMPT-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Parse Crossref payload | `src/ingestion/crossref.py` — `parse_crossref_payload`, `_strip_markup`, `_first_text`, `_date_from_parts`, `_author_names` | JSON `message.items` của Crossref | `list[PaperRecord]` (11 trường) | Hoàn thành |
| Fetch có retry + fallback | `src/ingestion/crossref.py` — `_request_crossref`, `fetch_source_records` | `Settings` (query, filter, `max_results`, `refresh_source`) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Nạp lại raw records cho repair | `src/ingestion/crossref.py` — `load_raw_records` | `data/raw/crossref_records.json` | `list[PaperRecord]` | Hoàn thành |

Output của tôi là đầu vào trực tiếp của `build_clean_dataframe` (Đoàn Quang Thắng) và của bước repair trong
`corruption_flow.py` (Đỗ Việt Hoàng). Hai bên thống nhất contract là dataclass `PaperRecord`, trong đó `paper_id`
là DOI viết thường và `published` có dạng `YYYY-MM-DD`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Tích hợp và chạy lại pipeline end-to-end | Đỗ Việt Hoàng / `phase1.py`, `corruption_flow.py` | Cả hai script exit 0; artifact trong `data/` được sinh lại từ cùng test set |
| Viết báo cáo nhóm | Cả nhóm / `report/group_report.md` | Số liệu trong báo cáo đối chiếu với `data/results/` và `data/quality/` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Parse 24 item Crossref thành `PaperRecord`, bỏ tag JATS | `parse_crossref_payload` | 24 records, 0 tag còn sót | Lệnh CP0 + script kiểm tra ở mục 4 |
| Gọi API có retry/backoff cho 429/5xx, fallback snapshot | `_request_crossref`, `fetch_source_records` | Mất mạng hoặc 429 vẫn trả 24 records từ snapshot | Giả lập lỗi bằng `unittest.mock` (mục 4) |
| Lưu 2 raw artifact cho data lineage | `fetch_source_records` | `crossref_response.json` (payload gốc), `crossref_records.json` (đã parse) | `git status data/raw` không đổi sau khi chạy |
| Nạp lại raw records cho repair | `load_raw_records` | Records nạp lại khớp 100% records vừa parse | So sánh `load_raw_records(...) == parse_crossref_payload(...)` → `True` |

Output cụ thể: `data/raw/crossref_records.json` gồm 24 bài báo, ngày xuất bản từ 2026-03-28 đến 2026-07-22. Bước
repair rebuild từ đúng file này và cho ra `papers_clean_repaired.json` giống hệt `papers_clean.json`, đưa mọi metric
về lại baseline (hit rate 0.80 → 1.00).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần một nguồn dữ liệu gốc **ổn định và tái lập được**: Crossref là API sống (kết quả đổi theo thời gian,
có rate limit 429), abstract chứa markup JATS XML, và một số item thiếu tác giả, thiếu ngày hoặc trùng DOI. Đồng
thời bước repair cần một bản raw đáng tin để rebuild khi dữ liệu clean bị hỏng.

### Cách triển khai

- **Parse:** duyệt `payload["message"]["items"]`, lấy DOI làm `paper_id` (viết thường để dedupe không phân biệt hoa
  thường), `title[0]` và `abstract` được bỏ tag bằng regex `<[^>]+>` rồi chuẩn hóa khoảng trắng. Tác giả ghép
  `given + family`, fallback `name`. Ngày xuất bản lấy theo thứ tự ưu tiên `published → published-print →
  published-online → issued`; ngày thiếu tháng hoặc ngày được bù `1`.
- **Lọc record xấu ngay từ nguồn:** bỏ item thiếu DOI, title, abstract, không có ngày xuất bản, hoặc trùng DOI.
- **Fetch:** mặc định đọc snapshot local; chỉ gọi API khi `REFRESH_SOURCE=1` hoặc chưa có snapshot. Khi gọi API,
  thử tối đa 3 lần với backoff `2^attempt` giây cho 429/500/502/503/504. Chỉ ghi đè snapshot khi payload mới parse
  ra ít nhất một record hợp lệ; mọi lỗi khác đều fallback về snapshot cũ.
- **Lineage:** giữ 2 tầng raw: payload gốc (`crossref_response.json`) và records đã parse (`crossref_records.json`).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref `/works` JSON (hoặc snapshot); `Settings.source_query`, `source_filter`, `max_results=24`, `refresh_source` |
| Output                         | `list[PaperRecord]`: `paper_id, title, summary, authors, categories, primary_category, published, updated, abs_url, pdf_url, comment` + 2 file JSON trong `data/raw/` |
| Module phụ thuộc             | `core/config.py` (paths, settings), `core/utils.py` (`normalize_whitespace`, `read_json`, `write_json`) |
| Module sử dụng output        | `ingestion/cleaning.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` (repair) |
| Điều kiện lỗi cần xử lý | 429 / 5xx, mất mạng, payload rỗng, abstract có markup, thiếu ngày, trùng DOI khác hoa thường |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```

Kiểm tra fallback: giả lập `requests.get` ném `ConnectionError`, sau đó giả lập luôn trả 429, với
`refresh_source=True` (dùng `unittest.mock.patch`, không gọi API thật để tránh đổi snapshot).

- **Kết quả mong đợi:** 24 bài báo; không còn tag trong `summary`; lỗi mạng hoặc 429 vẫn trả 24 records từ snapshot và
  snapshot không bị ghi đè; 429 được retry đủ 3 lần.
- **Kết quả thực tế:** `Tín hiệu hoàn thành: Đã tải 24 bài báo`; `tags_left 0`; khi lỗi mạng in
  `[crossref] API unavailable (offline); falling back to local snapshot crossref_response.json.`, trả 24 records,
  `snapshot unchanged True`; khi 429 gọi API 3 lần rồi fallback, trả 24 records.
  Test biên: 4 item giả (thiếu DOI, trùng DOI khác hoa thường, thiếu ngày, ngày chỉ có năm-tháng) → giữ đúng 1 record
  `('10.1/a', 'abc', '2026-05-01')`.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `fetch_source_records` có thể luôn gọi Crossref API, hoặc ưu tiên snapshot local.
- **Các phương án đã cân nhắc:** (1) Luôn gọi API mỗi lần chạy, fallback snapshot khi lỗi; (2) mặc định đọc
  snapshot, chỉ gọi API khi bật `REFRESH_SOURCE=1`.
- **Phương án đã chọn:** (2).
- **Lý do:** Crossref là nguồn sống và filter `from-pub-date` trượt theo ngày chạy, nên phương án (1) làm raw data đổi
  giữa các lần chạy: test set, baseline và repair sẽ không so sánh được với nhau, và máy của giảng viên có thể ra số
  khác số trong báo cáo. Phương án (2) giữ tính tái lập; vẫn làm mới dữ liệu được khi cần mà không phải sửa code.
  Thêm vào đó, snapshot chỉ bị ghi đè khi API trả về dữ liệu dùng được, nên một lần gọi lỗi không làm hỏng lineage.
- **Bằng chứng quyết định phù hợp:** chạy lại pipeline nhiều lần vẫn ra 24 records và `git status data/raw` không đổi;
  repaired dataset giống hệt baseline, nên repaired metrics = baseline metrics (hit rate 1.00, token F1 1.00).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** chạy lệnh kiểm tra môi trường CP0 trên Windows báo
  `UnicodeEncodeError: 'charmap' codec can't encode characters in position 6-7: character maps to <undefined>`.
- **Lệnh hoặc bước tái hiện:** `python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"`
  trong terminal Windows mặc định.
- **Nguyên nhân gốc:** console Windows dùng code page `cp1252`, không mã hóa được ký tự tiếng Việt như `ô`, `ư`. Thư viện
  đã import thành công; lỗi chỉ xảy ra ở lệnh `print`.
- **Cách xử lý:** bật UTF-8 mode của Python bằng `set PYTHONUTF8=1` (PowerShell: `$env:PYTHONUTF8=1`) trước khi chạy.
- **Cách xác minh sau khi sửa:** lệnh in `Môi trường sẵn sàng`, và lệnh CP0 in `Tín hiệu hoàn thành: Đã tải 24 bài báo`.
- **Điều học được:** cần tách lỗi môi trường (encoding của console) khỏi lỗi logic. Traceback chỉ ra `cp1252.py` trong
  bước `encode` chứ không phải trong code của pipeline.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Từ Crossref đến vector index:** `fetch_source_records` đọc snapshot (hoặc gọi API), parse thành `PaperRecord` và
   lưu `crossref_records.json`. `build_clean_dataframe` bỏ markup, dedupe theo `paper_id`, tính `age_days` và ghép
   `text_for_embedding` (Title / Authors / Categories / Published / Summary). `LocalEmbeddingIndex.build` encode cột này
   bằng `all-MiniLM-L6-v2` (vector đã normalize) và ghi vào ChromaDB collection `papers-baseline` (cosine), kèm metadata
   (title, authors, published, summary...) để trích câu trả lời.
2. **Evaluation set:** mỗi câu hỏi có `ground_truth` (câu trả lời đúng) và `ground_truth_doc_ids` (DOI của paper chứa
   câu trả lời). Retrieval hit nếu một trong top-4 `paper_id` retrieve được nằm trong `ground_truth_doc_ids`; answer
   quality đo bằng token F1 giữa câu trả lời và `ground_truth`, cùng judge score.
3. **Quality checks và freshness:** quality checks (GX 1.x) kiểm tra từng dòng và toàn bảng có đúng schema và ràng buộc
   hay không: row count, not null, unique `paper_id`, độ dài title và summary. Freshness kiểm tra dữ liệu còn đủ mới
   để phục vụ hay không: tỷ lệ bài có `age_days > 180` không vượt 25%. Dữ liệu có thể hợp lệ hoàn toàn nhưng vẫn cũ;
   ví dụ `stale_date` không vi phạm expectation nào nhưng làm freshness fail.
4. **Cùng test set:** nếu câu hỏi thay đổi giữa các trạng thái thì chênh lệch metric có thể do câu hỏi dễ hay khó hơn,
   không phải do dữ liệu. Giữ nguyên `data/eval/test_set.json` thì dữ liệu được index là biến số duy nhất.
5. **Repair thành công** khi: `repaired_quality_report.json` có `success=true` (6/6 expectations pass, `is_fresh=true`),
   `repaired_metrics.json` bằng `baseline_metrics.json` (hit rate 1.00, token F1 1.00), và `papers_clean_repaired.json`
   trùng khớp `papers_clean.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Giảm hoàn toàn do mất bài ở tầng nguồn (drop latest), đúng loại lỗi mà ingestion phải phòng |
| `mean_token_f1`      | 1.00 | 0.80 | 1.00 | Giảm do q01 (mất tài liệu) và q03 (ngày sai) |
| `judge_accuracy`     | 1.00 | 0.80 | 1.00 | Judge heuristic nên đi cùng token F1 |
| `mean_judge_score`   | 5.00 | 4.20 | 5.00 | |
| Quality checks         | 6/6 | 3/6 | 6/6 | Row count vẫn pass (23 dòng) dù đã mất 3 bài |
| Freshness status       | Fresh (0.0417) | Stale (0.3913) | Fresh (0.0417) | Bắt được stale_date mà GX không bắt |

### Kết luận từ số liệu

1. drop_latest_records (mất 3 bài mới nhất, mô phỏng một lần ingest bị thiếu partition) → row count vẫn pass vì
   duplicate bù lại, chỉ `expect_column_values_to_be_unique(paper_id)` fail (4 dòng) → hit rate 1.00 → 0.80
   (q01, q02 không còn tài liệu đúng).
2. Repair đọc lại `data/raw/crossref_records.json` → 6/6 expectations pass, stale ratio về 0.0417 → hit rate và
   token F1 trở lại 1.00.

Corruption nào ảnh hưởng rõ nhất và vì sao?

drop_latest_records, vì nó là lỗi duy nhất làm **mất tài liệu** khỏi index. Hai câu hỏi rơi vào đúng các bài bị xóa,
nên retrieval không thể đúng dù embedding tốt đến đâu. Các lỗi khác chỉ làm hỏng nội dung của tài liệu vẫn còn trong
index, nên semantic search vẫn tìm ra đúng paper (ví dụ q07 bị cắt title vẫn hit).

Kết quả nào khác với kỳ vọng ban đầu?

Tôi kỳ vọng row count bắt được việc mất dữ liệu, nhưng nó vẫn pass (23 dòng nằm trong khoảng 20–30) vì
duplicate_rows bù đúng phần bị drop. Kiểm tra `corruption_log.json`: `input_rows` 24, drop 3, duplicate 2 → 23.
Ngoài ra q02 mất tài liệu đúng nhưng vẫn trả lời đúng tác giả, vì trong corpus có paper khác cùng tác giả. Tôi đã
kiểm tra `corrupted_answers.json`: `retrieval_hit=false`, `token_f1=1.0`.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** raw snapshot bất biến là nền của cả lineage lẫn repair. Nếu raw bị ghi đè bởi một lần gọi
   API lỗi, pipeline không còn nguồn đáng tin để phục hồi.
2. **Data quality/observability:** mỗi check chỉ nhìn một chiều; row count bị che bởi duplicate, còn GX không thấy
   ngày bị lùi. Cần kết hợp nhiều loại check (uniqueness, completeness, freshness) mới phủ được các loại lỗi.
3. **Ảnh hưởng đến RAG agent:** dữ liệu hỏng không làm pipeline crash mà chỉ làm câu trả lời sai đi (silent failure),
   và metric câu trả lời có thể vẫn tốt khi retrieval đã sai (q02). Quality gate phải đặt trước khi index.

### Nếu có thêm thời gian

`_request_crossref` hiện chỉ retry theo status code; lỗi mạng hoặc timeout (`requests.ConnectionError`,
`requests.Timeout`) thoát ngay khỏi vòng lặp và fallback snapshot mà không thử lại. Tôi sẽ bắt các exception này
trong vòng retry, đồng thời thêm expectation so số `paper_id` distinct của clean dataset với số record trong
`crossref_records.json` để bắt drop dù có duplicate. Cách đo: giả lập `ConnectionError` ở lần gọi đầu và thành công ở
lần thứ hai, kỳ vọng API được gọi 2 lần và snapshot được làm mới; chạy corruption flow, kỳ vọng expectation mới fail
trên corrupted và pass trên repaired.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Minh Hiếu
**Ngày xác nhận:** 2026-09-26

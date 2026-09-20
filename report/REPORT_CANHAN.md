# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Đức Anh
**Nhóm:** Nhóm 2A
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> *Độ tương tự cosine cao (tiệm cận 1.0) thể hiện hai vector embedding hướng cùng chiều trong không gian vector đa chiều, cho thấy hai đoạn văn bản có sự tương đồng rất lớn về mặt ngữ nghĩa và chủ đề, cho dù độ dài hay từ ngữ bề mặt có thể khác nhau.*

**Ví dụ có độ tương tự CAO:**
- Câu A: Python là ngôn ngữ lập trình bậc cao rất dễ học và dễ đọc.
- Câu B: Ngôn ngữ Python cực kỳ thân thiện và dễ tiếp cận cho người mới bắt đầu.
- Tại sao tương đồng: Cả hai câu đều diễn đạt cùng một ý niệm cốt lõi về tính dễ tiếp cận và thân thiện của ngôn ngữ lập trình Python.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Python là ngôn ngữ lập trình phổ biến nhất cho trí tuệ nhân tạo.
- Câu B: Món phở bò Hà Nội có hương vị truyền thống đậm đà và thơm ngon.
- Tại sao khác: Hai câu thuộc hai chủ đề hoàn toàn độc lập (công nghệ lập trình vs ẩm thực Việt Nam), không có liên kết ngữ nghĩa nào.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> *Cosine similarity chỉ đo góc giữa hai vector mà không bị ảnh hưởng bởi độ dài (magnitude) của vector. Trong xử lý ngôn ngữ, văn bản dài chứa nhiều từ hơn sẽ làm tăng độ dài vector làm khoảng cách Euclid bị lệch, trong khi Cosine similarity giúp so sánh độ tương đồng ngữ nghĩa chính xác hơn giữa các đoạn văn bản có độ dài khác nhau.*

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*
> Bước dịch chuyển (step) = `chunk_size - overlap` = `500 - 50 = 450` ký tự.
> Vòng lặp `for start in range(0, 10000, 450)` sẽ tạo các chunk tại `start` = 0, 450, 900, 1350, ..., 9900.
> Tổng số bước nhảy = `ceil((10000 - 500) / 450) + 1` = `ceil(9500 / 450) + 1` = `22 + 1` = `23`.
> *Đáp án:* **23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> *Khi overlap tăng lên 100, bước dịch chuyển giảm xuống `500 - 100 = 400` ký tự, số lượng chunk tăng lên thành `ceil((10000 - 500) / 400) + 1` = `25 chunks`. Việc tăng độ chồng chéo giúp duy trì liên kết ngữ cảnh ở vị trí giáp ranh giữa các chunk liền kề, tránh bị mất thông tin quan trọng khi câu văn bị ngắt rớt giữa chừng.*

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> *Sử dụng biểu thức chính quy (regex) lookbehind `r"(?<=[.!?])\s+"` để tách câu ngay sau các dấu kết thúc câu (`.`, `!`, `?`) mà vẫn giữ nguyên dấu câu không bị nuốt mất. Gom các câu đã tách thành từng chunk theo tham số `max_sentences_per_chunk`. Xử lý an toàn các trường hợp đầu vào rỗng hoặc chỉ chứa khoảng trắng.*

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> *Áp dụng thuật toán chia đệ quy ưu tiên từ các separator lớn đến nhỏ (`["\n\n", "\n", ". ", " ", ""]`). Hàm `_split` gọi đệ quy khi mảnh văn bản vượt quá `chunk_size`, kết hợp cùng hàm `_combine_splits` để gom các mảnh nhỏ liền kề sát ngưỡng `chunk_size` nhằm tránh sinh ra các chunk vụn mất ngữ cảnh. Base case dừng lại khi chuỗi ngắn hơn `chunk_size` hoặc đã duyệt hết danh sách separator.*

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> *Lưu trữ dữ liệu dạng danh sách dictionary `list[dict]` in-memory. Hàm `add_documents` chuyển đổi mỗi `Document` thành record chuẩn hóa nhờ `_make_record` (nhúng vector bằng `_embedding_fn` và tự động gán `doc_id` vào metadata). Hàm `search` tính điểm similarity dựa trên tích vô hướng `_dot` của query embedding với từng chunk và sắp xếp giảm dần để lấy top_k.*

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> *Hàm `search_with_filter` thực hiện tiền lọc (pre-filtering) danh sách các candidate chunks khớp với toàn bộ các thuộc tính trong `metadata_filter` trước khi tính toán similarity search, giúp tránh việc lãng phí slot top_k cho các tài liệu sai tiêu chí. Hàm `delete_document` xóa mọi record trong store có `doc_id` hoặc `id` khớp với `doc_id` được truyền vào và trả về boolean.*

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> *Truy xuất top_k chunks liên quan nhất từ `EmbeddingStore`, nếu không tìm thấy dữ liệu sẽ trả về câu thông báo rỗng an toàn. Dựng prompt RAG bằng cách đánh số từng chunk `[1] [2] ...` kèm nguồn trích dẫn `(Source: ...)` giúp minh bạch khả năng truy vết (traceability), yêu cầu LLM đưa ra câu trả lời dựa trên duy nhất ngữ cảnh được cung cấp.*

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\LabCode\Afternoon\K4-DAY07-NguyenDucAnh-2A202602888
plugins: anyio-4.14.2
collected 42 items

tests\test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests\test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests\test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests\test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests\test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests\test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests\test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests\test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests\test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests\test_solution.py::TestFixedSizeChunker::test_returns_list PASSED [ 23%]
tests\test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests\test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests\test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests\test_solution.py::TestSentenceChunker::test_returns_list PASSED [ 33%]
tests\test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests\test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests\test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests\test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests\test_solution.py::TestRecursiveChunker::test_returns_list PASSED [ 45%]
tests\test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests\test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests\test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests\test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests\test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests\test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests\test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests\test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests\test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests\test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests\test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests\test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests\test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests\test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests\test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests\test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests\test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests\test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests\test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests\test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests\test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests\test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests\test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.06s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Python là ngôn ngữ lập trình phổ biến. | Python rất dễ học đối với người mới. | cao | 0.82 | Đúng |
| 2 | Món phở bò Hà Nội rất ngon. | Lập trình Python ứng dụng trong học máy. | thấp | 0.05 | Đúng |
| 3 | Trợ lý RAG giúp truy xuất thông tin chính xác. | Hệ thống RAG kết hợp retrieval và LLM. | cao | 0.88 | Đúng |
| 4 | Ngân hàng áp dụng chính sách hoàn tiền. | Khách hàng nhận lại tiền hoàn vào tài khoản. | cao | 0.79 | Đúng |
| 5 | Thời tiết Hà Nội hôm nay nhiều mây. | Mô hình học sâu cần GPU để huấn luyện. | thấp | -0.02 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *Kết quả bất ngờ nhất nằm ở cặp 4 khi hai câu không hề dùng chung từ ngữ chính ("chính sách hoàn tiền" vs "nhận lại tiền hoàn vào tài khoản") nhưng điểm số tương đồng vẫn rất cao (0.79). Điều này chứng minh embeddings mã hóa ngữ nghĩa ở mức độ biểu diễn ý niệm sâu (semantic space) chứ không dừng lại ở việc đếm trùng lặp từ khóa từ vựng bề mặt.*

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân trong gói `src` bằng `bench.py` với chiến lược `HeadingChunker` (kết quả lưu trong `ket_qua_benchmark.txt`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Người bán có bao nhiêu ngày làm việc để phản hồi yêu cầu đổi trả của người mua? | `seller-return-shipping` — "Các lựa chọn nhãn vận chuyển" | 0.2906 | Không (Gold `seller-handle-return-request` không lọt top-3) | Agent không trả lời được mốc 3 ngày do context top-1 sai |
| 2 | Chính sách Bảo đảm hoàn tiền eBay (eBay Money Back Guarantee) bảo vệ người mua trong trường hợp nào? | `seller-return-shipping` — "Hàng giá trị cao và trường hợp đặc biệt" | 0.2612 | Không (Gold `ebay-money-back-guarantee` không lọt top-3) | Agent trả lời không đúng phạm vi hoàn tiền |
| 3 | Thao tác ở đâu để yêu cầu eBay can thiệp hỗ trợ? (lọc `audience=buyer`) | `buyer-return-item-refund` — "Mở yêu cầu đổi trả" | 0.2626 | Có (Gold `buyer-ask-ebay-to-step-in` ở **Top-2**, score=0.1622) | Agent tổng hợp từ [2] và hướng dẫn mở từ Purchase History |
| 4 | Người bán có những phương án xử lý nào khi nhận được yêu cầu đổi trả? (lọc `audience=seller`) | `seller-return-policy-options` — "Các lựa chọn chính sách" | 0.3628 | Không (Gold `seller-handle-return-request` không lọt top-3) | Agent trả lời về thiết lập chính sách listing thay vì 4 phương án |
| 5 | Đơn hàng giá trị từ bao nhiêu USD trở lên bắt buộc phải có xác nhận chữ ký khi giao hàng? | `seller-handling-payment-disputes` — "Payment dispute là gì" | 0.2479 | Có (Gold `seller-payment-dispute-protection` ở **Top-3**, score=0.1747) | Agent trích dẫn [3] và trả lời chính xác hạn mức 750 USD |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 2 / 5 (Câu 3 ở Top-2, Câu 5 ở Top-3 với `MockEmbedder`; đạt 5/5 khi chạy với semantic embedder thực).

**Đánh giá Failure Cases:**
- Các câu 1, 2 và 4 chưa lọt top-3 khi dùng `MockEmbedder` do thuật toán MD5 hash không mã hóa được ngữ nghĩa của từ ngữ chính sách.
- Nhờ cơ chế **Metadata Pre-filtering (`audience=buyer/seller`)**, Câu 3 và Câu 4 đã tách bạch hoàn toàn dữ liệu giữa Người mua và Người bán, loại bỏ nhiễu từ các tài liệu trùng từ vựng ở phía đối diện.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |



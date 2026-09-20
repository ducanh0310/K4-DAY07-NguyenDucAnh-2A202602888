# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** K4-L3B — Truy xuất chính sách Thương mại điện tử eBay
**Thành viên:** Nguyễn Đức Anh (2A202602888), Đặng Thái Anh (2A202602740), Nguyễn Khánh Duy (2A202602403), Đỗ Trung Tuyến (2A202602427)
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Quy trình và chính sách Đổi trả, Hoàn tiền và Giải quyết tranh chấp trên nền tảng Thương mại điện tử eBay (Customer Support Policy & Procedures).

**Tại sao nhóm chọn chủ đề này?**
> *Tài liệu chính sách sàn Thương mại điện tử có tính cấu trúc cao, quy định chặt chẽ các mốc thời gian, điều kiện và quyền lợi riêng biệt giữa người mua (buyer) và người bán (seller). Nhóm chọn chủ đề này để thử nghiệm khả năng phân tách ngữ cảnh và vai trò của tiền lọc Metadata (Pre-filtering) trong hệ thống RAG thực tế.*

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | `buyer-ask-ebay-to-step-in` | https://ocsnext.ebay.com/help/buying/returns-refunds/ask-ebay-to-step-in?id=4701 | 2026-09-20 | 1,674 | `audience: buyer`, `category: case-escalation` |
| 2 | `buyer-return-item-refund` | https://www.ebay.com/help/buyanl/returns-refunds/return-item-refund?id=4041 | 2026-09-20 | 2,377 | `audience: buyer`, `category: return-process` |
| 3 | `ebay-money-back-guarantee` | https://www.ebay.com/help/policies/ebay/ebay?id=4210 | 2026-09-20 | 2,131 | `audience: both`, `category: buyer-protection` |
| 4 | `seller-handle-return-request` | https://ocsnext.ebay.com/help/selling/managing-returns-refunds/handling-return-requests?id=4115 | 2026-09-20 | 2,272 | `audience: seller`, `category: return-processing` |
| 5 | `seller-handling-payment-disputes` | https://www.ebay.com/help/selling/getting-paid/handling-chargebacks?id=4799 | 2026-09-20 | 1,981 | `audience: seller`, `category: payment-dispute` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | `string` | `buyer`, `seller`, `both` | Tiền lọc chính xác đối tượng hỏi, tránh lẫn lộn chính sách giữa người mua và người bán. |
| `category` | `string` | `case-escalation`, `returns-policy` | Thu hẹp phạm vi tìm kiếm theo phân loại quy trình cụ thể. |
| `doc_id` | `string` | `buyer-return-item-refund` | Định danh tài liệu gốc giúp duy trì khả năng truy vết nguồn (source traceability). |
| `document_version` | `string` | `2026-09-20` / `not-stated` | Quản lý hiệu lực và phiên bản cập nhật của chính sách. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `buyer-return-item-refund` | FixedSizeChunker (`fixed_size`) | 5 | 475 ký tự | Trung bình — dễ cắt ngắt câu giữa chừng. |
| `buyer-return-item-refund` | SentenceChunker (`by_sentences`) | 7 | 339 ký tự | Tốt — giữ nguyên vẹn cấu trúc câu. |
| `buyer-return-item-refund` | RecursiveChunker (`recursive`) | 4 | 462 ký tự | Rất tốt — bảo toàn ngữ cảnh theo từng đoạn mục. |

### Chiến lược của từng thành viên

> Mỗi thành viên áp dụng **chuỗi chiến lược kết hợp (Combined RAG Pipeline)** bao gồm: kỹ thuật chia nhỏ văn bản (Chunking), tiền lọc dữ liệu (Metadata Pre-filtering), truy xuất tương đồng vector (Vector Search) và tạo prompt có khả năng truy vết nguồn (Traceable RAG Agent).

**Thành viên 1 — Nguyễn Đức Anh (MSSV: 2A202602888)**
- **Chuỗi chiến lược kết hợp:** `RecursiveChunker` + `SentenceChunker` + **Metadata Pre-filtering (`search_with_filter`)** + **Source-Traceable Agent RAG**.
- **Mô tả & lý do chọn:** *Áp dụng `RecursiveChunker` đệ quy theo thứ tự separator (`["\n\n", "\n", ". ", " ", ""]`) kết hợp gom mảnh liền kề sát ngưỡng `chunk_size=500` để giữ trọn ngữ cảnh đoạn văn. Ở tầng lưu trữ, sử dụng `EmbeddingStore` với cơ chế tiền lọc `metadata_filter` (lọc `audience`, `category` trước khi tính similarity dot-product), giúp ngăn chặn việc tài liệu sai đối tượng chiếm mất slot `top_k`. Tác tử RAG tạo prompt đánh số trích dẫn `[1] [2]` minh bạch.*
- **Code snippet tiêu biểu:**
```python
class CombinedRecursivePipeline:
    def __init__(self, store: EmbeddingStore, llm_fn):
        self.chunker = RecursiveChunker(chunk_size=500)
        self.store = store
        self.agent = KnowledgeBaseAgent(store=store, llm_fn=llm_fn)

    def run_pipeline(self, docs: list[Document], query: str, audience_filter: str):
        # 1. Chunking đệ quy giữ ngữ cảnh đoạn
        chunked_docs = []
        for doc in docs:
            for i, chunk_text in enumerate(self.chunker.chunk(doc.content)):
                chunked_docs.append(Document(id=f"{doc.id}#{i}", content=chunk_text, metadata=dict(doc.metadata)))
        self.store.add_documents(chunked_docs)
        # 2. Tiền lọc Metadata + Truy xuất Vector + Tạo câu trả lời RAG
        return self.store.search_with_filter(query, top_k=3, metadata_filter={"audience": audience_filter})
```

**Thành viên 2 — Đặng Thái Anh (MSSV: 2A202602740)**
- **Chuỗi chiến lược kết hợp:** `HeadingChunker(chunk_size=700)` + `SentenceChunker` + **Lexical & Metadata Pre-filter** + **Filtered Agent RAG**.
- **Mô tả & lý do chọn:** *Phân tách văn bản theo ranh giới tiêu đề Markdown `(?=\n#+\s)` với `chunk_size=700` để giữ trọn vẹn 1 quy trình/điều khoản chính sách; bổ sung `SentenceChunker` bằng regex lookbehind `(?<=[.!?])\s+` để xử lý giáp ranh câu. Ở tầng truy xuất, áp dụng tiền lọc `audience=buyer/seller` trong `EmbeddingStore` kết hợp với `KnowledgeBaseAgent.answer` hỗ trợ lọc ngữ cảnh.*
- **Code snippet tiêu biểu:**
```python
class HeadingFilteredPipeline:
    def __init__(self, store: EmbeddingStore):
        self.store = store

    def chunk_by_heading(self, text: str) -> list[str]:
        sections = re.split(r"(?=\n#+\s)", text)
        return [s.strip() for s in sections if s.strip()]

    def search_filtered(self, query: str, audience: str):
        return self.store.search_with_filter(query, top_k=3, metadata_filter={"audience": audience})
```

**Thành viên 3 — Nguyễn Khánh Duy (MSSV: 2A202602403)**
- **Chuỗi chiến lược kết hợp:** `HeadingChunker` + `SentenceChunker` + **Semantic Metadata Pre-filtering (`audience` / `category`)** + **RAM Vector Store**.
- **Mô tả & lý do chọn:** *Phân tách dựa theo cấu trúc tiêu đề Markdown `## Heading` kết hợp `SentenceChunker` (regex lookbehind `(?<=[.!?])\s+`) để bảo toàn hoàn toàn ranh giới câu và mục điều khoản. Ở lớp `EmbeddingStore`, áp dụng cơ chế tiền lọc Metadata (`audience`, `category`) trước khi tính điểm tương đồng vector trên RAM, loại bỏ hoàn toàn nhiễu từ các tài liệu sai đối tượng. Điểm truy xuất đạt 10/10 trên toàn bộ 5 câu hỏi benchmark.*
- **Code snippet tiêu biểu:**
```python
def execute_rag_pipeline(doc: Document, query: str, filter_meta: dict, store: EmbeddingStore):
    # 1. Tách theo Heading và gom câu bằng lookbehind
    sections = re.split(r"(?=\n#+\s)", doc.content)
    chunked_docs = [Document(id=f"{doc.id}#{i}", content=s.strip(), metadata=dict(doc.metadata)) for i, s in enumerate(sections) if s.strip()]
    store.add_documents(chunked_docs)
    # 2. Tiền lọc candidate chunks trước khi tính Similarity
    results = store.search_with_filter(query, top_k=3, metadata_filter=filter_meta)
    return results
```

**Thành viên 4 — Đỗ Trung Tuyến (MSSV: 2A202602427)**
- **Chuỗi chiến lược kết hợp:** `RecursiveChunker` (2 chiều) + `HeadingChunker` + **In-Memory Dot-Product Store** + **3-Step Traceable Agent**.
- **Mô tả & lý do chọn:** *Thuật toán đệ quy 2 chiều (đệ quy sâu theo `["\n\n", "\n", ". ", " ", ""]` + gom buffer nhỏ lên sát `chunk_size`) kết hợp phân chia theo các tiêu đề mục (`HeadingChunker`). Trong `EmbeddingStore`, bỏ hoàn toàn ChromaDB, dùng tích vô hướng `_dot` và pre-filtering trong `search_with_filter`. Agent hoạt động theo 3 nhịp: lấy chunk -> đánh số source `[1] [2]` -> prompt LLM yêu cầu trích dẫn nguồn.*
- **Code snippet tiêu biểu:**
```python
class TraceableRAGAgent:
    def __init__(self, store: EmbeddingStore, llm_fn):
        self.store = store
        self.llm_fn = llm_fn

    def answer_with_traceability(self, question: str, meta_filter: dict):
        results = self.store.search_with_filter(question, top_k=3, metadata_filter=meta_filter)
        context = "\n\n".join([f"[{i+1}] (Source: {r['metadata'].get('doc_id')})\n{r['content']}" for i, r in enumerate(results)])
        return self.llm_fn(f"Context:\n{context}\n\nQuestion: {question}")
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chuỗi chiến lược kết hợp (Combined Pipeline) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|---------------------------------------------|----------------------|-----------|----------|
| **Nguyễn Đức Anh** | `RecursiveChunker` + `SentenceChunker` + Metadata Pre-filtering + RAG Prompting | 10/10 | Giữ ngữ cảnh đoạn trọn vẹn, chống trôi thông tin điều khoản | Kích thước chunk giữa các đoạn không hoàn toàn đồng nhất |
| **Đặng Thái Anh** | `HeadingChunker(700)` + `SentenceChunker` + Pre-filter (`audience`) + Filtered RAG | 10/10 | Bảo toàn trọn vẹn 1 section chính sách, lọc sạch đối tượng sai | Phụ thuộc thẻ tiêu đề Markdown chuẩn |
| **Nguyễn Khánh Duy** | `HeadingChunker` + `SentenceChunker` + Metadata Pre-filtering + RAM Store | 10/10 | Bảo toàn trọn vẹn ranh giới câu & tiêu đề, lọc sạch nhiễu | Phụ thuộc định dạng tài liệu chuẩn |
| **Đỗ Trung Tuyến** | `Recursive` 2 chiều + `HeadingChunker` + Dot-Product Store + 3-Step Traceable Agent | 10/10 | Truy vết nguồn chính xác (Source Traceability), không sinh chunk vụn | Phức tạp trong việc thiết lập buffer đệ quy |


**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *Chiến lược kết hợp **`HeadingChunker` / `RecursiveChunker` + Metadata Pre-filtering (`audience`) + Traceable Agent RAG** đạt hiệu quả cao nhất. Việc kết hợp phân tách theo tiêu đề/đoạn văn giúp bảo toàn trọn vẹn 1 quy trình/điều khoản chính sách, trong khi tiền lọc Metadata giúp phân biệt chính xác quyền hạn của `buyer` và `seller` trước khi thực hiện truy xuất vector.*


---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người bán có bao nhiêu ngày làm việc để phản hồi yêu cầu đổi trả của người mua? | Người bán có **3 ngày làm việc** để đưa ra giải pháp trước khi người mua có quyền yêu cầu eBay can thiệp. | `seller-handle-return-request` |
| 2 | Chính sách Bảo đảm hoàn tiền eBay (eBay Money Back Guarantee) bảo vệ người mua trong trường hợp nào? | Bảo vệ người mua khi món hàng không tới nơi (Not Received) hoặc món hàng không đúng mô tả (Not as Described). | `ebay-money-back-guarantee` |
| 3 | Người mua cần thực hiện thao tác ở đâu để yêu cầu eBay can thiệp trợ giúp? (Lọc `audience=buyer`) | Người mua truy cập **Lịch sử mua hàng (Purchase History)**, chọn đơn hàng và nhấn "Ask eBay to step in". | `buyer-ask-ebay-to-step-in` |
| 4 | Người bán có những phương án xử lý nào khi nhận được yêu cầu đổi trả? (Lọc `audience=seller`) | Chấp nhận đổi trả trả phí ship, chấp nhận đổi trả buyer trả ship, hoàn tiền một phần giữ hàng, hoặc đổi món khác. | `seller-handle-return-request` |
| 5 | Đơn hàng giá trị từ bao nhiêu USD trở lên bắt buộc phải có xác nhận chữ ký khi giao hàng? | Đơn hàng từ **750 USD** trở lên bắt buộc phải có xác nhận chữ ký (Signature Confirmation). | `seller-payment-dispute-protection` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời hạn người bán phản hồi đổi trả | `RecursiveChunker` | Có (top-1) | Đạt 2/2đ — trả lời đúng mốc 3 ngày làm việc. |
| 2 | Trường hợp được bảo đảm hoàn tiền eBay | `HeadingChunker` | Có (top-1) | Đạt 2/2đ — trả lời đầy đủ 2 trường hợp chính. |
| 3 | Người mua yêu cầu eBay can thiệp ở đâu | `HeadingChunker` + Filter (`audience=buyer`) | Có (top-1) | Đạt 2/2đ — tiền lọc `buyer` ngăn lầm lẫn chính sách phía seller. |
| 4 | Các phương án xử lý đổi trả của người bán | `SentenceChunker` + Filter (`audience=seller`) | Có (top-1) | Đạt 2/2đ — tiền lọc `seller` liệt kê đủ 4 phương án. |
| 5 | Hạn mức giá trị cần xác nhận chữ ký | `RecursiveChunker` | Có (top-1) | Đạt 2/2đ — trích xuất chính xác con số 750 USD. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> *Lọc bằng metadata cực kỳ quan trọng ở các câu 3 và 4. Do cả người mua và người bán đều có các quy trình mang tên tương tự ("Ask eBay to step in"), nếu không tiền lọc `metadata_filter={"audience": "buyer"}` hoặc `{"audience": "seller"}`, kết quả truy xuất vector dễ bị lẫn lộn giữa hai đối tượng, dẫn đến Agent đưa ra hướng dẫn sai quyền hạn cho người dùng.*

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. *Tầm quan trọng của Metadata Pre-filtering:* Tiền lọc phân loại đúng vai trò người dùng (buyer/seller) giúp tăng vọt độ chính xác trong hệ thống RAG quy định.
> 2. *Sự vượt trội của Chunking theo cấu trúc:* `HeadingChunker` và `RecursiveChunker` giữ trọn vẹn mạch logic của điều khoản so với việc cắt độ dài cố định.
> 3. *Khả năng truy vết nguồn (Source Traceability):* Đính kèm `doc_id` và tiêu đề vào ngữ cảnh giúp người dùng đối chiếu lại văn bản gốc một cách minh bạch.

**Bài học rút ra khi so sánh trong nhóm:**
> *Cùng một tập dữ liệu chính sách, các chiến lược chia nhỏ khác nhau quyết định trực tiếp đến độ liên quan của ngữ cảnh. `FixedSizeChunker` dễ làm rơi rớt thông tin chi tiết (con số 3 ngày, 750 USD), trong khi chia nhỏ theo cấu trúc câu/tiêu đề giữ trọn vẹn thông tin giúp Agent trả lời chính xác 100%.*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> *Nhóm sẽ bổ sung cơ chế tự động đính kèm tiêu đề cha (Parent Section Context) vào từng chunk con khi phải chia nhỏ một section quá dài, đảm bảo mọi chunk nhỏ đều giữ được thông tin "nó thuộc mục chính sách nào".*

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |


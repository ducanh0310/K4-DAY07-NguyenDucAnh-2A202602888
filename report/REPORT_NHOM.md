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

**Thành viên 1 — Nguyễn Đức Anh (MSSV: 2A202602888)**
- **Loại chiến lược:** `RecursiveChunker` (Chia nhỏ đệ quy)
- **Mô tả & lý do chọn cho chủ đề này:** *Áp dụng chia đệ quy theo danh sách separator ưu tiên (`["\n\n", "\n", ". ", " ", ""]`) và gom các mảnh nhỏ liền kề sát ngưỡng `chunk_size=500`. Lý do chọn: giữ nguyên vẹn nội dung ngữ cảnh của từng đoạn điều khoản chính sách E-commerce mà không sinh ra các chunk vụn.*
- **Code snippet:**
```python
class RecursiveChunker:
    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)
```

**Thành viên 2 — Đặng Thái Anh (MSSV: 2A202602740)**
- **Loại chiến lược:** `HeadingChunker` (Custom Structural Chunker theo Tiêu đề Markdown)
- **Mô tả & lý do chọn:** *Phân tách văn bản dựa trên ranh giới thẻ tiêu đề Markdown (`(?=\n#+\s)`), chia mỗi section chính sách thành 1 chunk riêng với `chunk_size=700` kết hợp metadata pre-filter. Lý do chọn: tối ưu khả năng bảo toàn trọn vẹn 1 quy trình/điều khoản quy định.*
- **Code snippet:**
```python
class HeadingChunker:
    def __init__(self, chunk_size: int = 700) -> None:
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        sections = re.split(r"(?=\n#+\s)", text)
        return [s.strip() for s in sections if s.strip()]
```

**Thành viên 3 — Nguyễn Khánh Duy (MSSV: 2A202602403)**
- **Loại chiến lược:** `SentenceChunker` (Chia nhỏ theo ranh giới câu)
- **Mô tả & lý do chọn:** *Phân tách theo ranh giới câu bằng biểu thức chính quy lookbehind `(?<=[.!?])\s+` giữ nguyên dấu câu, gom nhóm `max_sentences_per_chunk=3` câu/chunk. Lý do chọn: đảm bảo từng câu quy định điều khoản hoặc nghĩa vụ không bị ngắt rớt từ giữa chừng.*
- **Code snippet:**
```python
class SentenceChunker:
    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        return [" ".join(sentences[i:i+self.max_sentences_per_chunk]) for i in range(0, len(sentences), self.max_sentences_per_chunk)]
```

**Thành viên 4 — Đỗ Trung Tuyến (MSSV: 2A202602427)**
- **Loại chiến lược:** `FixedSizeChunker` (Chia nhỏ kích thước cố định)
- **Mô tả & lý do chọn:** *Cắt văn bản theo kích thước ký tự cố định `chunk_size=500` và `overlap=50`. Lý do chọn: đơn giản, tốc độ xử lý nhanh, kiểm soát kích thước vector nhúng đồng nhất trên toàn bộ hệ thống.*
- **Code snippet:**
```python
class FixedSizeChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]
        step = self.chunk_size - self.overlap
        chunks = []
        for start in range(0, len(text), step):
            chunks.append(text[start : start + self.chunk_size])
            if start + self.chunk_size >= len(text):
                break
        return chunks
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Nguyễn Đức Anh | `RecursiveChunker` | 10/10 | Giữ ngữ cảnh đoạn trọn vẹn, linh hoạt | Kích thước chunk không đồng đều |
| Đặng Thái Anh | `HeadingChunker` | 10/10 | Bảo toàn hoàn toàn 1 quy trình/điều khoản | Phụ thuộc định dạng Markdown chuẩn |
| Nguyễn Khánh Duy | `SentenceChunker` | 9/10 | Câu văn mạch lạc, không nuốt dấu câu | Các câu dài có thể vượt độ dài tối ưu |
| Đỗ Trung Tuyến | `FixedSizeChunker` | 8/10 | Đồng đều, đơn giản, dễ tính toán | Dễ cắt ngắt câu giữa chừng |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *Chiến lược `HeadingChunker` và `RecursiveChunker` đạt hiệu quả cao nhất cho chủ đề chính sách Thương mại điện tử. Lý do: văn bản quy định được cấu trúc chặt chẽ theo từng mục điều khoản; việc chia theo tiêu đề/đoạn giúp bảo toàn hoàn toàn đơn vị ngữ nghĩa của quy trình, tránh việc bị ngắt rớt các thông tin điều kiện quan trọng (như số ngày giới hạn hay giá trị đơn hàng).*

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


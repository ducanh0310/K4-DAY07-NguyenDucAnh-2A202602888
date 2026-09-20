from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

# Configure UTF-8 encoding for standard output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore


CHUNKER_STRATEGY = os.getenv("CHUNKER_STRATEGY", "heading")


class HeadingChunker:
    """Tách văn bản theo các mục Heading (## Heading).
    Nếu section dài quá chunk_size, hạ xuống RecursiveChunker và đính kèm lại tiêu đề vào từng mảnh con.
    """

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self.recursive_chunker = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        sections = re.split(r"(?=\n#+\s)", text)
        final_chunks: list[str] = []
        for sec in sections:
            sec_str = sec.strip()
            if not sec_str:
                continue
            if len(sec_str) <= self.chunk_size:
                final_chunks.append(sec_str)
            else:
                lines = sec_str.split("\n")
                heading_line = lines[0] if lines[0].startswith("#") else ""
                sub_chunks = self.recursive_chunker.chunk(sec_str)
                for sub in sub_chunks:
                    if heading_line and not sub.startswith("#"):
                        final_chunks.append(f"{heading_line}\n{sub}")
                    else:
                        final_chunks.append(sub)
        return final_chunks


def get_chunker(strategy: str, chunk_size: int = 500):
    """Khởi tạo Chunker theo chiến lược được chọn."""
    strat = strategy.lower().strip()
    if strat == "heading":
        return HeadingChunker(chunk_size=chunk_size)
    elif strat == "sentence":
        return SentenceChunker(max_sentences_per_chunk=3)
    elif strat == "fixed":
        return FixedSizeChunker(chunk_size=chunk_size, overlap=50)
    else:  # default to recursive
        return RecursiveChunker(chunk_size=chunk_size)


class CachedEmbedder:
    """Bọc embedder thực bằng cache MD5 để tiết kiệm chi phí/tốc độ khi chạy lại API."""

    def __init__(self, base_embedder, cache_file: str = ".embedding_cache.json"):
        self.base_embedder = base_embedder
        self.cache_file = cache_file
        self._backend_name = getattr(base_embedder, "_backend_name", base_embedder.__class__.__name__)
        self.cache: dict[str, list[float]] = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def __call__(self, text: str) -> list[float]:
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]
        vec = self.base_embedder(text)
        self.cache[text_hash] = vec
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f)
        except Exception:
            pass
        return vec


def parse_markdown_file(file_path: Path) -> tuple[dict, str]:
    """Tách frontmatter YAML (nếu có) và phần thân content."""
    content = file_path.read_text(encoding="utf-8")
    metadata: dict = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_block = parts[1].strip()
            body = parts[2].strip()
            for line in yaml_block.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    clean_val = val.strip().strip('"').strip("'")
                    if "#" in clean_val:
                        clean_val = clean_val.split("#")[0].strip()
                    metadata[key.strip()] = clean_val

    return metadata, body


def get_embedder():
    """Khởi tạo embedding backend dựa trên biến môi trường EMBEDDING_PROVIDER."""
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            base = LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
            return CachedEmbedder(base, ".cache_local_embed.json")
        except Exception:
            return _mock_embed
    elif provider == "openai":
        try:
            base = OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
            return CachedEmbedder(base, ".cache_openai_embed.json")
        except Exception:
            return _mock_embed
    elif provider == "gemini":
        try:
            base = GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
            return CachedEmbedder(base, ".cache_gemini_embed.json")
        except Exception:
            return _mock_embed
    return _mock_embed


BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Người bán có bao nhiêu ngày làm việc để phản hồi yêu cầu đổi trả của người mua?",
        "filter": None,
        "gold_doc": "seller-handle-return-request",
    },
    {
        "id": 2,
        "query": "Chính sách Bảo đảm hoàn tiền eBay (eBay Money Back Guarantee) bảo vệ người mua trong trường hợp nào?",
        "filter": None,
        "gold_doc": "ebay-money-back-guarantee",
    },
    {
        "id": 3,
        "query": "Thao tác ở đâu để yêu cầu eBay can thiệp hỗ trợ?",
        "filter": {"audience": "buyer"},
        "gold_doc": "buyer-ask-ebay-to-step-in",
    },
    {
        "id": 4,
        "query": "Người bán có những phương án xử lý nào khi nhận được yêu cầu đổi trả?",
        "filter": {"audience": "seller"},
        "gold_doc": "seller-handle-return-request",
    },
    {
        "id": 5,
        "query": "Đơn hàng giá trị từ bao nhiêu USD trở lên bắt buộc phải có xác nhận chữ ký khi giao hàng?",
        "filter": None,
        "gold_doc": "seller-payment-dispute-protection",
    },
]


def run_benchmark():
    print("=== STARTING BENCHMARK RETRIEVAL TEST ===")

    # 1. Đọc tất cả các file .md trong data/ecommerce/
    corpus_files = [Path(p) for p in sorted(glob.glob("data/ecommerce/*.md"))]
    print(f"Loaded {len(corpus_files)} Markdown files into corpus.")

    chunker = get_chunker(CHUNKER_STRATEGY, chunk_size=500)
    print(f"Selected Chunker strategy: {CHUNKER_STRATEGY} ({chunker.__class__.__name__})")

    all_chunks: list[Document] = []

    # 2. Chunk phần thân, mỗi chunk thành một Document
    #    doc_id trong metadata trỏ về tên file gốc (path.stem)
    #    Document.id trỏ về id từng chunk ("file#0", "file#1")
    #    Tất cả trường metadata frontmatter được trải vào mọi chunk
    for path in corpus_files:
        frontmatter, body = parse_markdown_file(path)
        chunks_text = chunker.chunk(body)
        for i, text in enumerate(chunks_text):
            meta = {
                **frontmatter,
                "doc_id": path.stem,
                "source": str(path),
                "chunk_index": i,
            }
            doc_item = Document(
                id=f"{path.stem}#{i}",
                content=text,
                metadata=meta,
            )
            all_chunks.append(doc_item)

    print(f"Total chunks created: {len(all_chunks)}")

    # 3. Nạp vào EmbeddingStore
    embedder = get_embedder()
    print(f"Embedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")

    store = EmbeddingStore(collection_name="benchmark_store", embedding_fn=embedder)
    store.add_documents(all_chunks)
    print(f"Stored {store.get_collection_size()} chunks in EmbeddingStore.\n")

    # 4. Chạy 5 query qua search_with_filter() và in top-3 kèm score & doc_id
    print("=== BENCHMARK EVALUATION RESULTS ===")
    success_count = 0
    for q_item in BENCHMARK_QUERIES:
        q_id = q_item["id"]
        query = q_item["query"]
        meta_filter = q_item["filter"]
        gold_doc = q_item["gold_doc"]

        print(f"Query {q_id}: '{query}'")
        if meta_filter:
            print(f"  filter: {meta_filter}")
        else:
            print("  filter: None")

        results = store.search_with_filter(query, top_k=3, metadata_filter=meta_filter)

        found_in_top3 = False
        for idx, res in enumerate(results, start=1):
            doc_id = res["metadata"].get("doc_id", "unknown")
            score = res["score"]
            content_preview = res["content"][:90].replace("\n", " ")
            is_gold = "(GOLD MATCH)" if doc_id == gold_doc else ""
            if doc_id == gold_doc:
                found_in_top3 = True
            print(f"  Top-{idx}: score={score:.4f} | doc_id={doc_id} {is_gold}")
            print(f"          content: {content_preview}...")

        if found_in_top3:
            success_count += 1
            print("  -> Result: SUCCESS (Gold in top-3)\n")
        else:
            print("  -> Result: FAIL (Gold not in top-3)\n")

    print(f"=== SUMMARY: {success_count}/{len(BENCHMARK_QUERIES)} Queries retrieved Gold Answer in Top-3 ===")


if __name__ == "__main__":
    run_benchmark()

from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "No relevant context found in knowledge base."

        context_blocks = []
        for i, res in enumerate(results, start=1):
            source = res.get("metadata", {}).get("source", res.get("id", f"doc_{i}"))
            context_blocks.append(f"[{i}] (Source: {source})\n{res['content']}")

        context_str = "\n\n".join(context_blocks)
        prompt = (
            f"Context information is below.\n"
            f"---------------------\n"
            f"{context_str}\n"
            f"---------------------\n"
            f"Given the context information and not prior knowledge, answer the question: {question}"
        )
        return self.llm_fn(prompt)


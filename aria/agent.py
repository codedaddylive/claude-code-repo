from __future__ import annotations

from collections.abc import Iterator

from .config import AriaSettings
from .embeddings import EmbeddingBackend, make_embedding_backend
from .llm import LLMBackend, make_llm_backend
from .models import Answer, ChatMessage, RepoStats, SearchResult
from .vectorstore import VectorStore

SYSTEM_PROMPT = """You are Aria, an open-source coding assistant. You answer \
questions about software repositories using ONLY the context provided below, \
which was retrieved from the indexed source code.

Rules:
- Ground every claim in the provided context. If the context does not contain \
the answer, say so plainly rather than guessing.
- Cite the files you rely on using their `repo/path:start-end` labels.
- Prefer concrete references (function names, file paths) over vague summaries.
- Be concise and technical."""


class AriaAgent:
    """Ties the vector store, embeddings, and LLM into a RAG assistant."""

    def __init__(
        self,
        settings: AriaSettings,
        store: VectorStore,
        embedder: EmbeddingBackend,
        llm: LLMBackend,
    ) -> None:
        self.settings = settings
        self.store = store
        self.embedder = embedder
        self.llm = llm

    # --- construction ------------------------------------------------------
    @classmethod
    def load(cls, settings: AriaSettings) -> "AriaAgent":
        """Build an agent with backends and the persisted index loaded from disk."""
        settings.ensure_dirs()
        embedder = make_embedding_backend(settings)
        store = VectorStore.load(settings.index_dir, dim=embedder.dim)
        llm = make_llm_backend(settings)
        return cls(settings, store, embedder, llm)

    def save(self) -> None:
        self.store.save(self.settings.index_dir)

    # --- retrieval ---------------------------------------------------------
    def retrieve(self, question: str, top_k: int | None = None) -> list[SearchResult]:
        query_vec = self.embedder.embed_one(question, input_type="query")
        return self.store.search(query_vec, top_k=top_k or self.settings.top_k)

    def _build_context(self, results: list[SearchResult]) -> str:
        budget = self.settings.max_context_chars
        blocks: list[str] = []
        used = 0
        for r in results:
            block = f"### {r.chunk.citation}\n```\n{r.chunk.text}\n```"
            if used + len(block) > budget:
                break
            blocks.append(block)
            used += len(block)
        return "\n\n".join(blocks)

    def _messages(self, question: str, results: list[SearchResult]) -> list[ChatMessage]:
        context = self._build_context(results) or "(no indexed context found)"
        return [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Context:\n{context}\n\nQuestion: {question}",
            ),
        ]

    # --- question answering ------------------------------------------------
    def ask(self, question: str) -> Answer:
        results = self.retrieve(question)
        messages = self._messages(question, results)
        reply = self.llm.chat(messages, temperature=self.settings.temperature)
        return Answer(question=question, answer=reply, sources=results)

    def ask_stream(self, question: str) -> tuple[Iterator[str], list[SearchResult]]:
        """Return a streaming token iterator plus the sources used."""
        results = self.retrieve(question)
        messages = self._messages(question, results)
        stream = self.llm.stream(messages, temperature=self.settings.temperature)
        return stream, results

    # --- introspection -----------------------------------------------------
    def stats(self) -> list[RepoStats]:
        return self.store.stats()

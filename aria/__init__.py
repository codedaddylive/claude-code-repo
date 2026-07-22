"""Aria — an open-source AI assistant that answers questions over GitHub repositories.

Aria is a small, self-contained retrieval-augmented-generation (RAG) system built
entirely from open-source components:

* Open-source LLMs served locally via `Ollama <https://ollama.com>`_
  (Llama, Mistral, Qwen, Gemma, ...), fully swappable.
* Local embeddings + a dependency-light NumPy vector store — no external
  vector database required.
* GitHub repositories as the knowledge source: clone, chunk, embed, and query.

The goal is a capable, private, open assistant you fully own — a practical
open-source alternative in the spirit of hosted assistants, not a from-scratch
frontier model.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]

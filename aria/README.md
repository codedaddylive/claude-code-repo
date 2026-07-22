# Aria 🪶

**An open-source AI assistant that answers questions over GitHub repositories.**

Aria is a small, self-contained retrieval-augmented-generation (RAG) system built
entirely from open-source parts. Point it at GitHub repos; it clones, chunks,
embeds, and indexes them, then answers questions about the code with citations —
running a local open-source LLM you fully own.

### What "comparable to a hosted assistant" means here — and what it doesn't

Aria does **not** train a frontier foundation model from scratch — that takes a
research team and millions of dollars in compute, and no amount of GitHub code
substitutes for it. What Aria *does* is give you a capable, **private, open**
assistant by assembling proven open-source components:

| Layer | Aria uses | Open-source options |
|---|---|---|
| LLM | [Ollama](https://ollama.com) (local server) | Llama 3.1, Qwen 2.5, Mistral, Gemma 2, Phi |
| Embeddings | Ollama embeddings | `nomic-embed-text`, `mxbai-embed-large` |
| Vector store | built-in NumPy store | swap for FAISS / Chroma behind one interface |
| Knowledge | your GitHub repos | any repo, org, or local path |

Nothing here calls a paid API. It is yours to run, inspect, and extend.

## Install

```bash
pip install -r aria/requirements.txt   # httpx, numpy, pydantic, typer, rich, fastapi

# For real answers, install Ollama and pull open models (optional):
#   https://ollama.com
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Aria also ships an **offline mode** (deterministic `hash` embeddings + an `echo`
LLM stub) so the full pipeline runs and tests pass with no model server at all.

## Quick start

```bash
# 1. Index one or more repositories (GitHub URL, owner/repo, or local path)
python -m aria.cli ingest fastapi/fastapi
python -m aria.cli ingest https://github.com/pallets/flask ./my-local-project

# 2. Ask a question — the answer streams, with cited sources
python -m aria.cli ask "How is dependency injection implemented?"

# 3. Or chat interactively
python -m aria.cli chat

# See what's indexed and the active config
python -m aria.cli status

# Remove a repo from the index
python -m aria.cli remove pallets/flask
```

### Run it fully offline (no Ollama needed)

```bash
export ARIA_LLM_BACKEND=echo
export ARIA_EMBED_BACKEND=hash
python -m aria.cli ingest .
python -m aria.cli ask "what does the extractor module do?"
```

## HTTP API

```bash
uvicorn aria.api:app --host 0.0.0.0 --port 8100 --workers 1
```

| Method | Path | Description |
|---|---|---|
| GET  | `/health` | Health check + indexed chunk count |
| GET  | `/repos` | List indexed repositories |
| POST | `/ingest` | `{"source": "owner/repo"}` — index a repo |
| POST | `/ask` | `{"question": "..."}` — answer with sources |
| DELETE | `/repos/{owner}/{name}` | Remove an indexed repo |

## Configuration

All settings are environment variables prefixed with `ARIA_` (or a `.env` file).
See [`config.example.yaml`](./config.example.yaml) for the full reference.

| Variable | Default | Description |
|---|---|---|
| `ARIA_LLM_BACKEND` | `ollama` | `ollama` or `echo` (offline) |
| `ARIA_MODEL` | `llama3.1:8b` | any chat model pulled in Ollama |
| `ARIA_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `ARIA_EMBED_BACKEND` | `ollama` | `ollama` or `hash` (offline) |
| `ARIA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `ARIA_TOP_K` | `6` | chunks retrieved per query |
| `ARIA_CHUNK_LINES` / `ARIA_CHUNK_OVERLAP` | `60` / `12` | chunking window |
| `ARIA_DATA_DIR` | `~/.aria` | where the index + clones live |

## Architecture

```
GitHub repo / local path
  → ingest.py      — clone (shallow), walk source files, chunk by lines
  → embeddings.py  — embed chunks (Ollama model, or offline hash)
  → vectorstore.py — persistent NumPy cosine index (vectors.npy + chunks.jsonl)
  → agent.py       — retrieve top-k, build a grounded prompt with citations
  → llm.py         — open-source model via Ollama (streaming) → cited answer
```

```
aria/
├── config.py       # env-driven settings (pydantic-settings)
├── models.py       # Chunk, SearchResult, Answer, ...
├── embeddings.py   # EmbeddingBackend: Ollama + offline hash
├── llm.py          # LLMBackend: Ollama (chat/stream) + offline echo
├── vectorstore.py  # dependency-light persistent vector store
├── ingest.py       # repo cloning, file walking, chunking, indexing
├── agent.py        # RAG orchestration
├── cli.py          # ingest / ask / chat / status / remove
├── api.py          # FastAPI server
└── tests/          # offline test suite (no model server required)
```

## Tests

```bash
python -m aria.tests.test_aria      # no pytest needed
pytest aria/tests/test_aria.py      # or via pytest
```

## Extending Aria

Every backend is an abstract base class with a swappable implementation:

- **Different LLM provider?** Implement `LLMBackend` (`aria/llm.py`).
- **Better embeddings?** Implement `EmbeddingBackend` (`aria/embeddings.py`).
- **Scale to millions of chunks?** Replace `VectorStore` (`aria/vectorstore.py`)
  with a FAISS/Chroma-backed class exposing the same `add` / `search` methods.

## License

Released under the same terms as the parent repository.

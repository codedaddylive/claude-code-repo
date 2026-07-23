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
| LLM | [Ollama](https://ollama.com) locally, **or** any OpenAI-compatible host | Llama 3.1/3.3, Qwen 2.5, Mistral, Gemma 2, Phi |
| Embeddings | Ollama, hosted API, or offline hash | `nomic-embed-text`, `bge-large`, `mxbai-embed-large` |
| Vector store | built-in NumPy store | swap for FAISS / Chroma behind one interface |
| Knowledge | your GitHub repos | any repo, org, or local path |

Run it three ways, all open-source models: **fully local** (Ollama, no API),
**fully offline** (built-in hash + echo, no server at all), or **in the cloud
with no GPU** (a hosted provider serves open models over an OpenAI-compatible
API — see [`DEPLOY.md`](./DEPLOY.md)).

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

## Build an AI team (LLM-as-a-judge)

Aria can assemble a role→model "team" from a catalog of **free, open-source**
models — the open analog of a proprietary roster. Its own LLM acts as the judge,
scoring each candidate per role; it falls back to a deterministic heuristic when
no model server is available.

```bash
python -m aria.cli team recommend                 # LLM judges (falls back to heuristic)
python -m aria.cli team recommend --judge heuristic
python -m aria.cli team recommend --config         # also print how to RUN each pick
python -m aria.cli team recommend -o team.json     # save the roster (incl. run plan)
python -m aria.cli team models                     # inspect the catalog
python -m aria.cli team models --role designer
python -m aria.cli team env reasoning -o r.env     # write a ready-to-run .env for a role
python -m aria.cli team env general_coding --hosted
```

`team env <role>` writes a ready-to-source Aria `.env` for that role's winning
model (local Ollama by default, `--hosted` for a provider):

```bash
python -m aria.cli team env reasoning -o reasoning.env
set -a; source reasoning.env; set +a          # now Aria uses that model
python -m aria.cli ask "..."
```

With `--config`, each pick comes with a runnable command — local and hosted —
so you can drop it straight into Aria:

```
Reasoning → DeepSeek-R1
  local : ollama pull deepseek-r1  &&  export ARIA_MODEL=deepseek-r1
  hosted: export ARIA_LLM_BACKEND=openai ARIA_MODEL=deepseek-ai/DeepSeek-R1  # + ARIA_API_KEY/ARIA_API_BASE_URL
Designer → FLUX.1 [schnell]
  image : ComfyUI / diffusers; weights on Hugging Face (black-forest-labs/FLUX.1-schnell)
```

(Local run tags and hosted ids are best-effort hints in `aria/data/models.json`;
confirm the exact id with your Ollama version / hosted provider.)

Example roster (heuristic judge; all free/open-weight — verify current ratings
on live leaderboards, and edit `aria/data/models.json` to re-rank or add models):

| Role | Pick | License |
|---|---|---|
| R&D | DeepSeek-R1 | MIT |
| Frontend | Qwen2.5-Coder-32B | Apache-2.0 |
| General coding | DeepSeek-V3 | DeepSeek (commercial OK) |
| Deep engineering | DeepSeek-V3 | DeepSeek (commercial OK) |
| Content writing | Qwen2.5-72B / Llama-3.3-70B | open (license limits apply) |
| Designer (image) | FLUX.1 [schnell] | Apache-2.0 |
| Reasoning | DeepSeek-R1 / QwQ-32B | MIT / Apache-2.0 |

Non-commercial-licensed open weights (e.g. FLUX.1 [dev]) are excluded by default;
add `--include-noncommercial` to consider them. "Highly rated" is qualitative —
the catalog encodes reputation as an editable starting point and the LLM judge
refines it; always confirm against LMArena / OpenLLM Leaderboard / Aider / SWE-bench.

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
| GET | `/team/models` | The open-source model catalog + roles |
| GET | `/team/recommend?method=auto` | Judge and return the recommended team |

## Configuration

All settings are environment variables prefixed with `ARIA_` (or a `.env` file).
See [`config.example.yaml`](./config.example.yaml) for the full reference.

| Variable | Default | Description |
|---|---|---|
| `ARIA_LLM_BACKEND` | `ollama` | `ollama`, `openai` (hosted), or `echo` (offline) |
| `ARIA_MODEL` | `llama3.1:8b` | Ollama tag, or the provider's model id for `openai` |
| `ARIA_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `ARIA_EMBED_BACKEND` | `ollama` | `ollama`, `openai`, or `hash` (offline) |
| `ARIA_EMBED_MODEL` | `nomic-embed-text` | embedding model id |
| `ARIA_API_BASE_URL` | `https://api.together.xyz/v1` | hosted provider URL (`openai` backend) |
| `ARIA_API_KEY` | – | hosted provider key (`openai` backend) |
| `ARIA_TOP_K` | `6` | chunks retrieved per query |
| `ARIA_CHUNK_LINES` / `ARIA_CHUNK_OVERLAP` | `60` / `12` | chunking window |
| `ARIA_DATA_DIR` | `~/.aria` | where the index + clones live |

## Run in the cloud (no GPU)

Use a hosted provider that serves open models over an OpenAI-compatible API:

```bash
export ARIA_LLM_BACKEND=openai ARIA_EMBED_BACKEND=openai
export ARIA_API_KEY=<your-provider-key>
export ARIA_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo
export ARIA_EMBED_MODEL=BAAI/bge-large-en-v1.5
python -m aria.cli ask "..."      # or deploy the API via aria/Dockerfile
```

A containerized deploy (Render/Railway/Fly, step by step) is documented in
[`DEPLOY.md`](./DEPLOY.md).

### Try it locally with Docker (one command)

**Hosted models (no GPU, needs a provider key):**

```bash
cp aria/.env.example aria/.env      # then put your ARIA_API_KEY in it
docker compose -f aria/docker-compose.yml up --build
# → http://localhost:8100/health
```

**Fully local (no key, runs open models via Ollama on your machine):**

```bash
docker compose -f aria/docker-compose.local.yml up --build -d
# one-time: pull the models into the Ollama container
docker compose -f aria/docker-compose.local.yml exec ollama ollama pull llama3.1:8b
docker compose -f aria/docker-compose.local.yml exec ollama ollama pull nomic-embed-text
# → http://localhost:8100/health
```

Then ingest and ask over HTTP:

```bash
curl -X POST localhost:8100/ingest -H 'content-type: application/json' -d '{"source":"pallets/flask"}'
curl -X POST localhost:8100/ask    -H 'content-type: application/json' -d '{"question":"How are routes registered?"}'
```

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
├── team.py         # LLM-as-a-judge: pick open-source models per role
├── data/models.json# editable catalog of free/open-source models
├── cli.py          # ingest / ask / chat / status / remove / team
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

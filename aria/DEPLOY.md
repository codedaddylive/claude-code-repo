# Deploying Aria to the cloud (easiest / cheapest path)

This guide gets Aria running in the cloud with **no GPU to manage**. You use a
hosted provider that serves open-source models (Llama, Qwen, ...) over an
OpenAI-compatible API, and deploy Aria itself as a small container.

You need two things: an **API key** from a model provider, and a **host** to run
the container. Both have free/cheap tiers.

---

## Step 1 — Get a model provider API key

Aria's `openai` backend works with any OpenAI-compatible provider. Recommended
for starting fresh: **[Together AI](https://together.ai)** — it serves open
models for both **chat** and **embeddings** from one key.

1. Sign up at together.ai and create an API key.
2. Note two model ids (any open models the provider lists work):
   - Chat: `meta-llama/Llama-3.3-70B-Instruct-Turbo`
   - Embeddings: `BAAI/bge-large-en-v1.5`

> Other OpenAI-compatible providers work too — set `ARIA_API_BASE_URL`
> accordingly (e.g. OpenRouter `https://openrouter.ai/api/v1`, Groq
> `https://api.groq.com/openai/v1`). OpenRouter/Groq are chat-only, so pair them
> with Together for embeddings via `ARIA_EMBED_API_BASE_URL` + `ARIA_EMBED_API_KEY`.

### Environment variables Aria needs

```bash
ARIA_LLM_BACKEND=openai
ARIA_EMBED_BACKEND=openai
ARIA_API_BASE_URL=https://api.together.xyz/v1
ARIA_API_KEY=<your-key>
ARIA_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo
ARIA_EMBED_MODEL=BAAI/bge-large-en-v1.5
ARIA_DATA_DIR=/data          # persist the index here (see Step 3)
```

---

## Step 2 — Run the container

Build (context is the repo root):

```bash
docker build -f aria/Dockerfile -t aria .
```

Run locally to test against the cloud provider:

```bash
docker run -p 8100:8100 \
  -e ARIA_LLM_BACKEND=openai -e ARIA_EMBED_BACKEND=openai \
  -e ARIA_API_KEY=$ARIA_API_KEY \
  -e ARIA_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo \
  -e ARIA_EMBED_MODEL=BAAI/bge-large-en-v1.5 \
  -v aria-data:/data \
  aria

# then, in another terminal:
curl localhost:8100/health
curl -X POST localhost:8100/ingest -H 'content-type: application/json' \
     -d '{"source":"pallets/flask"}'
curl -X POST localhost:8100/ask -H 'content-type: application/json' \
     -d '{"question":"How are routes registered?"}'
```

---

## Step 3 — Deploy to a host (Render, step by step)

[Render](https://render.com) deploys a Dockerfile as a web service with a
persistent disk — a good fit for starting fresh.

1. Push this repo to GitHub (already done for the Aria branch).
2. In Render: **New → Web Service** → connect the repo.
3. Settings:
   - **Runtime:** Docker
   - **Dockerfile path:** `aria/Dockerfile`
   - **Docker build context:** `.` (repo root)
4. **Environment variables:** add the ones from Step 1 (set `ARIA_API_KEY` as a
   *secret*). Render provides `PORT` automatically; the container honors it.
5. **Disk (important):** add a persistent disk mounted at **`/data`** so your
   index survives restarts and redeploys. Without it, you re-ingest on every
   restart (see note below).
6. Deploy. When live, hit `https://<your-service>.onrender.com/health`.

The same recipe applies to **Railway** or **Fly.io** — point them at
`aria/Dockerfile`, set the env vars, and attach a volume at `/data`.

---

## Why a persistent disk matters

Aria's vector index lives under `ARIA_DATA_DIR` (`/data` in the container). Cloud
containers have **ephemeral** filesystems — without a mounted volume, the index
is wiped on every restart and you'd have to re-`/ingest`. A small disk (1 GB is
plenty for many repos) fixes this.

## Scaling notes

- The API keeps the index **in memory per process**, so run **one worker**
  (the image already does). To scale horizontally, move the index behind a
  shared store — replace `VectorStore` (`aria/vectorstore.py`) with a
  FAISS/Chroma/managed-vector-DB implementation exposing the same
  `add` / `search` methods; the rest of Aria is unchanged.
- Keep one embedding model for the life of an index. Vectors from different
  embedding models aren't comparable, so switching `ARIA_EMBED_MODEL` means
  re-ingesting.

## Cost sketch

- **Model API:** pay-per-token; indexing embeds once, then each question is a
  few thousand tokens. Typically cents for light use.
- **Host:** Render/Railway/Fly all have low-cost tiers suitable for a personal
  Aria instance; the container is small and needs no GPU.

## Going fully self-hosted later

Because the backends are swappable, you can move off the hosted API without
changing Aria: run **Ollama** (or vLLM) on a GPU box and set
`ARIA_LLM_BACKEND=ollama` / `ARIA_EMBED_BACKEND=ollama`. Same app, your hardware.

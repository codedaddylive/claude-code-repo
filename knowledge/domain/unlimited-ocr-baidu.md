---
title: "Unlimited OCR (baidu/Unlimited-OCR) — Single-Pass Long-Document Parsing"
category: domain
tags: [ocr, document-parsing, vlm, sglang, pdf, baidu]
created: 2026-06-28
source: https://github.com/baidu/Unlimited-OCR
---

# Unlimited OCR (baidu/Unlimited-OCR)

**Repo**: https://github.com/baidu/Unlimited-OCR — MIT | arXiv 2606.23050 (June 2026)

## What it is / problem it solves

VLM-based OCR and document-parsing system from Baidu that performs "one-shot long-horizon parsing": processes multi-page PDFs in a **single model inference pass** rather than chunking pages and stitching results. Directly addresses quality-degradation and orchestration overhead of traditional OCR pipelines (PaddleOCR, DeepSeek-OCR) on long documents. Practical ceiling is the SGLang backend's 32,768-token context window.

## Key features

- **Single-pass multi-page parsing** — the entire document goes into one inference call; no chunking, no result merging
- **Two inference modes** — local HuggingFace Transformers and a persistent SGLang HTTP server (OpenAI-compatible `/v1/chat/completions`)
- **Two resolution/crop configurations**:
  - `gundam`: `base_size=1024, image_size=640, crop_mode=True` — high-res crops, best for dense text
  - `base`: `base_size=1024, image_size=1024, crop_mode=False` — full-page view, used for multi-page/PDF
- **PDF-native** — PyMuPDF (fitz) converts pages to images at 300 DPI before inference
- **Concurrent batch processing** — `ThreadPoolExecutor`-based harness in `infer.py`
- **Retry logic** — up to 5 attempts per image
- **n-gram logit processor** in SGLang to suppress output repetition

## Tech stack

| Component | Version |
|---|---|
| Python | 3.12 |
| CUDA | 12.9 |
| PyTorch | 2.10.0 |
| HuggingFace Transformers | 4.57.1 |
| SGLang | custom wheel in `wheel/` (FlashAttention 3 backend) |
| PyMuPDF | latest |

## Installation / quick-start

```bash
git clone https://github.com/baidu/Unlimited-OCR
cd Unlimited-OCR
# CRITICAL: install the in-repo wheel, NOT PyPI sglang
pip install wheel/sglang*.whl
pip install torch==2.10.0 torchvision==0.25.0 transformers==4.57.1
pip install pymupdf pillow einops addict psutil

# Launch SGLang server (GPU required)
python -m sglang.launch_server \
  --model-path <your-model-path> \
  --context-length 32768 \
  --mem-fraction-static 0.8 \
  --attention-backend fa3

# Wait for /health to return 200, then run batch inference
python infer.py --image_dir ./docs --output_dir ./results
```

## Notable patterns and API design

**Inference payload** — images embedded as base64 data URIs in standard OpenAI chat-completions body:
```json
{
  "model": "unlimited-ocr",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,<b64>"}},
      {"type": "text", "text": "document parsing"}
    ]
  }],
  "stream": true
}
```
Use `"Multi page parsing"` as the text prompt for multi-page PDFs.

**OpenAI-compatible API**: existing clients using the `openai` SDK can point `base_url` at the SGLang server with no code changes.

**Job discovery**: `collect_dataset_images(image_dir)` does recursive traversal to build the job list. Always `GET /health` before dispatching.

## Gotchas / caveats

- **SGLang wheel is critical** — do NOT install from PyPI (`pip install sglang`). The in-repo wheel includes n-gram logit processor and FA3 backend patches. Using the wrong wheel is a silent failure mode.
- **Version pinning is strict** — PyTorch 2.10.0 and Transformers 4.57.1 are not suggestions; mismatches break model loading or the custom wheel.
- **GPU required** — no CPU fallback path.
- **Context window ceiling** — single-pass parsing bounded by 32,768 tokens; extremely long PDFs (dense 50+ pages) may still need PDF-level splitting.
- **GPU memory** — `--mem-fraction-static 0.8` reserves 80% of VRAM for static KV cache. Do not run other workloads on the same GPU.
- **When to use**: long multi-page PDFs where chunked OCR loses cross-page context; self-contained locally-hosted OCR; drop-in OpenAI API compatible document pipeline.
- **When not to use**: no GPU; single-page documents where Tesseract/PaddleOCR suffices; environments where strict version pinning is impractical.

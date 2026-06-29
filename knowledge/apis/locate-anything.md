---
title: "NVIDIA LocateAnything-3B — Visual Grounding API"
category: apis
tags: [object-detection, visual-grounding, vision-language, bounding-box, video-pipeline, nvidia]
created: 2026-06-29
source: https://huggingface.co/nvidia/LocateAnything-3B
---

# NVIDIA LocateAnything-3B — Visual Grounding API

**Model:** `nvidia/LocateAnything-3B` — NVIDIA License (non-commercial research only)
**HF Space:** https://huggingface.co/spaces/nvidia/LocateAnything
**Paper:** https://arxiv.org/html/2605.27365v1

## What it does

Takes an image + natural language prompt, returns precise bounding boxes for any described object or region. Supports open-vocabulary detection — no fixed class list. Works on photos, screenshots, UI, documents, video frames.

```json
[{"bbox_2d": [45, 123, 910, 678], "label": "person holding phone"}]
```

Coordinates are normalized integers in `[0, 1000]` range, ordered `[y1, x1, y2, x2]`.

## Why it matters for ARIA's video pipeline

Claude vision describes *what* is in a frame. LocateAnything adds *where* — spatial coordinates for every detected object. Slot it as a pre-pass before `analyzer.py`:

```
extractor.py → frames
  ├── LocateAnything  → bounding boxes  ─┐
  └── Claude vision   → descriptions   ─┤→ AnalysisResult (enriched)
```

Useful queries: `"locate all people"`, `"find any text on screen"`, `"where is the product"`, `"locate hands"`.

## Core innovation: Parallel Box Decoding (PBD)

Predicts all bounding box coordinates in one parallel step instead of token-by-token. Result: **12.7 boxes/sec on H100** vs 1.1 BPS for Qwen3-VL. Three inference modes from the same model:

| Mode | How | When to use |
|---|---|---|
| **Fast** (MTP) | Full parallel decode | Robotics, real-time, on-device |
| **Slow** (NTP) | Autoregressive | Max accuracy, offline labeling |
| **Hybrid** (default) | Fast + fallback to Slow on bad output | Production pipelines |

## Architecture

- Vision encoder: Moon-ViT
- Language decoder: Qwen2.5
- Bridge: MLP projector

## Hardware

| Precision | VRAM |
|---|---|
| BF16 (default) | ~8.4 GB |
| INT4 quantized | ~2.1 GB |
| FP32 | ~16 GB |

MLX 8-bit community build available for Apple Silicon: `mlx-community/LocateAnything-3B-8bit`

## Integration — OpenAI-compatible API

Use the community FastAPI wrapper (https://github.com/adambarbato/locate-anything-api) for local deployment:

```bash
# Run the wrapper (requires GPU with ~8GB VRAM)
docker run --gpus all -p 8000:8000 locate-anything-api
```

```python
from openai import OpenAI
import base64

client = OpenAI(base_url="http://localhost:8000/v1", api_key="none")

with open("frame.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="nvidia/LocateAnything-3B",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": "locate all people and any visible text"}
        ]
    }]
)

import json
boxes = json.loads(response.choices[0].message.content)
# [{"bbox_2d": [y1, x1, y2, x2], "label": "..."}]
```

## HuggingFace Space (no GPU needed)

Use the Gradio Space for testing or low-volume use. No setup required, but rate-limited:

```python
from gradio_client import Client

client = Client("nvidia/LocateAnything")
result = client.predict(
    image="frame.jpg",
    prompt="locate all people",
    api_name="/predict"
)
```

## Benchmarks

- **HumanRef**: 78.7 mean F1 (referring expression comprehension)
- **ScreenSpot-Pro**: 60.3 mean F1 — SOTA, beats Qwen3-VL-30B and GUI-Owl-32B
- **RefCOCOg**: Competitive with top-tier VLMs

## License constraint

**NVIDIA non-commercial license** — research and academic use only. No commercial deployment permitted (except NVIDIA affiliates). For commercial visual grounding, use:
- Grounding DINO (Apache 2.0) — `IDEA-Research/grounding-dino`
- OWL-ViT (Apache 2.0) — `google/owlvit-base-patch32`

## When to use

- Augmenting video frame analysis with spatial coordinates
- UI/screenshot element location (GUI agents, testing)
- Document and text localization
- Any pipeline where Claude vision describes but can't pinpoint location

## When to avoid

- Commercial products (license violation)
- No GPU available and high query volume (Space rate limits)
- Sub-2GB VRAM — use INT4 build or switch to Grounding DINO

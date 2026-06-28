---
title: Anthropic Claude API usage
category: apis
tags: [anthropic, claude, vision, ai, api]
created: 2026-06-28
---

# Anthropic Claude API

## Current model IDs (as of 2026-06-28)
- `claude-sonnet-4-6` — balanced speed/quality (default for most tasks)
- `claude-opus-4-8` — highest capability
- `claude-haiku-4-5-20251001` — fastest / cheapest
- `claude-fable-5` — latest flagship

## Vision (image input)
```python
import anthropic
import base64

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

with open("frame.jpg", "rb") as f:
    img_b64 = base64.standard_b64encode(f.read()).decode()

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
            {"type": "text", "text": "Describe what you see in this frame."},
        ],
    }],
)
print(message.content[0].text)
```

## Batching frames (up to 20 images per call)
```python
content = []
for frame_path in frame_paths[:20]:
    with open(frame_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
content.append({"type": "text", "text": "Describe each image briefly."})
```

## Streaming
```python
with client.messages.stream(model="claude-sonnet-4-6", max_tokens=512, messages=[...]) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

## Notes
- Max images per request: 20 (was 10 in older docs — verify with current API limits)
- Always set `ANTHROPIC_API_KEY` in env; never hardcode
- Rate limits: use exponential backoff on 429 errors
- `anthropic.BadRequestError` is raised for blocked/unsafe content

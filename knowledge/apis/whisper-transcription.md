---
title: OpenAI Whisper (local) usage
category: apis
tags: [whisper, transcription, audio, python]
created: 2026-06-28
---

# OpenAI Whisper (local transcription)

## Basic usage
```python
import whisper

# Models: tiny, base, small, medium, large (larger = more accurate, slower)
model = whisper.load_model("base")  # ~150MB download on first run
result = model.transcribe("audio.wav")
print(result["text"])
```

## Cache the model (avoid reloading)
```python
_whisper_model = None

def get_model(name: str = "base"):
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(name)
    return _whisper_model
```

## Language + timestamps
```python
result = model.transcribe("audio.wav", language="en", word_timestamps=True)
for segment in result["segments"]:
    print(f"{segment['start']:.1f}s: {segment['text']}")
```

## Notes
- Whisper expects WAV or MP3; extract from video with ffmpeg first
- `base` model is the sweet spot: fast, decent accuracy, ~150MB
- `large` model ~3GB, significantly more accurate for noisy audio
- GPU (CUDA) used automatically if available; falls back to CPU
- `fp16=False` required when running on CPU-only machines

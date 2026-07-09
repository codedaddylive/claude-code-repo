---
title: Video analysis pipeline architecture
category: architecture
tags: [architecture, pipeline, video, design]
created: 2026-06-28
---

# Video analysis pipeline architecture

## Flow
```
Input (URL / local path)
  → downloader.py   — download to temp dir via yt-dlp or direct copy
  → extractor.py    — OpenCV frame extraction + ffmpeg audio WAV
  → transcriber.py  — Whisper transcription (cached model instance)
  → analyzer.py     — Claude vision (batched ≤20 frames/call)
  → AnalysisResult  — Pydantic model → JSON output
```

## Key decisions
- **Temp dir per job**: each run gets its own `tempfile.mkdtemp()`, cleaned up in a `finally` block
- **Frame batching**: Claude vision called with up to 20 frames at once (not one-by-one) to minimize API round trips
- **Model caching**: Whisper model loaded once and reused across calls via module-level singleton
- **Sync CLI, async API**: `cli.py` runs synchronously; `api.py` uses FastAPI async + BackgroundTasks for non-blocking uploads

## Extending the pipeline
- Add a new stage by creating a module in `video_tool/` with a single public function
- Wire it into `cli.py` and `api.py` — both call the same underlying functions
- Add its output field to `AnalysisResult` in `models.py`

## Scaling notes
- API server runs `--workers 1` (in-memory job store) — switch to Redis for multi-worker
- yt-dlp downloads blocked from datacenter IPs; local files always work

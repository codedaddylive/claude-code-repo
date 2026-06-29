# Project Overview

> Deep context for agents. Update this when architectural decisions change.

---

## Architecture

```
Input (URL / local file)
  → downloader.py    yt-dlp + direct URL + local file handling
  → extractor.py     frame extraction (OpenCV) + audio WAV (ffmpeg)
  → transcriber.py   Whisper transcription (model cached on first run)
  → analyzer.py      Claude vision — keyframes, objects, summary (batched ≤10 frames/call)
  → AnalysisResult   structured JSON output (Pydantic v2)
```

**ARIA knowledge layer (runs alongside all sessions):**
```
raw/          data lake — unprocessed uploads
knowledge/    wiki — settled decisions encoded as markdown
brain.py      CLI — add/list/search/show/review/inflow/queue
```

---

## Architectural Decisions (settled — check before changing)

| Decision | Rationale |
|---|---|
| Whisper runs locally | No extra API cost; model cached after first download (~150MB base) |
| Claude vision batched ≤10 frames | API limit; analyzer.py handles chunking automatically |
| Pydantic v2 for all models | Type safety at I/O boundaries; `video_tool/models.py` is the single source of truth |
| FastAPI for HTTP server | Async-native, automatic OpenAPI docs, aligns with stack |
| Typer for CLI | Matches FastAPI ergonomics; same patterns documented in `knowledge/patterns/cli-typer.md` |
| yt-dlp over youtube-dl | Actively maintained fork; same API surface |
| imageio-ffmpeg for H.264 | Bundled ffmpeg has full codec support including libx264 for iOS-compatible MP4 |
| Squad for multi-agent | SQLite transport — no infra, works offline, ARIA-aware roles |

---

## Target Audience / Users

- **Primary**: Developer (you) — building and iterating on the platform
- **Secondary**: Claude Code + other AI agents — consuming ARIA's knowledge to implement features without re-researching
- **Future**: Other developers who clone the repo and want a working video analysis pipeline out of the box

---

## Core Dependencies

```
# Runtime
anthropic          Claude vision API
openai-whisper     local speech transcription
yt-dlp             video download
opencv-python      frame extraction
imageio-ffmpeg     H.264/MP4 encoding (full ffmpeg bundle)
fastapi            HTTP API server
uvicorn            ASGI server
typer              CLI framework
pydantic>=2.0      data validation
python-dotenv      env var loading

# Dev
httpx              async HTTP client (test requests)
pytest             test runner
```

---

## Key File Locations

| File | Purpose |
|---|---|
| `cli.py` | Typer CLI entry point |
| `api.py` | FastAPI server |
| `video_tool/models.py` | All Pydantic models |
| `video_tool/analyzer.py` | Claude vision calls |
| `brain.py` | ARIA knowledge CLI |
| `knowledge/` | ARIA wiki entries |
| `.squad/roles/` | Multi-agent role definitions |

---

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | `sk-ant-...` |

---

## Known Constraints

- YouTube downloads blocked from datacenter/Colab IPs — use local files there
- Whisper base model: ~150MB download on first run
- Bundled system ffmpeg is minimal (VP8 only) — use `imageio-ffmpeg` binary for H.264/MP4
- iOS requires MP4/H.264 — WebM/VP8 plays black screen on iPhone

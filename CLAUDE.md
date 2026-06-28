# Video Extraction & Analysis Tool

## Project setup (run these first)

```bash
# 1. Clone the repo (if not already cloned)
git clone https://github.com/codedaddylive/claude-code-repo
cd claude-code-repo

# 2. Install system dependency
apt install ffmpeg        # Linux
brew install ffmpeg       # macOS

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set API key
export ANTHROPIC_API_KEY=sk-ant-...
```

## What this project does

Analyzes videos from YouTube, yt-dlp-supported platforms, direct URLs, or local files using:
- **Claude AI vision** — keyframe descriptions, object detection, visual summary
- **Whisper** — local audio transcription (no extra API cost)
- **yt-dlp + OpenCV + ffmpeg** — download, frame extraction, audio extraction

## Key commands

```bash
# Analyze a video (full pipeline)
python cli.py analyze "path/to/video.mp4" --max-frames 5 --output result.json

# YouTube / yt-dlp URL (works on home IPs, not datacenter/Colab)
python cli.py analyze "https://www.youtube.com/watch?v=..." --max-frames 5

# Extract frames only
python cli.py extract-frames "video.mp4" --output-dir ./frames --interval 5

# Transcribe only
python cli.py transcribe "video.mp4" --model base

# Start the API server
uvicorn api:app --host 0.0.0.0 --port 8000

# Run integration tests
python tests/integration_test.py
```

## Project structure

```
claude-code-repo/
├── cli.py                  # Typer CLI — analyze / extract-frames / transcribe
├── api.py                  # FastAPI server — POST /analyze, POST /analyze/upload
├── requirements.txt        # All Python dependencies
├── colab_demo.ipynb        # Google Colab notebook for browser-based use
├── video_tool/
│   ├── models.py           # Pydantic v2 models for all inputs/outputs
│   ├── downloader.py       # yt-dlp + direct URL + local file handling
│   ├── extractor.py        # Frame extraction (OpenCV) + audio (ffmpeg)
│   ├── transcriber.py      # Whisper transcription with model caching
│   └── analyzer.py         # Claude vision — keyframes, objects, summary
└── tests/
    └── integration_test.py # Full pipeline test (run to verify everything works)
```

## Architecture

```
Input URL/path
  → downloader.py   — download or copy video to temp dir
  → extractor.py    — extract frames (interval or scene-change) + audio WAV
  → transcriber.py  — Whisper transcription (cached model)
  → analyzer.py     — Claude vision analysis (batched, <= 10 frames/call)
  → AnalysisResult  — structured JSON output
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (sk-ant-...) |

## API server endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/analyze` | Analyze a video URL |
| POST | `/analyze/upload` | Analyze an uploaded file |
| GET | `/jobs/{job_id}` | Retrieve past result |

## Notes

- YouTube downloads blocked from datacenter/Colab IPs — use local files or home network
- Whisper base model downloads ~150MB on first run
- Claude vision batches up to 10 frames per API call
- All temp files cleaned up automatically after each run
- API server uses --workers 1 (in-memory job store)

---

## Knowledge base (brain)

Accumulated patterns, API notes, architecture decisions, and domain rules live in `knowledge/`.
**Always consult these files before implementing something — they encode settled decisions.**

Manage entries with `brain.py`:
```bash
python brain.py list                        # all entries
python brain.py list --category patterns    # filter by category
python brain.py search "fastapi"            # keyword search
python brain.py show patterns/fastapi-endpoint.md  # read an entry
python brain.py add --title "..." --category apis  # add new entry
python brain.py rebuild-index               # regenerate index below
```

### Knowledge base index

#### Patterns
- **FastAPI endpoint patterns** — `knowledge/patterns/fastapi-endpoint.md`  tags: fastapi, python, api, routing
- **Pydantic v2 model patterns** — `knowledge/patterns/pydantic-models.md`  tags: pydantic, python, validation, models
- **Typer CLI patterns** — `knowledge/patterns/cli-typer.md`  tags: typer, cli, python

#### Apis
- **Anthropic Claude API usage** — `knowledge/apis/anthropic-claude.md`  tags: anthropic, claude, vision, ai, api
- **OpenAI Whisper (local) usage** — `knowledge/apis/whisper-transcription.md`  tags: whisper, transcription, audio, python

#### Architecture
- **Preferred project layout** — `knowledge/architecture/project-layout.md`  tags: structure, layout, python, project
- **Video analysis pipeline architecture** — `knowledge/architecture/video-pipeline.md`  tags: architecture, pipeline, video, design

#### Domain
- **Video analysis domain concepts** — `knowledge/domain/video-analysis-concepts.md`  tags: video, analysis, domain, concepts

# Video Extraction & Analysis Tool

Analyze videos from YouTube, Vimeo, TikTok, direct URLs, or local files using Claude AI vision and Whisper transcription.

## Features

- **Key frame extraction** — sample frames by time interval or scene change detection
- **Audio transcription** — local Whisper model (no extra API cost)
- **Object & scene detection** — per-frame object lists and scene descriptions via Claude vision
- **Visual summary** — narrative paragraph summary combining frames and transcript
- **CLI** — `python cli.py analyze <url>`
- **FastAPI server** — `POST /analyze` JSON endpoint + file upload support

## Prerequisites

```bash
# System dependency
apt install ffmpeg

# Python dependencies
pip install -r requirements.txt
```

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

> **Note:** The first transcription request downloads the Whisper `base` model (~150 MB).

## CLI Usage

### Full analysis
```bash
python cli.py analyze "https://www.youtube.com/watch?v=<id>" \
  --interval 10 \
  --max-frames 10 \
  --output result.json
```

### Extract frames only
```bash
python cli.py extract-frames "https://youtu.be/<id>" \
  --output-dir ./frames \
  --interval 5
```

### Transcribe only
```bash
python cli.py transcribe "https://youtu.be/<id>" \
  --model base \
  --output transcript.json
```

### Options
| Flag | Default | Description |
|---|---|---|
| `--analysis` / `-a` | `full` | `keyframes`, `transcribe`, `objects`, `summary`, `full` |
| `--interval` / `-i` | `5.0` | Seconds between sampled frames |
| `--strategy` / `-s` | `interval` | `interval` or `scene` (scene-change detection) |
| `--max-frames` / `-m` | `20` | Maximum frames to extract |
| `--whisper-model` / `-w` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `--output` / `-o` | stdout | Save JSON result to file |

## API Server

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/analyze` | Analyze a video URL |
| `POST` | `/analyze/upload` | Analyze an uploaded file |
| `GET` | `/jobs/{job_id}` | Retrieve a past result |
| `GET` | `/jobs` | List all job statuses |

### Example request

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=<id>",
    "analysis_types": ["summary", "transcribe"],
    "frame_interval_sec": 10,
    "max_frames": 10
  }'
```

### File upload

```bash
curl -X POST http://localhost:8000/analyze/upload \
  -F "file=@/path/to/video.mp4" \
  -F "analysis_types=full" \
  -F "max_frames=10"
```

## Output Format

```json
{
  "source": "https://...",
  "duration_sec": 120.5,
  "frame_count": 12,
  "keyframe_descriptions": ["A person speaking at a podium...", "..."],
  "transcription": {
    "language": "en",
    "full_text": "Welcome everyone...",
    "segments": [{"start": 0.0, "end": 3.2, "text": "Welcome everyone"}]
  },
  "object_detections": [
    {
      "frame_index": 0,
      "timestamp_sec": 0.0,
      "detected_objects": ["person", "microphone", "podium"],
      "scene_description": "Indoor conference stage"
    }
  ],
  "visual_summary": "This video features..."
}
```

## Supported Sources

- YouTube & YouTube Shorts
- Vimeo, TikTok, Dailymotion, Twitch, Twitter/X, Instagram
- Any other [yt-dlp-supported site](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- Direct video URLs (`.mp4`, `.webm`, `.mov`, etc.)
- Local file paths

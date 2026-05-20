# claude-video

A Claude Code skill that lets Claude watch any video and answer questions about it.

Paste a URL or local file path, ask a question — Claude downloads the video,
extracts frames, transcribes audio, and answers grounded in what it actually
saw and heard.

## Install

```bash
# Clone into Claude Code skills directory
git clone https://github.com/bradautomates/claude-video.git ~/.claude/skills/watch

# Run preflight check
python ~/.claude/skills/watch/scripts/setup.py --check
```

## Dependencies

| Tool | Required | Install |
|---|---|---|
| ffmpeg | Yes | `brew install ffmpeg` |
| yt-dlp | Yes | `brew install yt-dlp` |
| GROQ_API_KEY | No* | https://console.groq.com/keys |
| OPENAI_API_KEY | No* | https://platform.openai.com/api-keys |

\* Only needed for videos without native captions (Whisper fallback).

Set API keys in `~/.config/watch/.env`:

```ini
GROQ_API_KEY=gsk_...
# OPENAI_API_KEY=sk-...   # fallback if no Groq key
```

## Usage

### Via Claude Code skill

```bash
/watch https://youtu.be/dQw4w9WgXcQ what happens at 30 seconds?
/watch ~/Movies/bug-repro.mp4 when does the UI break?
/watch https://youtu.be/abc --start 2:15 --end 2:45
```

### Direct CLI

```bash
python scripts/watch.py https://youtu.be/dQw4w9WgXcQ "summarize this"
python scripts/watch.py video.mp4 --start 1:30 --end 2:00 "what happens here?"
python scripts/watch.py video.mp4 --no-whisper "describe the visuals"
```

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--start TIME` | — | Focus start (`1:30`, `90`, `1:12:00`) |
| `--end TIME` | — | Focus end |
| `--max-frames N` | auto | Override frame budget cap |
| `--resolution W` | 512 | Frame width in px (use 1024 for slides/text) |
| `--fps F` | auto | Override fps (capped at 2 fps) |
| `--whisper groq\|openai` | auto | Force Whisper backend |
| `--no-whisper` | — | Disable transcription; frames only |
| `--out-dir DIR` | tmp | Keep working files in this directory |
| `--no-cleanup` | — | Don't suggest removing working dir |

## How it works

1. **Download** — yt-dlp fetches the video and tries to grab native VTT captions
2. **Frames** — ffmpeg extracts JPEGs at auto-scaled fps (max 2 fps, 100 frames)
3. **Transcribe** — native captions used if available; otherwise Whisper API
4. **Answer** — Claude reads the frames as images and answers using frames + transcript

### Frame budget

| Video duration | Target frames |
|---|---|
| ≤ 30 s | ~30 |
| 30–60 s | ~40 |
| 1–3 min | ~60 |
| 3–10 min | ~80 |
| > 10 min | 100 (use `--start`/`--end` for detail) |

### Transcription strategy

1. Native VTT captions via yt-dlp (free, instant)
2. Groq `whisper-large-v3` (fast, generous free tier)
3. OpenAI `whisper-1` (fallback)
4. `--no-whisper` disables fallback entirely

## License

MIT

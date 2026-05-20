# claude-video — /watch skill

## What this is

A Claude Code skill that gives Claude the ability to watch any video.
You paste a URL or local file path, ask a question, and Claude downloads
the video, extracts frames, transcribes audio, and answers grounded in
what it actually saw and heard.

## Project structure

```
claude-video/
├── CLAUDE.md               ← you are here
├── SKILL.md                ← skill contract loaded by Claude Code
├── README.md
└── scripts/
    ├── watch.py            ← entry point (orchestrator)
    ├── download.py         ← yt-dlp wrapper + local file probe
    ├── frames.py           ← ffmpeg frame extraction + auto-fps logic
    ├── transcribe.py       ← VTT parsing + dedup + Whisper orchestration
    ├── whisper.py          ← Groq / OpenAI Whisper clients (pure stdlib)
    └── setup.py            ← preflight checker + dependency installer
```

## How to install as a Claude Code skill

```bash
# Option A — from the marketplace (recommended)
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video

# Option B — use this repo directly
git clone https://github.com/bradautomates/claude-video.git ~/.claude/skills/watch
```

## Dependencies

|Tool          |Required|Auto-install (macOS)                |
|--------------|--------|------------------------------------|
|ffmpeg        |Yes     |`brew install ffmpeg`               |
|yt-dlp        |Yes     |`brew install yt-dlp`               |
|GROQ_API_KEY  |No*     |https://console.groq.com/keys       |
|OPENAI_API_KEY|No*     |https://platform.openai.com/api-keys|

*Only needed for videos without native captions.

Set keys in `~/.config/watch/.env`:

```
GROQ_API_KEY=your-key-here
```

## Running the preflight check

```bash
python scripts/setup.py --check
```

## Usage examples

```bash
# Via Claude Code skill
/watch https://youtu.be/dQw4w9WgXcQ what happens at 30 seconds?
/watch ~/Movies/bug-repro.mp4 when does the UI break?
/watch https://youtu.be/abc --start 2:15 --end 2:45

# Direct CLI
python scripts/watch.py https://youtu.be/dQw4w9WgXcQ "summarize this"
python scripts/watch.py video.mp4 --start 1:30 --end 2:00 "what happens here?"
```

## CLI flags

|Flag                   |Default|Description                                 |
|-----------------------|-------|--------------------------------------------|
|`--start TIME`         |—      |Focus start (`1:30`, `90`, `1:12:00`)       |
|`--end TIME`           |—      |Focus end                                   |
|`--max-frames N`       |auto   |Override frame budget cap                   |
|`--resolution W`       |512    |Frame width in px (use 1024 for slides/text)|
|`--fps F`              |auto   |Override fps (capped at 2 fps)              |
|`--whisper groq|openai`|auto   |Force Whisper backend                       |
|`--no-whisper`         |—      |Disable transcription; frames only          |
|`--out-dir DIR`        |tmp    |Keep working files here                     |
|`--no-cleanup`         |—      |Don't suggest removing working dir          |

## Frame budget logic (frames.py)

Auto-scales based on video duration. Hard caps: 2 fps, 100 frames.

|Duration|Target frames                 |
|--------|------------------------------|
|≤30 s   |~30                           |
|30–60 s |~40                           |
|1–3 min |~60                           |
|3–10 min|~80                           |
|>10 min |100 (sparse — use –start/–end)|

## Transcription strategy (transcribe.py)

1. Try native VTT captions via yt-dlp (free, instant)
1. Fall back to Whisper API if no captions exist
- Groq `whisper-large-v3` preferred
- OpenAI `whisper-1` as alternative
1. `--no-whisper` disables fallback entirely

## Pipeline (watch.py orchestrates)

1. `setup.py --check` — verify deps
1. `download.py` — fetch video + captions
1. `frames.py` — extract JPEGs at auto-scaled fps
1. `transcribe.py` — get timestamped transcript
1. Print structured output with frame paths + transcript
1. Claude Reads each frame as an image and answers the question

## Key implementation details

- `whisper.py` uses only Python stdlib (no requests/httpx)
- Frames are tagged with `t=MM:SS` markers for timestamp correlation
- VTT deduplication strips repeated lines common in auto-captions
- Local files are probed with ffprobe (no download needed)
- Audio extracted as mono 16 kHz WAV for Whisper (25 MB limit)

## License

MIT — based on https://github.com/bradautomates/claude-video

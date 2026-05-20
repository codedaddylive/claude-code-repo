# watch skill

**Trigger:** `/watch`

**Usage:** `/watch <url_or_path> [question] [flags]`

## What Claude does

1. Run `python $SKILL_DIR/scripts/watch.py <url_or_path> <question> [flags]`
2. The script prints structured output:
   - `FRAME:<path>` lines — one per extracted JPEG
   - `TRANSCRIPT:` block — timestamped captions or Whisper output
   - `QUESTION:<text>` — the user's question
3. Read each frame image using the Read tool (Claude supports image reading)
4. Answer the user's question grounded in the frames and transcript

## Argument parsing

The skill receives everything after `/watch` as a single string. Split on the
first argument (URL or path), collect remaining words as the question unless
they begin with `--`.

Examples:
- `/watch https://youtu.be/abc what happens at 30 seconds?`
  → url=`https://youtu.be/abc`, question=`what happens at 30 seconds?`
- `/watch ~/video.mp4 --start 1:00 --end 1:30 describe this scene`
  → url=`~/video.mp4`, flags=`--start 1:00 --end 1:30`, question=`describe this scene`
- `/watch https://youtu.be/abc --no-whisper`
  → url=`https://youtu.be/abc`, question=*(empty, just summarize)*

## Invocation

```bash
python $SKILL_DIR/scripts/watch.py "<url_or_path>" "<question>" [flags]
```

Pass flags verbatim. If no question is given, use `"Describe what happens in this video."`.

## Supported flags

| Flag | Default | Description |
|---|---|---|
| `--start TIME` | — | Focus start (`1:30`, `90`, `1:12:00`) |
| `--end TIME` | — | Focus end |
| `--max-frames N` | auto | Override frame budget cap |
| `--resolution W` | 512 | Frame width in px |
| `--fps F` | auto | Override fps (capped at 2) |
| `--whisper groq\|openai` | auto | Force Whisper backend |
| `--no-whisper` | — | Skip transcription |
| `--out-dir DIR` | tmp | Keep working files here |
| `--no-cleanup` | — | Don't suggest removing working dir |

## Output format

```
FRAME:/tmp/watch_xyz/frame_000001_t00-00.jpg
FRAME:/tmp/watch_xyz/frame_000002_t00-02.jpg
...
TRANSCRIPT:
[00:00] Welcome to this video...
[00:05] Today we'll cover...

QUESTION: what happens at 30 seconds?
```

Parse `FRAME:` lines and read each path as an image. Use `TRANSCRIPT:` content
for audio context. Answer `QUESTION:` using both sources.

## Setup check

Before first use, run:
```bash
python $SKILL_DIR/scripts/setup.py --check
```

This verifies ffmpeg, yt-dlp, and API key availability.

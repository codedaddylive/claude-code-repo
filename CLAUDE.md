# claude-code-repo

## What this is

This repository contains the `claude-video` skill — a Claude Code skill (`/watch`) that lets Claude watch any video, extract frames, transcribe audio, and answer questions grounded in what it actually saw and heard.

## Project structure

```
claude-code-repo/
├── CLAUDE.md                  ← you are here
├── setup.sh                   ← one-shot install script
├── anthropic_claude_interaction.py   ← Claude API example
└── claude-video/              ← /watch skill
    ├── CLAUDE.md              ← skill spec
    ├── SKILL.md               ← Claude Code skill contract
    ├── README.md
    └── scripts/
        ├── watch.py           ← orchestrator (entry point)
        ├── download.py        ← yt-dlp wrapper + local file probe
        ├── frames.py          ← ffmpeg frame extraction + auto-fps
        ├── transcribe.py      ← VTT parse + dedup + Whisper fallback
        ├── whisper.py         ← Groq / OpenAI Whisper (pure stdlib)
        └── setup.py           ← preflight checker + dep installer
```

## Quick start

```bash
# Install everything in one command
bash setup.sh
```

Then open Claude Code in any directory and use:

```
/watch https://youtu.be/VIDEO_ID what happens in this video?
/watch ~/Movies/recording.mp4 when does the error appear?
```

## Installing the skill manually

```bash
cp -r claude-video ~/.claude/skills/watch
python ~/.claude/skills/watch/scripts/setup.py --check
```

## Dependencies

| Tool | Required | Install |
|---|---|---|
| ffmpeg | Yes | `brew install ffmpeg` |
| yt-dlp | Yes | `brew install yt-dlp` |
| GROQ_API_KEY | No* | https://console.groq.com/keys |

*Only needed for videos without native captions.

Set API keys in `~/.config/watch/.env`:
```
GROQ_API_KEY=your-key-here
```

## Running the preflight check

```bash
python ~/.claude/skills/watch/scripts/setup.py --check
```

## Common commands

```bash
# Check skill is installed
ls ~/.claude/skills/watch/

# Run preflight
python ~/.claude/skills/watch/scripts/setup.py --check

# Test with a local file
python ~/.claude/skills/watch/scripts/watch.py video.mp4 "describe this"

# Test with a URL
python ~/.claude/skills/watch/scripts/watch.py https://youtu.be/ID "summarize this"
```

---
title: "Voicebox: Local-First AI Voice Studio"
category: architecture
tags: [voice-cloning, tts, local-first, tauri, mcp, open-source]
created: 2026-06-28
source: https://github.com/jamiepine/voicebox
---

# Voicebox: Local-First AI Voice Studio

**Repo:** https://github.com/jamiepine/voicebox — MIT | v0.5.0 (June 2026) | 34.8k stars

## What it is

Desktop application that unifies the full voice I/O stack — TTS generation, voice cloning, real-time dictation, and agent voice integration — in a single local-first tool. No subscription or recurring API cost after initial setup. "Clone any voice. Generate speech. Dictate into any app. Talk to agents in voices you own."

## Key features

- **Seven TTS engines**: Qwen3-TTS (1.7B/0.6B, 10 languages), Qwen CustomVoice (preset speakers + instruct), LuxTTS (fast CPU English), Chatterbox Multilingual (23 languages), Chatterbox Turbo (English + paralinguistic tags), TADA/HumeAI (1B and 3B variants), Kokoro 82M (CPU realtime, 8 languages). Models auto-download from HuggingFace on first use.
- **Voice cloning** from audio samples with post-processing: pitch shift, reverb, delay, compression.
- **Global dictation hotkey** with push-to-talk and toggle modes (Whisper-based STT) — injects text into any focused app.
- **Stories Editor** for composing multi-voice podcasts or narrative audio with per-segment speaker assignment.
- **Unlimited generation length** via automatic chunking.
- **MCP server** exposing TTS to agents (Claude Code, Cursor, etc.) through a single tool call — agent-to-voice workflows without custom integration code.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Tailwind CSS (`/app`) |
| Desktop shell | Tauri (Rust) — not Electron; substantially smaller binary |
| Backend | Python FastAPI (`/backend`) |
| Database | SQLite |
| Inference (Apple Silicon) | MLX |
| Inference (other) | PyTorch with CUDA, ROCm, or Intel Arc |
| Build tooling | `just` command runner, Bun, Python 3.11+, Rust toolchain |

## Installation / quick-start

```bash
# Prerequisites: Bun, Rust toolchain, Python 3.11+
git clone https://github.com/jamiepine/voicebox
cd voicebox
just setup   # installs JS deps, Python venv, Rust deps
just dev     # starts Tauri desktop app with hot reload
```

Native installers available for macOS and Windows. Linux requires building from source. Models download automatically on first use — plan for several GB depending on which engines you enable.

## Notable APIs and design decisions

**REST API** (FastAPI backend):
- `POST /generate` — synthesize speech specifying engine and voice profile
- `POST /transcribe` — Whisper transcription of an audio file
- `GET/POST /models/*` — list available engines, trigger downloads
- `GET/POST /profiles` — manage voice personality profiles
- `GET /history` — retrieve past captures/generations
- `GET/POST /stories` — Stories Editor data

**MCP integration** — embedded MCP server means any agent supporting MCP tool calls can invoke Voicebox TTS without writing audio code. One tool call from Claude Code or Cursor produces audio output through a locally running voice.

**Tauri over Electron** — deliberate choice: significantly smaller binary and lower memory footprint than Electron, which matters when running alongside inference workloads.

**Auto-chunking** — transparently splits arbitrarily long text into model-sized chunks and stitches audio; callers do not need to manage input length limits per engine.

## Gotchas and caveats

**Active bugs in v0.5.0 (June 2026) — check PR status before using:**
- **macOS Apple Silicon crashes on all TTS model loads** (issues #606, #615) — fix exists in PR #789 but not yet merged. Apple Silicon users: treat app as broken until that PR lands.
- **Imported audio captures truncate at 30 seconds** (issue #609) — WAV re-encoding fix in PR #602, unmerged.
- **LLM text refinement silently translates non-English to English** (issue #603) — no warning shown; disable refinement for non-English workflows.
- **MCP tool naming does not follow Claude Desktop conventions** (issue #790) — may require manual MCP config adjustments.
- **DNS-rebinding vulnerability on local API/MCP server** (issue #778) — patches exist but unmerged. Do not expose the local port to untrusted networks.

**Maintenance posture (June 2026):** 34.8k stars, 1.3M downloads, but only 2 merges since v0.5.0 with 88 open PRs and 402 open issues. Several significant fixes exist as PRs not yet merged. Evaluate merge velocity before depending on this in production.

**Funding model:** tied to a Solana token ($VOICEBOX); the app is free and MIT-licensed but introduces non-standard sustainability risk.

**When to use:**
- Privacy-sensitive voice workflows where cloud TTS is not acceptable.
- Desktop tooling that benefits from MCP agent integration without writing audio infrastructure.
- Prototyping multi-engine TTS to compare quality across models on the same hardware.

**When to avoid (for now):**
- Apple Silicon production use until PR #789 is merged.
- Any non-English refinement workflow (silent translation bug).
- Projects requiring a stable, actively merged upstream.

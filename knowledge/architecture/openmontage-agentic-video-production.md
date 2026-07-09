---
title: OpenMontage: Agentic Video Production System
category: architecture
tags: [video-production, agentic-pipeline, ffmpeg, ai-orchestration, open-source, python]
created: 2026-06-28
source: https://github.com/calesthio/OpenMontage
---

# OpenMontage: Agentic Video Production System

**Repo:** https://github.com/calesthio/OpenMontage — AGPLv3, 25.3k stars

## What it is / what problem it solves

OpenMontage turns AI coding assistants (Claude Code, Cursor, Copilot, Windsurf, Codex) into autonomous video production studios. It addresses a gap in existing AI video tools: most either animate static images or depend end-to-end on expensive proprietary APIs. OpenMontage instead orchestrates a full pipeline — research, scripting, asset generation, editing, and composition — and can produce real motion videos from free/open footage archives without any paid API keys.

## Key features and components

**12 production pipelines** (YAML-defined in `pipeline_defs/`): Animated Explainer, Documentary Montage, Talking Head, Screen Demo, Cinematic, Clip Factory, Localization & Dub, Podcast Repurpose, Avatar Spokesperson, Animation, Hybrid, and custom workflows.

**52 Python tools** grouped by capability: video generation, image generation, TTS/audio, music, graphics, enhancement, analysis, avatar, and subtitles.

**500+ agent skill files** (markdown in `.agents/skills/`) encoding pipeline conventions, creative techniques, and core operations. These form the second layer of the three-layer knowledge model (see Architecture below).

**14 cloud video providers**: Kling, Runway Gen-4, Google Veo 3, HeyGen, MiniMax, Higgsfield, and others. Local GPU options include WAN 2.1, Hunyuan, CogVideo, and LTX-Video.

**Zero-API-key baseline**: Piper TTS (offline), Archive.org, NASA footage, Wikimedia Commons, Pexels/Pixabay/Unsplash. Fully functional without any paid credentials, though capability is limited.

**Two composition engines**:
- **Remotion** — React-based programmatic video, requires Node.js 18+
- **HyperFrames** — HTML/CSS/GSAP motion graphics, requires Node.js >= 22 (stricter than the baseline requirement)
- Both engines backed by FFmpeg for final assembly

**JSON Schema validation** (`schemas/`, 15 files) enforces contracts between pipeline stages.

## Installation / quick-start

```bash
git clone https://github.com/calesthio/OpenMontage.git
cd OpenMontage
make setup   # installs Python deps, npm deps, Piper TTS, copies .env.example
```

For local GPU video generation:
```bash
make install-gpu
# then set VIDEO_GEN_LOCAL_ENABLED=true in .env
```

Windows gotcha: if `npm install` fails with `ERR_INVALID_ARG_TYPE`, use `npx --yes npm install` instead.

Agent entry points are per-tool: `CLAUDE.md`, `CURSOR.md`, `COPILOT.md`, `CODEX.md` — all backed by the shared `AGENT_GUIDE.md` and `PROJECT_CONTEXT.md`.

## Notable patterns and design decisions

**Three-layer knowledge model** — the architecture that makes agentic operation practical:
1. Executable Python tools + YAML pipeline definitions (what to run)
2. Markdown skill files encoding production conventions (how to run it well)
3. External technology knowledge packs in `.agents/skills/` (domain context)

**Provider selection via 7-dimension scoring**: task fit (30%), output quality (20%), control (15%), reliability (15%), cost (10%), latency (5%), continuity (5%).

**Built-in quality governance**:
- Pre-compose validation blocks renders that score high on a 6-dimension "slideshow risk" metric or have unmet delivery promises
- Post-render self-review uses ffprobe + frame sampling + audio analysis
- Budget controls support observe/warn/cap modes with per-action approval thresholds

## Gotchas, caveats, and when to use vs not

- **Node.js version split**: HyperFrames composition engine requires Node >= 22; provision Node 22 from the start if you need motion graphics.
- **Local LLM not yet available**: Ollama/LM Studio listed as "coming soon."
- **AGPLv3 copyleft**: any service built on top and offered over a network must be open-sourced. Evaluate before embedding in commercial SaaS.
- **Zero-key mode is for prototyping**: quality and variety scale significantly with paid provider keys.
- **Documentary pipeline limited by open-source indexing**: niche topics may have sparse coverage; plan fallback to paid stock.

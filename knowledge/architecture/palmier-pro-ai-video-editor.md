---
title: "Palmier Pro: AI-Native Video Editor with Embedded MCP Server"
category: architecture
tags: [mcp, swift, video-editing, ai-agents, macos, avfoundation]
created: 2026-06-28
source: https://github.com/palmier-io/palmier-pro
---

# Palmier Pro: AI-Native Video Editor with Embedded MCP Server

**Repo:** https://github.com/palmier-io/palmier-pro | ~9,200 stars | Active

## What it is / problem it solves

Open-source macOS video editor (Swift 6.2) that embeds an MCP HTTP server directly inside the application process. Traditional video editors offer no programmatic control surface for AI agents — Palmier solves this by exposing 48 agent-accessible tools over a loopback MCP endpoint, letting LLMs read and manipulate the timeline, apply effects, generate media, and export without screen scraping or Accessibility APIs.

## Key features

**Editor core (free, no login)**
- Full non-linear timeline: tracks, clips, trimming, ripple edits, splits, moves
- Descript-style word-level speech removal (`removeWords` tool)
- On-device audio transcription and visual search across media library
- Keyframe animation, color grading (wheels, curves, LUTs, hue targeting)
- Text/caption overlays, audio sync via cross-correlation
- Lottie animation support
- Metal GPU shaders: chroma key, grain, glow, vignette, LUT tetra, curve grading

**MCP server (built-in)**
- 48 tools: timeline inspection/manipulation, clip properties, keyframe animation, color grading, text overlays, audio sync, AI media generation, media library management, export (MP4, FCPXML, XML, Palmier format)
- Runs on `http://127.0.0.1:19789/mcp` (loopback only)

**Generative AI (requires account/credits)**
- Video generation: Seedance2, Kling3, Veo, Grok
- Image generation: GPT-image-2, Nano Banana Pro
- Music and TTS generation

## Tech stack

| Layer | Technology |
|---|---|
| Language | Swift 6.2 |
| UI | SwiftUI + AppKit |
| Media | AVFoundation + Metal (custom `.metal` shaders via MetalCIKernelPlugin build plugin) |
| MCP | `swift-sdk` from modelcontextprotocol (>=0.11.0) |
| On-device ML | Swift Transformers (>=1.3.3) for local transcription |
| Auth/Backend | Clerk + Convex |

## MCP API quick-start

The app runs an MCP HTTP server at `http://127.0.0.1:19789/mcp`:
- `POST /mcp` — stateless JSON-RPC MCP requests
- `GET /mcp` — SSE stream for streaming responses

**Connect an external agent (e.g., Claude Desktop config):**
```json
{
  "mcpServers": {
    "palmier-pro": {
      "url": "http://127.0.0.1:19789/mcp"
    }
  }
}
```

The app must be running for the server to be available. No authentication required on loopback for editor tools; generative AI tools require account login. Body size limit ~1MB per request.

## Notable patterns and design decisions

**In-process MCP server** — runs inside the app process with direct access to in-memory timeline state; no IPC serialization overhead. Most MCP servers are standalone processes — this is unusual.

**AppKit fallback for broken SwiftUI drag-and-drop** — SwiftUI `.onDrop` is broken for nested drop zones on macOS 26. Uses native AppKit `NSDraggingDestination` for parent containers. Worth knowing for any nested drag targets on macOS 26 + SwiftUI.

**Audio sync via cross-correlation** — `audioSync` tool aligns clips by computing cross-correlation of waveforms; works without timecode or metadata.

**Word-level edit via transcription index** — `removeWords` uses on-device transcription to build a word-to-timecode index, then performs frame-accurate ripple deletes (same paradigm as Descript's "edit video like a doc").

**Metal shader build plugin** — custom `.metal` shaders compiled via `MetalCIKernelPlugin` build plugin, integrating GPU effects into the SwiftUI/AVFoundation pipeline.

## Gotchas / caveats

- **macOS 26 (Tahoe) + Apple Silicon only** — no Intel support, no older macOS versions.
- **MCP server is loopback-only** — remote agent access requires ngrok or cloudflared. Do not expose port 19789 directly.
- **Generative AI requires account/credits** — free tier covers editor and all 48 MCP tools; AI generation models fail without login.
- **Transitions, masking, and graphics not yet implemented** — early-stage product; MCP tool surface may expand and break agent scripts that hardcode tool names.
- **No Homebrew formula or one-liner install** — distribution is a macOS app download.
- **SwiftUI `.onDrop` bug on macOS 26** — use AppKit `NSDraggingDestination` for any nested container in extensions.
- **When to use**: building AI agent workflows that drive video editing programmatically; prototyping LLM-controlled video production on macOS; on-device transcription tightly integrated with editing.
- **When not to use**: Linux/Windows/Intel Mac; need a stable versioned API surface (actively changing); need remote/headless operation; purely file-in/file-out pipeline (FFmpeg + yt-dlp + Whisper is simpler and more portable).

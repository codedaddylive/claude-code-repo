---
title: "HyperFrames: Deterministic HTML-to-MP4 Video Rendering"
category: architecture
tags: [video-rendering, html-to-video, typescript, animation, headless-browser, ci-cd]
created: 2026-06-28
source: https://github.com/heygen-com/hyperframes
---

# HyperFrames: Deterministic HTML-to-MP4 Video Rendering

**Repo**: https://github.com/heygen-com/hyperframes | Apache 2.0 | 31.8k stars

## What it is

HyperFrames converts HTML, CSS, animations, and media into deterministic MP4 videos. Developers author compositions as ordinary HTML files with timing attributes, preview them live in a browser, then render to video via a CLI. Core guarantee: identical inputs always produce identical frames — suitable for CI/CD and AI agent pipelines. Built by HeyGen, no per-render fees.

## Key features

- **HTML-native authoring**: compositions are standard HTML files with `data-start` and `data-duration` attributes; no build step required for preview.
- **Multiple animation adapters**: GSAP, Lottie, Three.js, CSS animations, and WAAPI via a pluggable `FrameAdapter` interface.
- **Live studio**: preview server on port 3002 (`npx hyperframes preview`); playground at hyperframes.dev.
- **Shader transitions**: `@hyperframes/shader-transitions` for GPU-accelerated inter-scene transitions.
- **Cloud rendering**: first-class packages for AWS Lambda, GCP Cloud Run, and Kubernetes Jobs.
- **Agent skills**: 19 pre-built skills (`npx skills add heygen-com/hyperframes`); MCP tooling also exposed.

## Tech stack

TypeScript (87%), JavaScript (11%). Pipeline: Puppeteer (headless Chromium) seeks frames → FFmpeg encodes to MP4. Requires Node.js 22+. Monorepo packages: `core`, `engine`, `producer`, `player`, `studio`, `studio-server`, `cli`, `sdk`, `lint`, `parsers`, `shader-transitions`, `aws-lambda`, `gcp-cloud-run`.

## Installation and quick-start

```bash
npm install -g hyperframes

npx hyperframes init my-video
cd my-video
npx hyperframes doctor    # check Node/FFmpeg/Chrome deps
npx hyperframes preview   # live studio on :3002
npx hyperframes render    # outputs MP4
npx hyperframes lint      # validate composition HTML
```

Minimal composition:
```html
<div data-track="background" data-start="0" data-duration="3000">
  <video src="bg.mp4"></video>
</div>
<div data-track="title" data-start="500" data-duration="2000">
  <h1>Hello World</h1>
</div>
```

## Key APIs

| API | Purpose |
|-----|---------|
| `parseHtml(html)` | Extracts `TimelineElement[]` from a composition file |
| `generateHyperframesHtml(spec)` | Generates valid HF HTML from a programmatic spec |
| `compileTimingAttrs()` | Converts relative `data-start`/`data-duration` to absolute time values |
| `lintHyperframeHtml()` | Validates compositions; returns `{ errorCount, warningCount, infoCount, findings[] }` |
| `createGSAPFrameAdapter(timelineGetter, compositionId)` | Wires a GSAP timeline to the HF seek protocol (`window.__hf`) |

**FrameAdapter interface** (for custom animation libraries):
```typescript
interface FrameAdapter {
  id: string;
  getDurationFrames(): number;
  seekFrame(frame: number): void;
}
```

Use the `@hyperframes/core/lint` subpath for lint imports. Most users should depend on `cli`, `producer`, or `studio` — not `@hyperframes/core` directly.

## Gotchas and caveats

- **Node.js 22+ required** — `hyperframes doctor` will catch this.
- **FFmpeg is a separate system dep** — not bundled; install via `apt install ffmpeg` / `brew install ffmpeg`.
- **Puppeteer/Chromium managed separately** — use `hyperframes browser` to download after npm install.
- **Lint verbosity** — `npx hyperframes lint` only shows errors/warnings by default; pass `--verbose` for info-level findings.
- **Cloud IP blocking for external media** — in Lambda/Cloud Run, prefer pre-downloaded or CDN-hosted assets; network video fetches are subject to datacenter IP blocking.
- **When to use**: deterministic reproducible video for CI/CD or agent pipelines; HTML/CSS-native authoring; cloud-scale rendering.
- **When not to use**: editing existing footage (not a video editor); environments that can't run Node 22+ or install FFmpeg.

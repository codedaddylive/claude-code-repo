# Agent Onboarding Guide

> Read this at the start of every session. It defines who I am, what I'm building, and how I work.

---

## Project & Business Goals

**What I'm building:**

**ARIA (Adaptive Reasoning Intelligence Archive)** — a self-growing, **application-agnostic development brain** (`brain.py` + `knowledge/`) that stores settled architectural decisions, API patterns, and domain knowledge for **any project I work on, not just one app**. Every agent session checks ARIA before implementing anything, across every codebase.

ARIA is the primary system. Individual applications are *clients* of the brain — the first and reference application is the **Video Analysis Tool** (downloads/analyzes videos from YouTube, direct URLs, or local files using Claude vision + Whisper), which is why much of the current knowledge base is video-flavored. New applications add their own patterns/apis/architecture/domain entries alongside it; nothing about ARIA itself is video-specific.

**Business goal:** Reduce the cost of repeated research and implementation by encoding decisions once and reusing them across agents, sessions, **and applications**.

---

## Preferred Technical Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| API server | FastAPI |
| CLI | Typer |
| Validation | Pydantic v2 |
| Video download | yt-dlp |
| Frame extraction | OpenCV + ffmpeg |
| Transcription | Whisper (local) |
| AI vision | Anthropic Claude API |
| Multi-agent | Squad (SQLite) |
| Video rendering | Remotion (React/Node) |
| Knowledge base | Markdown files + brain.py |

---

## Coding Voice & Style

- **Concise over verbose** — short functions, no padding. If a function exceeds ~40 lines, split it.
- **No unnecessary comments** — code should read itself. Only comment non-obvious WHY, never WHAT.
- **No multi-line docstrings** — one short line max, or nothing.
- **Functional where practical** — prefer pure functions and immutability; avoid unnecessary classes.
- **Pydantic v2 for all I/O boundaries** — never raw dicts crossing module boundaries.
- **FastAPI patterns** — dependency injection, typed request/response models, explicit status codes.
- **No deprecated libraries** — check before suggesting any dependency.
- **No explanatory fluff before code blocks** — just the code.

---

## How I Like to Collaborate

- **Check ARIA first** — always run `python brain.py search <topic>` before implementing. If a pattern exists, use it.
- **Short updates while working** — one sentence at key moments, not running commentary.
- **Recommend, don't over-plan** — for exploratory questions, 2-3 sentences + a recommendation. Don't list every option.
- **Multi-agent when it makes sense** — use `/squad` to delegate parallel work to Gemini/Codex workers.
- **Commit early and often** — feature branches, descriptive messages, always push.
- **No backwards-compat hacks** — if something is unused, delete it cleanly.
- **Ask before risky actions** — destructive git ops, pushing to main, modifying CI, dropping data — always confirm first.

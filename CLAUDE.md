@agents.md
@memory.md
@context/project-overview.md

# GUARDRAIL — Scope Boundary

**This repository is for ARIA improvements only.**

Do NOT include, reference, push, or discuss anything related to:
- Connect for Health Colorado (C4HCO)
- C4 Report Builder (`c4-report-builder`)
- Any code, data, credentials, or config from C4 projects

If a task involves C4 or C4HCO in any way, stop and tell the user this repo is out of scope for that work.

---

# Video Extraction & Analysis Tool

## Project setup (run these first)

```bash
# 1. Clone the repo (if not already cloned)
git clone https://github.com/codedaddylive/claude-code-repo
cd claude-code-repo

# 2. Install system dependency
apt install ffmpeg        # Linux
brew install ffmpeg       # macOS

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set API key
export ANTHROPIC_API_KEY=sk-ant-...
```

## What this project does

Analyzes videos from YouTube, yt-dlp-supported platforms, direct URLs, or local files using:
- **Claude AI vision** — keyframe descriptions, object detection, visual summary
- **Whisper** — local audio transcription (no extra API cost)
- **yt-dlp + OpenCV + ffmpeg** — download, frame extraction, audio extraction

## Key commands

```bash
# Analyze a video (full pipeline)
python cli.py analyze "path/to/video.mp4" --max-frames 5 --output result.json

# YouTube / yt-dlp URL (works on home IPs, not datacenter/Colab)
python cli.py analyze "https://www.youtube.com/watch?v=..." --max-frames 5

# Extract frames only
python cli.py extract-frames "video.mp4" --output-dir ./frames --interval 5

# Transcribe only
python cli.py transcribe "video.mp4" --model base

# Start the API server
uvicorn api:app --host 0.0.0.0 --port 8000

# Run integration tests
python tests/integration_test.py
```

## Project structure

```
claude-code-repo/
├── cli.py                  # Typer CLI — analyze / extract-frames / transcribe
├── api.py                  # FastAPI server — POST /analyze, POST /analyze/upload
├── requirements.txt        # All Python dependencies
├── colab_demo.ipynb        # Google Colab notebook for browser-based use
├── video_tool/
│   ├── models.py           # Pydantic v2 models for all inputs/outputs
│   ├── downloader.py       # yt-dlp + direct URL + local file handling
│   ├── extractor.py        # Frame extraction (OpenCV) + audio (ffmpeg)
│   ├── transcriber.py      # Whisper transcription with model caching
│   └── analyzer.py         # Claude vision — keyframes, objects, summary
└── tests/
    └── integration_test.py # Full pipeline test (run to verify everything works)
```

## Architecture

```
Input URL/path
  → downloader.py   — download or copy video to temp dir
  → extractor.py    — extract frames (interval or scene-change) + audio WAV
  → transcriber.py  — Whisper transcription (cached model)
  → analyzer.py     — Claude vision analysis (batched, <= 10 frames/call)
  → AnalysisResult  — structured JSON output
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (sk-ant-...) |

## API server endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/analyze` | Analyze a video URL |
| POST | `/analyze/upload` | Analyze an uploaded file |
| GET | `/jobs/{job_id}` | Retrieve past result |

## Notes

- YouTube downloads blocked from datacenter/Colab IPs — use local files or home network
- Whisper base model downloads ~150MB on first run
- Claude vision batches up to 10 frames per API call
- All temp files cleaned up automatically after each run
- API server uses --workers 1 (in-memory job store)

---

## Agent Skills (via Vercel Skills CLI)

Before writing code for a common task, check if an installable skill already exists:

```bash
npx skills find [query]          # search the ecosystem
npx skills add <owner/repo>      # install a skill
npx skills add -g -y <pkg>       # install globally, no prompts
```

Browse at **https://skills.sh/** — prefer skills with 1K+ installs from `vercel-labs`, `anthropics`, or `microsoft`.
The `find-skills` skill is already installed — ask "find a skill for X" and it will search for you.

---

## ARIA — Adaptive Reasoning Intelligence Archive

**ARIA is an application-agnostic development brain — not tied to the video platform.**
It stores settled decisions, patterns, and domain knowledge for *any* project. The video
analysis tool is ARIA's first and reference client, which is why the current knowledge base
skews video; new applications add their own entries alongside it. Treat ARIA as the primary
system and each app as a consumer of it.

**Invoke ARIA by name.** When you say "ARIA, build this" or "ARIA, create this", consult
the knowledge base below first, then implement using the settled patterns and decisions it encodes.

The system sharpens through consistent reps, not perfect planning. Start by building.

```
BASE   →  raw/ (data lake)  +  knowledge/ (wiki)  +  skills in brain.py
UPLOAD →  brain.py upload / ingest   (bulk-ingest files into review queue)
INFLOW →  brain.py inflow add/run    (automated pipelines: Slack, transcripts, feeds)
LOOP   →  brain.py queue / review    (3 buckets: auto-approve / need-signoff / need-context)
DRIVE  →  brain.py list / search / show  (consume the wiki — always check before implementing)
```

**Always consult `knowledge/` before implementing something — these files encode settled decisions.**

Manage entries with `brain.py`:
```bash
# DRIVE — consume the wiki
python brain.py list                            # all entries
python brain.py list --category patterns        # filter by category
python brain.py search "fastapi"                # keyword search
python brain.py show patterns/fastapi-endpoint.md
python brain.py add --title "..." --category apis
python brain.py status                          # full system overview

# UPLOAD — ingest raw data
python brain.py upload path/to/file.txt --category patterns
python brain.py ingest                          # process all of raw/_inbox/

# INFLOW — automated pipelines
python brain.py inflow add                      # register a new source
python brain.py inflow list                     # view sources
python brain.py inflow run                      # pull from all active sources

# LOOP — review queue
python brain.py queue                           # view all 3 buckets
python brain.py review                          # interactive review (a/r/s/q)
python brain.py approve <id>                    # approve specific item
python brain.py reject  <id>                    # reject specific item

# MAINTAIN
python brain.py rebuild-index                   # regenerate index below
```

### Knowledge base index

#### Patterns
- **FastAPI endpoint patterns** — `knowledge/patterns/fastapi-endpoint.md`  tags: fastapi, python, api, routing
- **Pydantic v2 model patterns** — `knowledge/patterns/pydantic-models.md`  tags: pydantic, python, validation, models
- **Typer CLI patterns** — `knowledge/patterns/cli-typer.md`  tags: typer, cli, python
- **mattpocock/skills — Structured Agent Skill Library** — `knowledge/patterns/mattpocock-skills-agent-prompt-library.md`  tags: claude-code, ai-agents, prompt-engineering, tdd, skills
- **LLM Council — adversarial decision review** — `knowledge/patterns/llm-council-adversarial-decision-review.md`  tags: decision-making, multi-agent, squad, adversarial-review, judge-pattern

#### Apis
- **Anthropic Claude API usage** — `knowledge/apis/anthropic-claude.md`  tags: anthropic, claude, vision, ai, api
- **OpenAI Whisper (local) usage** — `knowledge/apis/whisper-transcription.md`  tags: whisper, transcription, audio, python
- **NVIDIA LocateAnything-3B — Visual Grounding API** — `knowledge/apis/locate-anything.md`  tags: object-detection, visual-grounding, bounding-box, video-pipeline, nvidia

#### Architecture
- **Preferred project layout** — `knowledge/architecture/project-layout.md`  tags: structure, layout, python, project
- **Video analysis pipeline architecture** — `knowledge/architecture/video-pipeline.md`  tags: architecture, pipeline, video, design
- **OpenMontage: Agentic Video Production System** — `knowledge/architecture/openmontage-agentic-video-production.md`  tags: video-production, agentic-pipeline, ffmpeg, ai-orchestration
- **DeerFlow: ByteDance Super Agent Harness** — `knowledge/architecture/deerflow-super-agent-harness.md`  tags: multi-agent, langgraph, orchestration, fastapi, sandboxed-execution
- **HyperFrames: Deterministic HTML-to-MP4 Rendering** — `knowledge/architecture/hyperframes-html-to-video.md`  tags: video-rendering, html-to-video, typescript, animation, ci-cd
- **Codebase Memory MCP** — `knowledge/architecture/codebase-memory-mcp.md`  tags: mcp, code-intelligence, knowledge-graph, tree-sitter
- **GStack: Structured AI Workflow Framework** — `knowledge/architecture/gstack-ai-workflow-framework.md`  tags: ai-coding, claude-code, workflow, slash-commands, multi-agent
- **SkillSpector: Security Scanner for AI Agent Skills** — `knowledge/architecture/skillspector-security-scanner.md`  tags: security, mcp, static-analysis, langgraph, supply-chain
- **Palmier Pro: AI-Native Video Editor with MCP** — `knowledge/architecture/palmier-pro-ai-video-editor.md`  tags: mcp, swift, video-editing, macos, avfoundation
- **Hermes Agent — Self-Improving Personal AI Agent** — `knowledge/architecture/hermes-agent-nous-research.md`  tags: ai-agent, self-improving, multi-platform, model-agnostic
- **Voicebox: Local-First AI Voice Studio** — `knowledge/architecture/voicebox-local-ai-voice-studio.md`  tags: voice-cloning, tts, local-first, tauri, mcp
- **Squad: Multi-Agent AI Coordination** — `knowledge/architecture/squad-multi-agent.md`  tags: multi-agent, coordination, sqlite, cli, claude-code, gemini
- **Autonomous Loop Engineering** — `knowledge/architecture/autonomous-loop-engineering.md`  tags: autonomous-loops, agent-engineering, triggers, goal-based, proactive
- **ARIA scope: application-agnostic development brain** — `knowledge/architecture/aria-scope-application-agnostic-development-brain.md`  tags: aria, scope, knowledge-base, cross-application, governance
- **agent-reach — internet research & sentiment capability** — `knowledge/architecture/agent-reach-internet-research-sentiment-capability.md`  tags: agent-reach, internet-research, sentiment, multi-platform, research

#### Domain
- **Video analysis domain concepts** — `knowledge/domain/video-analysis-concepts.md`  tags: video, analysis, domain, concepts
- **Anthropic Cybersecurity Skills Library** — `knowledge/domain/anthropic-cybersecurity-skills.md`  tags: cybersecurity, agent-skills, mitre-attack, security-workflows
- **Unlimited OCR — Single-Pass Long-Document Parsing** — `knowledge/domain/unlimited-ocr-baidu.md`  tags: ocr, document-parsing, vlm, sglang, pdf

## Squad Collaboration

This project uses [Squad](https://github.com/mco-org/squad) for multi-agent AI coordination.
Squad agents communicate via SQLite and can span Claude Code, Gemini, Codex, and OpenCode.

```bash
# Start a multi-agent session (use /squad slash command in Claude Code)
squad join <id> --role manager|worker|inspector
squad agents                          # see who's online
squad task create manager worker "<title>"
squad send <id> manager "<message>"
squad receive <id>
```

Roles in `.squad/roles/` are ARIA-aware — they check `brain.py` before acting.
See `knowledge/architecture/squad-multi-agent.md` for the full reference.


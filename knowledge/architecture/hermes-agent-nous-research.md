---
title: Hermes Agent — Self-Improving Personal AI Agent (Nous Research)
category: architecture
tags: [ai-agent, self-improving, multi-platform, python, model-agnostic, open-source]
created: 2026-06-28
source: https://github.com/nousresearch/hermes-agent
---

# Hermes Agent — Self-Improving Personal AI Agent (Nous Research)

**Repo:** https://github.com/nousresearch/hermes-agent | MIT

## What it is / what problem it solves

Open-source, self-improving personal AI agent that runs persistently across CLI, messaging platforms, a TUI, and an Electron desktop app. Core differentiator: a closed learning loop — the agent authors reusable skills from experience, curates and improves them in the background, and retires stale ones automatically. Explicitly model-agnostic, routing through any OpenAI-compatible provider.

## Key features and components

- **Self-improving skill system** — agent-authored skills archived when stale; background "Curator" process improves them over time. Bundled (in-tree) skills are never modified by the curator.
- **Multi-platform messaging gateway** — unified adapter framework for Telegram, Discord, Slack, WhatsApp, Signal, Email, Microsoft Teams, and Google Chat. A single `COMMAND_REGISTRY` drives CLI dispatch, gateway hook emission, Telegram `/help` menus, Slack routing, and autocomplete simultaneously.
- **Rich TUI** — multiline editing, command autocomplete, YAML-driven theming (`ui-tui/`). Built with Ink/React, communicates with the Python backend over newline-delimited JSON-RPC.
- **Scheduled automations** — SQLite-backed cron scheduler, file-locked to prevent duplicate ticks, with a 3-minute hard session interrupt.
- **Multi-agent delegation** — `delegate_task` spawns isolated leaf or orchestrator subagents; durable work uses cron or background terminal sessions.
- **Kanban task board** — SQLite-backed, multi-agent, per-board isolation with failure-limit auto-blocking.
- **Multiple terminal backends** — local, Docker, SSH, Modal, Singularity.
- **Profile support** — multiple independent instances via `HERMES_HOME` env var.

## Tech stack

| Layer | Technology |
|---|---|
| Conversation loop | Python (~12k-line `run_agent.py`), FastAPI or CLI entry |
| Session state | SQLite with FTS5 |
| Terminal UI | TypeScript/Node.js, Ink (React), JSON-RPC to Python |
| Desktop app | Electron + React + nanostore |
| Dependency mgmt | `uv`, Nix flake for reproducible dev |
| Deployment | Docker / docker-compose |

**Provider plugins:** OpenRouter (200+ models), OpenAI, Google Gemini, Ollama, Groq, Novita, Arcee, MiniMax, Kimi/Moonshot, ZhipuAI GLM, Hugging Face inference, and more.

## Installation / quick-start

```bash
# Linux / macOS / WSL2
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Windows PowerShell (no admin required)
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

Set your provider API key in `.env` and configure your model in `config.yaml`. Run tests via the project wrapper, not bare pytest:
```bash
scripts/run_tests.sh
```

## Notable patterns and design decisions

**"Narrow waist" tool surface** — the core tool surface is kept deliberately small. Footprint ladder for adding capability:
1. Extend existing code
2. Add a CLI command + skill
3. Add a service-gated tool
4. Write a plugin
5. Add an MCP server
6. Add a new core tool (last resort)

New in-tree memory providers are rejected by policy (as of May 2026) — ship them as standalone repos installed into `~/.hermes/plugins/`.

**Prompt caching is treated as sacred** — the system prompt must be byte-stable for the entire conversation lifetime. Slash commands that mutate system-prompt state default to deferred invalidation (takes effect next session). Use explicit `--now` flag to force immediate invalidation and accept the cache-bust cost.

**Tool discovery vs. toolset membership are separate concerns** — tools auto-discovered from `tools/*.py` via `registry.register()`, but which tools are active in a given context is explicit and manually managed in `toolsets.py`.

**Subprocess-per-test isolation** — custom pytest plugin enforces subprocess isolation per test; credentials unset during tests; real paths used — no mocks for I/O-touching code.

## Gotchas / caveats

- **Do not run `pytest` directly** — always use `scripts/run_tests.sh` for CI parity.
- **Never hardcode `~/.hermes`** — use `get_hermes_home()` for multi-profile setups.
- **Squash-merging stale branches** silently reverts recent fixes; be aware of branch age before merging.
- **Messaging gateway has two message guards** — both must allow approval/control commands to pass through or failures will be silent.
- **All dependencies require upper bounds**; run `uv lock` after any dependency change.
- **New memory providers belong outside the tree** — project policy rejects in-tree additions.
- **When to use**: persistent self-improving agent with out-of-the-box multi-platform messaging, a rich TUI, and the ability to swap LLM providers freely.
- **When not to use**: tightly scoped stateless function-calling harness (persistent loop and skill system add overhead); environments that cannot run SQLite and a Python long-lived process (e.g., serverless).

---
title: "Squad: Multi-Agent AI Coordination"
category: architecture
tags: [multi-agent, coordination, sqlite, cli, claude-code, gemini, codex]
source: https://github.com/mco-org/squad
added: 2026-06-29
---

# Squad: Multi-Agent AI Coordination

Squad is a lightweight CLI tool that lets multiple AI coding agents (Claude Code,
Gemini, Codex, OpenCode) coordinate on a shared goal via SQLite message passing.

## Installation

```bash
# Download Linux binary from GitHub Releases
curl -L https://github.com/mco-org/squad/releases/download/v0.7.6/squad-x86_64-unknown-linux-musl.tar.gz | tar xz
mv squad /usr/local/bin/squad
squad --version  # → squad 0.7.6

# Initialize workspace in project root
cd /your/project
squad init       # creates .squad/, installs /squad slash command in Claude Code
```

## Core Concepts

**Agents** — any AI terminal session that joins the squad with an ID and role.
Each agent runs `squad join <id> --role manager|worker|inspector`.

**Roles (in `.squad/roles/`)**:
- `manager.md` — decomposes goals, assigns tasks, collects results
- `worker.md` — executes code tasks, reports back
- `inspector.md` — reviews output, sends PASS/FAIL to manager

**Messages** — stored in `.squad/messages.db` (SQLite). Ephemeral — not committed to git.

**Tasks** — tracked work items with explicit lifecycle: created → acked → completed.

## Task Lifecycle

```bash
# Manager creates a tracked task
squad task create manager worker1 --title "Add FastAPI health endpoint" --body "..."

# Worker acknowledges
squad task ack worker1 <task-id>

# Worker completes
squad task complete worker1 <task-id> --summary "Added GET /health returning {status: ok}"

# Manager views task state
squad task list
```

## Message Passing

```bash
# Join the squad
squad join claude1 --role worker

# Send message
squad send claude1 manager "Task complete: refactored downloader.py"

# Send with task linkage (preferred for tracked tasks)
squad send --task-id <id> --reply-to <msg-id> claude1 manager "Complete"

# Receive messages
squad receive claude1        # check inbox once
squad receive claude1 --wait # block until message arrives

# Broadcast to all agents
squad send manager @all "New sprint starting"

# Check who's online
squad agents
```

## ARIA Integration Pattern

This project's Squad roles are ARIA-aware. The manager and worker roles both
check `brain.py` before acting:

```bash
# Manager checks before decomposing
python brain.py search "fastapi"      # → finds knowledge/patterns/fastapi-endpoint.md
python brain.py show patterns/fastapi-endpoint.md

# Worker checks before implementing
python brain.py search "pydantic"     # → finds settled model patterns
```

**Why this matters**: Workers don't reinvent patterns that are already in the knowledge
base. The manager's task brief includes the relevant ARIA entries so workers start
from known-good foundations.

## Multi-Agent Session Setup

Terminal 1 — Manager (Claude Code):
```
/squad
# Claude joins as manager and waits for user's goal
```

Terminal 2 — Worker (another Claude Code / Gemini / Codex instance):
```bash
squad join gemini1 --role worker
squad receive gemini1 --wait
```

Terminal 3 — Inspector:
```bash
squad join inspector1 --role inspector
squad receive inspector1 --wait
```

## Files to Commit vs Ignore

```gitignore
# Commit these (configuration)
# .squad/roles/
# .squad/teams/

# Ignore these (ephemeral)
.squad/sessions/
.squad/messages.db
```

## Stale Agent Cleanup

```bash
squad agents                  # shows [stale] next to inactive agents
squad leave <agent-id>        # archive stale agent, preserve unread messages
```

## Supported Agent Runtimes

- **Claude Code** — best integration; `/squad` slash command installed by `squad init`
- **Google Gemini CLI** — join with `squad join gemini1 --role worker`
- **OpenAI Codex** — same join pattern
- **OpenCode** — same join pattern

## Key Design Decisions

- SQLite transport means zero infra — works fully offline
- Roles are markdown files in `.squad/roles/` — easy to customise per project
- The `/squad` Claude Code slash command (at `~/.claude/commands/squad.md`) gives Claude
  a concise command reference without polluting system context
- Sessions directory (`~/.squad/sessions/`) is separate from the project workspace,
  so multiple projects can share the same installed binary

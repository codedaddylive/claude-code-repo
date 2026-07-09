---
title: "GStack: Structured AI Workflow Framework for Claude Code"
category: architecture
tags: [ai-coding, claude-code, workflow, slash-commands, developer-tooling, multi-agent]
created: 2026-06-28
source: https://github.com/garrytan/gstack
---

# GStack: Structured AI Workflow Framework for Claude Code

**Repo:** https://github.com/garrytan/gstack | MIT | 117k+ stars | by Garry Tan (YC President)

## What it is / what problem it solves

40+ slash-command skills for Claude Code that organize an AI assistant into specialized virtual team roles — CEO, Engineering Manager, Designer, Security Officer, QA, Release Engineer. Replicates cross-functional review discipline that larger engineering orgs provide, for solo builders and small teams.

## Core workflow

Enforces a **Think → Plan → Build → Review → Test → Ship → Reflect** cycle:

| Phase | Key commands | What happens |
|---|---|---|
| Product | `/office-hours` | Forcing-question product interrogation |
| Planning | `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review` | Structured planning with ratings and architecture diagrams |
| Planning (auto) | `/autoplan` | Runs the full planning pipeline in one shot |
| Code review | `/review` | Staff-engineer code audit with auto-fix for obvious bugs |
| Cross-review | `/codex` | Independent OpenAI Codex adversarial review |
| Design | `/design-review`, `/design-shotgun`, `/design-html` | Design consultation, multi-variant mockups, mockup-to-production HTML |
| QA | `/qa` | Real Chromium browser QA with automatic bug fixes and regression test generation |
| Ship | `/ship` | Syncs, tests, audits, squashes WIP commits, opens PR |
| Deploy | `/land-and-deploy`, `/canary` | Post-merge CI / deploy / monitoring |
| Security | `/cso` | OWASP Top 10 + STRIDE audit |
| Learning | `/retro`, `/learn` | Retrospectives and persistent cross-session learnings |

## Installation / quick-start

```bash
# Personal install
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup

# Team mode — commits .claude/ config into the repo so teammates share settings
./setup --team
gstack-team-init required
```

Re-run `./setup` after every `git pull` (setup creates symlinks that must be refreshed).

**Runtime requirements:** TypeScript, Bun v1.0+ (Node.js on Windows), Playwright/Chromium for `/qa` and `/browse`.

## Key features and design decisions

**GBrain — persistent knowledge base**: Vector store (Supabase, PGLite, or remote MCP) that persists learnings across sessions and repos. Each repo gets a trust tier: read-write, read-only, or deny. Sync with `/sync-gbrain`. On remote machines, requires ngrok or Tailscale.

**Continuous checkpoint mode**: Auto-commits WIP with a `WIP:` commit prefix. After crash/context loss, `/context-restore` reconstructs state from WIP history. `/ship` squashes all WIP commits before opening the PR.

**Browser automation**: `/browse` drives headed Chromium via Playwright with a CDP allowlist (`browse/src/cdp-allowlist.ts` — deny-by-default; any raw CDP method requires a one-line justification comment to allowlist). Supports CAPTCHA handoff.

**Multi-host support**: Works across Claude Code, OpenAI Codex CLI, Cursor, Factory Droid, Slate, Kiro, and Hermes via a `--host` flag.

**Parallel sprints**: Integrates with Conductor to fan out 10-15 parallel Claude Code sessions simultaneously.

**Telemetry**: Off by default. When opted in, only collects skill name, duration, pass/fail, OS. Schema is public in `supabase/migrations/`.

## Gotchas and caveats

1. **Windows symlinks** — Developer Mode must be enabled; re-run `./setup` after every `git pull` or symlinks break silently.
2. **API key conflicts with Conductor** — Use `GSTACK_ANTHROPIC_API_KEY` / `GSTACK_OPENAI_API_KEY` instead of bare env vars inside Conductor workspaces.
3. **`/codex` requires a separate OpenAI account** — Codex CLI must be installed independently; fails silently if missing.
4. **GBrain on remote machines** — Requires ngrok or Tailscale; no built-in tunneling.
5. **CDP allowlist is deny-by-default** — Any raw CDP call not in `cdp-allowlist.ts` will be blocked.
6. **`/ship` runs `/document-release` automatically** — Keeps docs current but adds latency to every ship cycle; no flag to skip it.
7. **Design taste memory decays 5% per week** — ML classifier for design preferences degrades without ongoing feedback.

## When to use vs. not

**Use GStack when:**
- Solo builder or small team wanting structured code review, security audits, and QA without hiring those specialists.
- Want persistent AI learnings that survive across sessions and are scoped per-repo.
- Ship frequently and want `/ship` to enforce test, audit, and squash discipline before every PR.

**Skip GStack when:**
- Your team already has established CI/CD, code review, and QA processes — GStack duplicates rather than integrates with them.
- Need fully headless CI (the `/qa` and `/browse` skills require a display or virtual framebuffer).
- Not on Claude Code or one of the explicitly supported hosts.

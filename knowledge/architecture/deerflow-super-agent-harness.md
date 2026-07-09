---
title: "DeerFlow: ByteDance Super Agent Harness"
category: architecture
tags: [multi-agent, langchain, langgraph, orchestration, fastapi, sandboxed-execution]
created: 2026-06-28
source: https://github.com/bytedance/deer-flow
---

# DeerFlow: ByteDance Super Agent Harness

**Repo:** https://github.com/bytedance/deer-flow — MIT, 75k+ stars, #1 GitHub Trending Feb 2026

## What it is / what problem it solves

DeerFlow is an open-source orchestration harness built by ByteDance that coordinates parallel sub-agents, sandboxed execution environments, and persistent long-term memory for complex, long-duration AI tasks. It bridges the gap between a single-turn LLM call and a persistent, multi-agent autonomous work system. Version 2.0 (early 2026) is a ground-up rewrite — no shared code from v1.

## Key features and components

- **Sub-agent spawning** — Tasks decomposed and delegated to parallel sub-agents (max 3 concurrent) with scoped contexts and hard 15-minute timeouts. Includes a bash-specialist sub-agent.
- **Sandboxed execution** — Each thread gets isolated filesystem access via virtual paths (`/mnt/user-data/` mapped to per-thread physical directories). Backends: local, Docker, or Kubernetes.
- **Long-term memory** — User profiles and knowledge persisted across sessions via a memory-extraction middleware layer.
- **Progressive skill loading** — Skills defined by `SKILL.md` files discovered recursively. Only loaded on demand, keeping per-call token cost low.
- **9-component middleware chain** — Handles sandbox acquisition, memory extraction, context summarization, tool integration, and more.
- **IM integrations** — Telegram, Slack, Feishu/Lark, WeChat, WeCom, DingTalk.
- **Observability** — LangSmith and Langfuse tracing can run simultaneously.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, LangChain/LangGraph |
| Frontend | TypeScript, Node.js 22+ |
| Infrastructure | Docker Compose, nginx, optional Kubernetes |
| Tool protocol | MCP (configurable server list) |

## Installation / quick-start

```bash
git clone https://github.com/bytedance/deer-flow.git
cd deer-flow
make setup        # interactive wizard: LLM provider, web search, sandbox backend (~2 min)
make dev          # local development
make docker-start # Docker-based development
make up           # production
```

UI available at `http://localhost:2026`. Minimum: 4 vCPU / 8 GB RAM. Recommended: 8 vCPU / 16 GB RAM.

## Notable patterns and design decisions

- **In-process gateway** — FastAPI gateway embeds the agent runtime directly (not remote RPC). Simpler deployment, less horizontal scaling flexibility.
- **Virtual path abstraction** — Sandbox filesystem locations addressed via virtual paths; storage backends are swappable without changing agent code.
- **Aggressive context compression** — Summarization and compression middleware run mid-workflow to avoid context-limit failures on long sessions.
- **Thread-local isolation** — Per-request temp directories with automatic cleanup; no shared mutable state between concurrent agent threads.

## Gotchas and caveats

- **Security risk is real** — Includes system command execution and filesystem operations. The project explicitly warns against public deployment. Use only on trusted local networks.
- **No v1 migration path** — v2.0 is a complete rewrite. Start from scratch.
- **Concurrency cap** — Sub-agent parallelism hard-capped at 3, with a 15-minute timeout per agent.
- **Wizard-locked configuration** — LLM provider and sandbox backend set during `make setup`. Changing them requires re-running the wizard.
- **When to use** — Multi-step research, code generation with execution, document processing pipelines, tasks requiring persistent memory and parallel decomposition.
- **When not to use** — Simple single-turn queries, latency-sensitive apps, environments where arbitrary command execution poses unacceptable risk.

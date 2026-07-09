---
title: "SkillSpector: Security Scanner for AI Agent Skills and MCP Servers"
category: architecture
tags: [security, mcp, ai-agents, static-analysis, langgraph, supply-chain]
created: 2026-06-28
source: https://github.com/nvidia/skillspector
---

# SkillSpector: Security Scanner for AI Agent Skills and MCP Servers

**Repo:** https://github.com/nvidia/skillspector — Apache 2.0, NVIDIA

## What it is

Pre-installation security scanner for AI agent skills — MCP servers, agent plugins, and tool packages. Acts as an antivirus gate before a skill enters your agent environment. Empirical research across 42,447 skills shows 26.1% contain vulnerabilities and 5.2% show likely malicious intent. Targets threats unique to agentic contexts: prompt injection, data exfiltration, privilege escalation, and supply chain attacks.

## Key features

**Detection surface — 68 patterns across 17 categories:**
- Prompt injection and anti-refusal bypasses
- Data exfiltration (network calls, file reads, env var leaks)
- Dangerous code execution: `exec`, `eval`, `subprocess`, `os.system`
- Taint tracking (user-controlled data flowing to sinks)
- MCP-specific issues (tool description manipulation, resource abuse)
- Supply chain risks via live CVE lookups against OSV.dev

**Two-stage pipeline:**
- Stage 1: Fast static analysis — regex, Python AST parsing, YARA rules, OSV.dev dependency checks
- Stage 2: Optional LLM semantic pass (~87% precision) with human-readable explanations. LLM prompts include anti-jailbreak guards so a malicious skill cannot manipulate its own analysis.

**Risk scoring (0-100):**
- CRITICAL finding: +50 | HIGH: +25 | MEDIUM: +10 | LOW: +5
- Executable scripts get a 1.3x multiplier
- Bands: SAFE (0-20), CAUTION (21-50), DO NOT INSTALL (51+)
- CI-friendly exit codes: 0 = safe/caution, 1 = do-not-install, 2 = error

**Output formats:** terminal, JSON, Markdown, SARIF 2.1.0 (integrates with GitHub Code Scanning, VS Code)

**MCP server mode:** Run SkillSpector itself as an MCP server so agents can call `scan_skill()` as a runtime guardrail — agents scan before installing other agents.

## Installation and quick-start

```bash
# Recommended — installs as isolated tool
uv tool install git+https://github.com/NVIDIA/skillspector.git

# MCP server support
pip install "skillspector[mcp]"

# Docker (no Python required)
make docker-build

# Scan a local skill directory
skillspector scan ./my-mcp-server/

# Fast, fully offline (no LLM, only OSV.dev for supply chain)
skillspector scan ./my-mcp-server/ --no-llm

# SARIF output for CI (exit 1 if score > 50)
skillspector scan ./my-mcp-server/ --format sarif --output results.sarif

# Register as MCP server with Claude Code
claude mcp add skillspector
```

**Python API:**
```python
from skillspector import graph
result = graph.invoke({"skill_path": "./my-mcp-server"})
```

## Architecture and design decisions

**LangGraph workflow** — entire analysis pipeline is a LangGraph graph. All 22 analyzer nodes run in parallel after a shared context-building step, then converge at a meta-analyzer node. Adding new analyzers is cheap — no orchestration code to touch.

**`SkillspectorState` TypedDict** — shared graph state: carries skill metadata, raw file contents, cached ASTs, per-analyzer findings, and report parameters. Analyzers are pure functions over this state.

**Pluggable analyzer interface:**
```python
def analyze(content: str, file_path: str, file_type: str) -> AnalyzerNodeResponse:
    ...
```

**LLM provider abstraction** — configured entirely via env vars:
```bash
SKILLSPECTOR_PROVIDER=anthropic   # or openai, bedrock, nv_build, ollama, vllm
SKILLSPECTOR_MODEL=claude-opus-4-8
```
Default provider is NVIDIA's inference endpoint (`nv_build`), requiring `NVIDIA_INFERENCE_KEY`.

**Multi-format input:** local directory, single file, zip archive, or remote Git URL — auto-clones/unpacks.

**Baseline/suppression:** accept known findings so rescans only surface new issues; glob rules by rule ID, file path, or message.

## Gotchas and when to use vs. not

**Use when:**
- Vetting third-party MCP servers or agent plugins before production
- Running CI checks on skill repos before publishing to a marketplace
- Embedding a scan gate in an agent that auto-installs plugins

**Do not rely on it as your only defense when:**
- Skills use runtime-only malicious behavior (purely static analysis — never executes code)
- Skills contain non-English text, encrypted payloads, or binary/image-encoded logic (known detection gaps)
- You need guaranteed false-positive-free output — LLM stage hits ~87% precision

**Privacy:**
- `--no-llm`: keeps file contents local; only OSV.dev receives dependency names
- Air-gapped mode (`--no-llm` + no network): uses bundled CVE list — reduced coverage, zero external data exposure
- With LLM enabled: full file contents sent to configured provider — choose provider matching your data classification requirements

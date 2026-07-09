---
title: Codebase Memory MCP — Persistent Knowledge Graph for AI Coding Agents
category: architecture
tags: [mcp, code-intelligence, knowledge-graph, static-analysis, ai-agents, tree-sitter]
created: 2026-06-28
source: https://github.com/DeusData/codebase-memory-mcp
---

# Codebase Memory MCP — Persistent Knowledge Graph for AI Coding Agents

**Repo:** https://github.com/DeusData/codebase-memory-mcp

## What it is / what problem it solves

Indexes a software repository into a persistent structural knowledge graph and exposes it to AI coding agents via MCP. Replaces agents reading files one-by-one to answer structural questions with sub-millisecond graph queries. Benchmark: 5 structural queries cost ~3,400 tokens via graph vs ~412,000 tokens through raw file exploration — a 120x reduction.

## Key features

**Indexer**
- Full-indexes Django (49K nodes, 196K edges) in ~6 seconds; Linux kernel (28M LOC) in ~3 minutes.
- 158 languages via vendored tree-sitter grammars compiled into the binary.
- Hybrid LSP layer: lightweight C reimplementation of type-resolution from tsserver, pyright, gopls, Roslyn, Eclipse JDT, and rust-analyzer for 10 languages (Python, TS/JS/JSX/TSX, PHP, C#, Go, C/C++, Java, Kotlin, Rust). Resolves cross-file call edges, generics, inheritance, and stdlib types without running a language server.

**Graph data model**

Node labels: `Project`, `Package`, `Folder`, `File`, `Module`, `Class`, `Function`, `Method`, `Interface`, `Enum`, `Type`, `Route`, `Resource`.

Edge types: `CALLS`, `HTTP_CALLS`, `ASYNC_CALLS`, `IMPORTS`, `DEFINES`, `IMPLEMENTS`, `EMITS`, `LISTENS_ON`, `DATA_FLOWS`, `SIMILAR_TO`, `SEMANTICALLY_RELATED`, `TESTS`, `FILE_CHANGES_WITH`, plus cross-repo `CROSS_*` variants.

**14 MCP tools** (selection):

| Tool | Purpose |
|---|---|
| `index_repository` | Initial full index (absolute path required) |
| `search_graph` | Regex name-pattern search across nodes |
| `trace_path` | Symbol-to-symbol path tracing |
| `detect_changes` | Git diff → symbol-level blast radius + risk classification |
| `query_graph` | openCypher read-subset queries (`MATCH/WHERE/RETURN`) |
| `get_architecture` | High-level architecture summary |
| `search_code` | BM25 + semantic hybrid search |
| `manage_adr` | CRUD for Architecture Decision Records (survive session restarts) |

**Tech stack**: pure C, statically linked binary, zero runtime dependencies. SQLite (WAL mode) for graph storage. Bundled `nomic-embed-code` embeddings (768-dim int8) for local semantic search — no external API. BM25 via SQLite FTS5 with camelCase/snake_case-aware tokenizer. zstd for team-shareable graph artifact compression.

## Installation / quick-start

```bash
# One-line install (macOS/Linux)
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash

# Auto-configure all detected agents
codebase-memory-mcp install

# Manual MCP config — add to .mcp.json
# { "mcpServers": { "codebase-memory": { "command": "codebase-memory-mcp" } } }

# CLI mirror for any MCP tool
codebase-memory-mcp cli search_graph '{"name_pattern": ".*Handler.*"}'
codebase-memory-mcp cli detect_changes '{"diff": "$(git diff HEAD~1)"}'
```

State persists to `~/.cache/codebase-memory-mcp/` (override with `CBM_CACHE_DIR`).

## Notable patterns and design decisions

**Claude Code `PreToolUse` hook integration** — installer adds a hook that intercepts `Grep` and `Glob` calls and injects graph-augmented context as `additionalContext`. Non-blocking, always exits 0.

**openCypher read-subset query engine** — supports `MATCH/WHERE/RETURN`, variable-length paths, aggregates, and `EXISTS` sub-patterns:
```cypher
MATCH (f:Function)-[:CALLS*1..3]->(g:Function {name: "processPayment"})
RETURN f.name, f.file
```

**Team-shareable graph artifact** — commit `.codebase-memory/graph.db.zst` to let teammates skip full reindexes. Paired with background file watcher for incremental re-indexing on save.

**Infrastructure-as-code as first-class nodes** — Dockerfiles, Kubernetes manifests, and Kustomize overlays indexed alongside application code; `detect_changes` and `trace_path` work across both.

**`manage_adr` for session-persistent decisions** — Architecture Decision Records stored in the graph survive agent session restarts. Use to record non-obvious design choices so the agent doesn't re-litigate them.

## Gotchas and caveats

- **Absolute paths only** — `index_repository` fails on relative paths. Always pass `os.path.abspath()` or `$(pwd)/...`.
- **`trace_path` requires exact symbol names** — use `search_graph` first to find the canonical name.
- **openCypher engine is read-only** — `MERGE`, `CREATE`, `CALL`, list/map literals not supported; will return explicit error.
- **UI visualization is a separate binary** — the 3D graph viewer at `localhost:9749` requires downloading the UI variant explicitly.
- **Windows SmartScreen** — binary is unsigned; manually allow and verify against `checksums.txt`.
- **When to use**: large or unfamiliar codebases; impact analysis before refactors; teams wanting a shared queryable architecture artifact.
- **When not to use**: tiny repos; when you need semantic understanding of business logic (the graph is structural; language understanding comes from the agent).

---
title: Cross-session agent coordination: git bus vs. Mosaic
category: architecture
tags: [multi-agent, coordination, git, mosaic, cross-session, async]
created: 2026-07-09
---

# Cross-session agent coordination: git bus vs. Mosaic

## Decision

For coordinating multiple Claude Code sessions/agents (e.g. a web session + an EC2 session),
ARIA uses a **git-based async message bus**, not a hosted shared-terminal product. Evaluated
Mosaic (mosaic.inc) as the productized alternative — kept the git approach for our constraints.

## The built approach (git bus)

1. **Shared branch (`ARIA`)** — one session commits+pushes, the other pulls. Carries all real work.
2. **`COORDINATION.md`** — standing mailbox on the branch: log entries newest-on-top, tagged
   OPEN / DONE / FYI; standing rules (rebase-not-reset, record tip hash after push, no credentials).
3. **Handoff flow**: A appends entry -> push -> human nudges B ('read COORDINATION.md, act on OPEN')
   -> B pulls, works, appends DONE with new tip hash -> A verifies hash. Loop closed.
4. **Discipline**: on divergence, REBASE onto the other's work (never reset -> data loss). Hit live
   twice this session; preserved both sides both times.

## Mosaic (the alternative)

macOS app: shared terminals + connect everyone's agents in real time. Hobby free; Team ~$20/seat/mo
(up to 20 seats) — pricing unverified (site network-blocked; confirm at mosaic.inc/pricing).

## When to use which

| Factor | git bus (built) | Mosaic |
|---|---|---|
| Cost | free | free solo / ~$20 seat team |
| Platform | any (git) | macOS only |
| Network need | GitHub only (already allowed) | its own relay (BLOCKED in our web/EC2 env) |
| Interaction | async, nudge-driven handoffs | live shared terminal |
| Setup | none beyond git+GitHub | install app, hosted account |

**Switch to Mosaic only if**: on macOS, open network, and you need *live* shared terminals.
**Stay on the git bus if** (our case): Linux/EC2, restrictive network, async handoffs are fine —
it works where Mosaic's backend can't even connect, and costs nothing.

## Cross-links
- `COORDINATION.md` (the live channel + protocol)
- `knowledge/architecture/squad-multi-agent.md` (in-machine multi-agent; git bus is cross-machine)

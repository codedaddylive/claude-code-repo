---
title: mattpocock/skills — Structured Agent Skill Library for Claude Code
category: patterns
tags: [claude-code, ai-agents, prompt-engineering, tdd, developer-workflow, skills]
created: 2026-06-28
source: https://github.com/mattpocock/skills
---

# mattpocock/skills — Structured Agent Skill Library for Claude Code

## What it is / problem it solves

A curated collection of small, composable agent skills (structured prompt files) that Matt Pocock uses daily in Claude Code. Addresses four recurring AI agent failure modes: agent misalignment (building the wrong thing), excessive verbosity, broken feedback loops (coding without types/tests/browser), and accelerated software entropy from unchecked AI-assisted development speed. Model-agnostic plain text instructions — the developer stays in control.

## Key skills

**User-invoked (you type them):**

- `/grill-me` / `/grill-with-docs` — Relentless Q&A interview before any coding starts. `grill-with-docs` also builds a `CONTEXT.md` domain glossary and Architecture Decision Records (ADRs).
- `/tdd` — Red-green-refactor TDD loop. Enforces vertical slices (one test + minimal implementation at a time), tests through public interfaces only, no speculative code.
- `/diagnosing-bugs` — Disciplined bug loop: reproduce → minimise → hypothesise → instrument → fix → regression-test.
- `/to-prd` — Synthesizes a conversation into a Product Requirements Document and pushes it to the issue tracker.
- `/to-issues` — Breaks a PRD or plan into independently-grabbable vertical-slice issues.
- `/triage` — State-machine label workflow for issue triage (GitHub Issues, Linear, or local markdown).
- `/improve-codebase-architecture` — Scans for "deepening opportunities," presents an HTML report, then grills through improvements.
- `/prototype` — Builds throwaway prototypes: terminal apps for logic questions or multiple UI variants on one route.
- `/handoff` — Compacts a long conversation into a handoff doc for a fresh agent session.
- `/domain-modeling` — Actively challenges and refines the project glossary; updates `CONTEXT.md` and ADRs.

**Model-invoked (agent reaches for automatically):**
- `/git-guardrails-claude-code` — Blocks dangerous git commands (force push, `reset --hard`, `clean`).
- `/setup-pre-commit` — Adds Husky + lint-staged + Prettier + type-check + test pre-commit hooks.

## Installation / quick-start

```bash
npx skills@latest add mattpocock/skills
```

Then inside your agent session: **run `/setup-matt-pocock-skills` before any other skill.** It wires up your issue tracker choice (GitHub Issues, Linear, or local markdown), label mappings, and docs directory layout.

## Notable patterns and design decisions

**`disable-model-invocation: true` flag** — user-invoked skills declare this flag to prevent the agent from autonomously chaining into them. The agent cannot silently start a full TDD loop without explicit invocation.

**Compositional skill references** — skills call each other. `grill-with-docs` internally invokes `grilling` and `domain-modeling`. Keeps individual skills small and single-purpose.

**`CONTEXT.md` as the central artifact** — many skills read from and write to a shared `CONTEXT.md` that serves as a living domain glossary. This is the core mechanism for shared vocabulary, reducing token usage and keeping naming consistent across sessions and files. Treat it as a first-class project artifact.

**Vertical slice enforcement** — `/tdd` and `/to-issues` are explicitly opinionated: one thin slice of behavior end-to-end at a time, not all tests or all infrastructure first.

**Philosophy against large orchestration frameworks** — skills explicitly reject opinionated orchestration systems (GSD, BMAD, Spec-Kit) in favor of small, composable primitives.

## Gotchas / caveats

- **Always run `/setup-matt-pocock-skills` first.** Without it, other skills have no issue tracker config, label mappings, or known docs directory — they behave incorrectly or fail silently.
- **`CONTEXT.md` must be actively maintained.** If it drifts from the actual codebase, the shared-language benefit evaporates.
- **Vertical slice TDD is non-negotiable in `/tdd`.** It will actively resist horizontal TDD (writing a full test suite before any implementation).
- **Use when**: you want disciplined, fundamentals-grounded AI-assisted development with explicit human control at every major decision point. Valuable on long-running projects where domain vocabulary needs to stay coherent across many agent sessions.
- **Do not use when**: you want fully autonomous "vibe coding" end-to-end. These skills keep a human in the loop at every major decision point.

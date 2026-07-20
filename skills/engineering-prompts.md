# Skill: 8 Ready-to-Copy Engineering Prompts

**Trigger**: You want a strong, reusable prompt for a common software-engineering
task (build from scratch, refactor, debug, design, optimize, review, or build UI).

---

## When to Use

- Starting a non-trivial engineering task and want a senior-level framing
- You want repeatable prompt quality instead of ad-hoc one-liners
- Driving one of the model clients in this repo (`video_tool/analyzer.py` for
  Claude, `gemini_interaction.py`, `grok_interaction.py`) or the loop harness
  (`agent_loop.py`)

Prompt #7 (Multi-Agent Workflow) is **implemented as code** in
`agent_loop.run_pipeline` — see the note at the bottom.

---

## The prompts

### 1. Complete Application from Scratch
> Act as a senior full-stack engineer. Before writing code, design the
> architecture. Then build a scalable MVP: file structure, database schema, API
> endpoints, and UI. Explain key decisions and trade-offs as you go.

### 2. Codebase Understanding & Refactoring
> Analyze this large, unfamiliar codebase. Identify issues — duplication,
> bottlenecks, and maintainability risks — then refactor for clarity and
> structure **without changing functionality**. Explain each change.

### 3. Senior Debugging Engineer
> Debug this with a production mindset. Do step-by-step root-cause analysis,
> consider edge cases, and deliver a robust fix (not just a patch). State your
> hypothesis, how you'd confirm it, and why the fix is correct.

### 4. System Design + Implementation
> Produce a full system design: architecture, data flow, caching, scaling, and
> failure modes. Then provide a minimal viable implementation of the core path.

### 5. Performance Optimization
> Optimize this for speed, memory, and scalability. Identify the bottlenecks
> with reasoning, then deliver optimized code and quantify the expected impact.

### 6. Clean Architecture Rebuild
> Restructure this code for clean architecture: separation of concerns,
> modularity, and reduced coupling. Preserve behavior; improve boundaries.

### 7. Multi-Agent Workflow
> Simulate four collaborating agents to solve this task:
> **Architect** (design) → **Engineer** (implement) → **Reviewer** (find issues)
> → **Optimizer** (produce the final polished version). Pass each agent's output
> to the next.

### 8. Production-Level UI Component Builder
> Build a reusable, accessible, responsive UI component. Include loading states,
> error/empty/edge cases, keyboard support, and sensible props/defaults.

---

## Prompt #7 is runnable in this repo

`agent_loop.run_pipeline` implements the Architect → Engineer → Reviewer →
Optimizer chain, with an optional different model per role:

```python
from agent_loop import run_pipeline, claude_responder, gemini_responder, grok_responder

result = run_pipeline(
    "Build a token-bucket rate limiter with tests.",
    responders={
        "Architect": claude_responder(),
        "Engineer":  grok_responder(),
        "Reviewer":  gemini_responder(),
        "Optimizer": claude_responder(),
    },
)
print(result.final)
```

Or from the CLI (single model for all roles):

```bash
python agent_loop.py "Build a token-bucket rate limiter." --pipeline --model claude
```

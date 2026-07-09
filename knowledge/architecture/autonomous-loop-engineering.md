---
title: "Autonomous Loop Engineering — Claude Code Patterns"
category: architecture
tags: [autonomous-loops, agent-engineering, claude-code, triggers, goal-based, proactive]
source: Anthropic Claude Code team internal practices
added: 2026-06-30
---

# Autonomous Loop Engineering

Four loop types used by the Claude Code team at Anthropic for agentic task management.

## The Four Loop Types

### 1. Turn-based
Human triggers each step manually. Agent gathers context, acts, returns control.
- **Use when**: exploring, debugging, tasks that need human judgment at each step
- **ARIA today**: default `/claude` session model

### 2. Goal-based
Agent works toward defined success criteria. A **separate judge model** verifies the work — the agent must not self-evaluate.
- **Use when**: tasks with a clear definition of done (tests pass, PR merged, file matches spec)
- **ARIA today**: Squad manager/worker/inspector — inspector is the judge
- **Critical**: always use a separate agent as judge, never let the worker verify its own output

### 3. Time-based
Triggered on a schedule. Agent checks state, acts if needed, stays silent otherwise.
- **Use when**: monitoring (PR status, news feeds, inbox), recurring data pulls
- **ARIA today**: Voicebox PR watcher (daily at 10am via `create_trigger`)
- **Pattern**: silent by default, only notify on actionable change

### 4. Proactive
Combines schedule + goal. Monitors platforms (Slack, GitHub, email), triggers dynamic workflows when conditions are met. Closest to an autonomous employee.
- **Use when**: issue triage, PR review automation, alert response
- **ARIA today**: not yet built
- **Next build**: GitHub issue monitor → ARIA wiki lookup → auto-draft response

---

## Best Practices

### 1. Define Done
Every loop needs explicit success criteria before it starts.
```
BAD:  "Fix the tests"
GOOD: "All tests in test_api.py pass with exit code 0"
```

### 2. Set Stop Criteria
Prevent runaway loops — always cap retries and token usage.
```python
MAX_RETRIES = 3
MAX_TOKENS = 50_000

retries = 0
while not done and retries < MAX_RETRIES:
    result = agent.run(task)
    retries += 1
```
For Squad: include `--max-retries 3` in task body or manager briefing.

### 3. Pilot Before Scaling
Run the task manually once (turn-based) before committing to an autonomous loop.
The `skills/` directory enforces this — document the manual workflow first, automate second.

### 4. Outsource to Scripts
Deterministic, repetitive work should be code, not AI tokens.
```
BAD:  ask Claude to rename 50 files
GOOD: write a Python script, ask Claude to verify the output
```
In ARIA: `brain.py`, `cli.py`, and the Typer commands exist for exactly this reason.

### 5. Monitor Usage
Check token and API consumption regularly, especially for proactive loops.
```bash
# Claude Code Remote — check trigger run history
mcp__Claude_Code_Remote__list_triggers
```

---

## Loop Engineering in ARIA

### Current loop inventory

| Loop | Type | Trigger | Status |
|---|---|---|---|
| Daily session | Turn-based | Manual `claude` | Active |
| Voicebox PR watch | Time-based | Daily 10am UTC | Active |
| Squad task cycle | Goal-based | `/squad` command | Active |
| GitHub issue monitor | Proactive | Not built | Planned |

### Building a goal-based loop with Squad

```bash
# Manager defines done explicitly
squad task create manager worker1 \
  --title "Add /summarize endpoint" \
  --body "Done when: POST /summarize returns {summary: str}, all tests pass, PR is open. Max 3 retries."

# Inspector is the judge — worker cannot self-approve
squad task complete worker1 <task-id> --summary "Implemented, tests pass"
# → manager forwards to inspector
# → inspector sends PASS/FAIL
```

### Building a time-based loop with triggers

```python
# Via Claude Code Remote MCP
create_trigger(
    name="...",
    cron_expression="0 10 * * *",   # daily 10am UTC
    prompt="Check X. If condition met: act + notify. If not: do nothing."
)
```

**Silent by default rule**: time-based loops should only fire a notification when something actionable has changed. Never ping on "no change."

---

## Learned Behavior Pattern

Claude Code doesn't update its weights, but it approximates learning through:

1. **`memory.md`** — rules appended each session, read at every session start
2. **`skills/`** — workflows encoded after manual piloting
3. **`brain.py`** — settled decisions stored after each feature
4. **`create_trigger`** — Claude creates its own scheduled monitors
5. **Hooks (`settings.json`)** — fire shell commands on Claude Code events (Stop, PreToolUse, PostToolUse)

The full learned-behavior loop:
```
Observe pattern → encode in memory.md / skills / brain.py
               → create trigger if recurring
               → add hook if event-driven
```

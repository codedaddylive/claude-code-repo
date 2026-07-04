---
name: llm-council
description: >-
  Adversarial decision review for consequential, hard-to-reverse decisions.
  MUST be used PROACTIVELY (without being asked) before committing to a choice
  that is BOTH high-cost-if-wrong AND hard-to-undo: adopting a dependency or
  library, choosing an architecture or framework, committing to an API shape or
  data model, picking a vendor, greenlighting a feature, or any "should we
  adopt/switch to/commit to X" question. Runs five independent adversarial
  personas, then a SEPARATE judge renders the verdict. NOT for routine coding,
  reversible edits, or small choices — those use normal "recommend, don't
  over-plan". When in doubt whether a decision qualifies, mention the council is
  available rather than forcing it.
---

# LLM Council — Adversarial Decision Review

**Trigger (BOTH must hold, else skip and just recommend):** the decision is
**(a) consequential** — wrong choice costs real rework — **AND (b) hard-to-reverse**
— a dependency/architecture/API/data-shape/vendor commit, not a code detail you can
edit later. Routine work stays "recommend, don't over-plan"; the council is the exception.

**Proactive use:** invoke this yourself when a qualifying decision surfaces — the user
should not have to name it. If it's borderline, say "this looks council-worthy" and offer.

**Default is solo mode.** Run the five passes + an isolated judge yourself (subagent, or a
fresh judge pass). Escalate to live Squad agents only for the biggest calls.

**Retire rule:** after ~3-5 real uses, if it hasn't caught something a plain recommendation
would have missed, drop it. It must earn its keep, not become ceremony.

**Goal:** surface blind spots before committing, via five independent personas, then a
separate judge — the agent under review never grades its own decision.

---

## The five personas

Run each as an independent pass. Do not let one persona's output soften another's.

| Persona | Mandate |
|---|---|
| **The Contrarian** | Argue the decision is wrong. Strongest case against, steelmanned. |
| **The First-Principles Thinker** | Strip assumptions. What's actually true? Rebuild from constraints, not convention. |
| **The Expansionist** | Second-order effects, scale, what this unlocks or blocks in 12 months. |
| **The Outsider** | No context. Would this make sense to someone seeing it cold? Flags jargon-justified choices. |
| **The Executor** | Cost to ship, maintain, and reverse. What breaks first. Concrete next steps. |

---

## Workflow

### 1. Frame the decision (one line, explicit)
```
BAD:  "Should we use X?"
GOOD: "Adopt X as ARIA's default Y, replacing Z, this quarter."
```

### 2. Check ARIA first
```bash
python brain.py search "<decision keyword>"
```
A settled entry may already answer it — cite it, skip the council.

### 3. Run the five passes
Each persona produces: **position** (support/oppose), **top-2 reasons**, **one blind spot**.
Keep them independent — no shared draft.

### 4. Judge with a SEPARATE agent (never self-grade)
**Judge independence is the load-bearing part — enforce it or the whole thing is ceremony.**
The judge sees ONLY the five final positions, never the deliberation, and runs in a fresh
context. Correlated errors are the real risk: five personas from one model share blind
spots, so the value is the *independent verifier*, not the five roles.

- **Claude Code:** spawn a subagent as the judge (fresh context), or route to the Squad
  **inspector** (`squad task create manager inspector1 ...`) if Squad is running.
- **Plain chat (no subagents):** run the judge as a second, fresh conversation with the
  five positions and the instruction *"you did not author these — judge cold."*

### 5. Synthesize
Output: **verdict** (proceed / proceed-with-changes / don't), **the decisive reason**,
**the top blind spot**, **3 concrete next steps**.

### 6. Encode the outcome
```bash
python brain.py add --title "Decision: <X>" --category architecture
```

---

## Why a separate judge

Mirrors ARIA's goal-based loop rule (`knowledge/architecture/autonomous-loop-engineering.md`):
the worker must not verify its own output. The council *generates* perspectives; the judge
*judges*. Same separation that makes Squad's PASS/FAIL trustworthy.

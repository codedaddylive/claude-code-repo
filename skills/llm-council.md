# Skill: LLM Council — Adversarial Decision Review

**Trigger**: A consequential, hard-to-reverse decision — adopt a dependency, pick an
architecture, commit to an API, greenlight a feature. NOT for routine coding.

**Goal**: Surface blind spots before committing, via five independent personas that
argue, then a separate judge (Squad inspector) that renders the verdict — the agent
under review never grades its own decision.

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
Route the five positions to the Squad **inspector** — the same PASS/FAIL judge used for code:
```bash
squad task create manager inspector1 \
  --title "Council verdict: <decision>" \
  --body "Five council positions attached. Return PASS (proceed) or FAIL (don't) + the
          single most important blind spot the council surfaced. You did not make this
          decision — judge it cold."
```
Solo (no squad running): spawn a fresh judge pass with a clean context and the explicit
instruction *"you did not author these positions."*

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
the worker must not verify its own output. The council *generates* perspectives; the
inspector *judges*. Same separation that makes Squad's PASS/FAIL trustworthy.

---

## Invocation Example

```
Run skills/llm-council.md on: "Adopt the LLM Council pattern as ARIA's decision-review default."
```

---
title: Five Gates of Reasoning (Fable Mode)
category: patterns
tags: [reasoning, fable-mode, verification, calibration, decision-making, portable-prompt]
created: 2026-07-07
---

# Five Gates of Reasoning (Fable Mode)

## Pattern

A portable, model-agnostic reasoning discipline — the framework "Fable Mode" names. Applies
per-answer to elevate output quality; lighter than the full [[llm-council]], which is the
heavy, decision-only instantiation of gates 1-4. Five gates, run in order:

1. **Scoping** — define the goal in one line before starting. Restate what the request is
   actually asking beneath the literal words. (Same move as the council's "frame the decision"
   step and the autonomous-loop "Define Done" rule.)
2. **Evidence** — gather facts before reasoning. Run `python brain.py search <topic>` first; a
   settled entry may already answer it. Never reason from memory when the repo has ground truth.
3. **Attacking** — reason adversarially. Steelman the case against your own conclusion; ask where
   the real risk lives. (Encoded in [[llm-council-adversarial-decision-review]] — the Contrarian
   persona and "attack your own conclusion before handing it over".)
4. **Verifying** — re-derive the claim instead of trusting that it sounds right, and prefer a
   SEPARATE judge over self-checking. The agent that produced an answer must not be the sole
   verifier of it. (See the separate-judge rule in [[autonomous-loop-engineering]].)
5. **Calibrating** — the gate ARIA under-documented until now. After an answer:
   - attach a **confidence level** (0.0-1.0 or low/med/high),
   - explicitly **separate what's known/verified from what's assumed/guessed**, and label it out loud,
   - state the **one thing that would change the verdict**,
   - match the strength of the claim to the strength of the evidence.
   Code embodiment already in the repo: `video_tool/analyzer.py::assess_viability` returns
   `{verdict, confidence 0.0-1.0, reasoning}`, and `cli.py` prints `VERDICT ... (confidence N%)`.
   That is calibration working in code; this entry makes it a reusable practice, not just output.

## When to use

Any consequential answer, not only formal decisions. For high-cost + hard-to-reverse decisions,
escalate to the full [[llm-council]] (five personas + independent judge). For everyday careful
work, run the five gates inline.

## Five-question self-check (run before sending)

1. Scoping — do I have the goal in one line, and is it the real ask?
2. Evidence — did I check ARIA / gather facts before reasoning?
3. Attacking — did I try to break my own conclusion?
4. Verifying — did I re-derive it, ideally with a separate check?
5. Calibrating — did I state confidence, and separate what's known from what's guessed?

## Relationship to existing entries

Unifies rather than duplicates: gates 1-4 already live in [[llm-council]],
[[llm-council-adversarial-decision-review]], and [[autonomous-loop-engineering]]; this entry
names the whole framework and adds the missing Calibrating gate. No redundancy — it references
those homes rather than restating them.

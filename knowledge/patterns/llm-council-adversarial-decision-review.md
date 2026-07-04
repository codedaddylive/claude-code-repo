---
title: LLM Council — adversarial decision review
category: patterns
tags: [decision-making, multi-agent, squad, adversarial-review, karpathy, judge-pattern]
created: 2026-07-04
---

# LLM Council — adversarial decision review

## Pattern

Five independent advisor personas debate a consequential decision; a **separate judge**
(Squad inspector) renders the verdict. The deciding agent never grades its own call.

Personas: **Contrarian** (steelman the case against), **First-Principles Thinker**
(strip assumptions), **Expansionist** (second-order effects at scale), **Outsider**
(cold-read sanity check), **Executor** (cost to ship/maintain/reverse).

## When to use

Consequential, hard-to-reverse decisions — adopting a dependency, architecture choice,
API commitment, feature greenlight. NOT routine coding.

## Why a separate judge

Same rule as goal-based loops (see `autonomous-loop-engineering.md`): the agent that
generates an answer must not verify it. The council generates perspectives; the Squad
inspector judges PASS/FAIL cold. This is what makes the verdict trustworthy.

## How

Operational workflow lives in `skills/llm-council.md`. Flow: frame the decision in one
line -> check ARIA for an existing answer -> run five independent persona passes ->
route positions to a separate judge -> synthesize (verdict + decisive reason + top
blind spot + 3 next steps) -> encode the outcome with `brain.py add`.

## Relationship to existing ARIA entries

- Judge role: reuses Squad's inspector (`squad-multi-agent.md`).
- Separation-of-judge principle: `autonomous-loop-engineering.md` (goal-based loops).
- Complements, does not replace, DeerFlow/Squad multi-agent orchestration.

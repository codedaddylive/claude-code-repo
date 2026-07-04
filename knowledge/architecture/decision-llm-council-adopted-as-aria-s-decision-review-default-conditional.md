---
title: Decision: LLM Council adopted as ARIA's decision-review default (conditional)
category: architecture
tags: [decision, llm-council, governance, squad, judge-independence]
created: 2026-07-04
---

# Decision: LLM Council adopted as ARIA's decision-review default (conditional)

## Decision

Adopt the LLM Council (`skills/llm-council.md`) as ARIA's default review for
consequential + hard-to-reverse decisions. Verdict from its own first run: CONDITIONAL-PASS
(five personas + an independent judge agent).

## Decisive reason

Near-zero cost, trivially reversible, and it compounds knowledge quality across apps —
but only if the judge is genuinely independent.

## Top blind spot the council surfaced

**Correlated errors.** Five personas from one model share training priors, so a shared
blind spot survives all five votes. The load-bearing mechanism is independent generation
+ an ISOLATED verifier — not the five roles (which are decoration).

## Conditions (now baked into the skill)

1. Judge independence enforced — fresh context, sees only the five final positions.
   Without this it degrades to self-grading → FAIL.
2. Concrete trigger — consequential AND hard-to-reverse; solo mode is the default;
   routine work stays 'recommend, don't over-plan'.
3. Earns its keep — after ~3-5 uses, if it hasn't caught something solo review missed,
   retire it. Risk is ossification, not sunk cost.

## Meta

First real use of the council was judging its own adoption — dogfooded. Judge ran as a
separate agent (Squad offline → fresh-context fallback per the skill).

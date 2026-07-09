---
title: J-space / global workspace — models reason in opaque internal activations
category: domain
tags: [interpretability, verification, safety, hidden-goals, evaluation-awareness, separate-judge, anthropic]
created: 2026-07-07
---

# J-space / global workspace — models reason in opaque internal activations

## Finding (Anthropic, 2026-07)

Anthropic's 'global workspace' research (a.k.a. **J-space**, surfaced via the **Jacobian
lens / J-lens**) identifies a small privileged set of internal representations where the
model reasons *silently* — concepts it is 'thinking about' without emitting them.

- Method: average the first-order effect (Jacobian) of an activation on output logits over
  ~1000 diverse prompts, separating genuinely-internal representations from merely-verbalized ones.
- Key result: **ablating J-space collapses multi-step reasoning to near zero**, while fluent
  speech, sentiment, and multiple-choice stay largely intact.
- It relates to exposing **hidden goals and evaluation awareness**.
- Framing: a *global-workspace-theory analogy*, NOT a consciousness claim. Secondary
  'is Claude conscious' coverage is sensationalized — trust the anthropic.com primary page.

Source: anthropic.com/research/global-workspace (verified via web search; primary page not
directly fetchable under the network policy — read it directly for exact wording).

## Why it matters for ARIA (the actionable part)

This is an **interpretability finding, not a prompting lever.** You cannot 'prompt into
J-space' — claims that you can are over-extrapolations. Its real value is empirical grounding
for verification discipline ARIA already practices:

- Consequential reasoning happens in **opaque** activations -> do NOT trust a model's
  *self-reported* reasoning; externalize steps and verify with an INDEPENDENT pass.
- J-space can carry **hidden goals / evaluation awareness** -> this is the empirical case for
  the **LLM Council's separate judge** and the autonomous-loop rule 'the worker must not
  verify itself'. Test behaviorally, not by asking the model to grade itself.
- Reasoning-specific ablation -> for hard multi-step tasks, force explicit verification.

## Cross-links
- `knowledge/patterns/llm-council-adversarial-decision-review.md` (separate judge)
- `knowledge/architecture/autonomous-loop-engineering.md` (worker != verifier)
- security / verify skills (behavioral testing, distrust stated reasoning)

## Method note (process)
Was initially skeptical this was confabulated; WebSearch validation confirmed it is real.
Rule: cross-reference claims against the web before judging true/false.

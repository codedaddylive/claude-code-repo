---
title: ARIA scope: application-agnostic development brain
category: architecture
tags: [aria, scope, knowledge-base, cross-application, governance]
created: 2026-07-03
---

# ARIA scope: application-agnostic development brain

## Decision

ARIA is an **application-agnostic development brain**, not a component of the video platform.
It captures settled decisions, patterns, API usage, and domain knowledge for *any* project the
user works on. The video analysis tool is ARIA's first and reference client — the current
knowledge base skews video only because that was the first app, not because ARIA is scoped to it.

## Rationale

- `brain.py` and `knowledge/` are already domain-neutral (entries are categorized as
  patterns / apis / architecture / domain — nothing video-specific).
- Coupling ARIA's identity to one app blocks its core business goal: reuse decisions across
  agents, sessions, AND applications.

## Implications for agents

- Treat ARIA as the primary system; each application is a *consumer* of the brain.
- New applications add their own `knowledge/` entries alongside the video ones.
- 'Off-domain' is NOT a reason to reject knowledge. Judge new knowledge on: is it a settled,
  reusable decision? Not: does it relate to video?

## Applied example — AIOS intake engine (2026-07-03)

Evaluated a proposed 'AIOS Data Intake Engine' (Gmail/Slack/Fathom MCP intake with
proposal files). Verdict: SKIP — redundant with ARIA's existing INFLOW (`inflow add/run`)
and LOOP (`queue/review/approve`) pipeline. Note: rejected for architectural redundancy,
NOT for being sales/CRM domain — under an app-agnostic brain, that domain would be valid.

---
title: agent-reach — internet research & sentiment capability
category: architecture
tags: [agent-reach, internet-research, sentiment, multi-platform, skill, research]
created: 2026-07-04
---

# agent-reach — internet research & sentiment capability

## What it is

`agent-reach` (Panniantong/Agent-Reach) is an **installed skill** giving ARIA internet
research across 15 platforms via multi-backend routing (OpenCLI / per-platform CLIs / APIs).
This entry exists because the capability was installed as a skill but not documented — so
future sessions know ARIA already covers internet research and don't rebuild it.

## Channels

search / social (xiaohongshu, twitter/X, bilibili, V2EX, reddit, facebook, instagram) /
career (linkedin) / dev (github code search) / web (pages, articles, RSS) /
video (youtube, bilibili, podcasts).

## When to use

Any 'research / search / look up / what are people saying about X' task, or when a URL /
platform is mentioned. Invoke the `agent-reach` skill; run `agent-reach doctor --json`
to see which backend serves each platform.

## Covers (do NOT rebuild)

Public sentiment analysis across Reddit/X/YouTube/etc. is already this skill's job — a
separate 'sentiment scanner' mode is redundant. Reject such proposals; point here.

## Hard constraint in restricted environments

Requires outbound egress to the target platforms. In the Claude Code web/EC2 environment,
the network policy blocks those hosts (same wall as video ingest) — agent-reach only
functions where the network is open (local/home machine). See analyze-video skill's
network-policy notes.

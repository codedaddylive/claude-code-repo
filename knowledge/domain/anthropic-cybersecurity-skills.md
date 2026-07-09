---
title: Anthropic Cybersecurity Skills — Structured Security Competency Library for AI Agents
category: domain
tags: [cybersecurity, agent-skills, mitre-attack, ai-agents, security-workflows, knowledge-base]
created: 2026-06-28
source: https://github.com/mukul975/Anthropic-Cybersecurity-Skills
---

# Anthropic Cybersecurity Skills

**Repo:** https://github.com/mukul975/Anthropic-Cybersecurity-Skills
**Version:** v1.3.0 (June 2026) | Apache 2.0 | 22.2k stars

Note: community project, not an official Anthropic product despite the name.

## What it is / problem it solves

817 structured cybersecurity skill files designed to be loaded on demand into AI agents via the agentskills.io standard. Generic LLM prompts cannot encode practitioner-level specificity for tasks like DPAPI credential extraction or Kubernetes RBAC auditing. This library fills that gap with pre-packaged, machine-readable workflows — the agent loads only the skill it needs rather than hallucinating security procedures.

## Key features

- **817 skills across 29 domains**: Cloud Security, Threat Hunting, Malware Analysis, Digital Forensics, Incident Response, Container/Infrastructure Security, Cryptography/Blockchain, Authentication Systems, Network Analysis, Web Application Security, and more.
- **Six simultaneous framework mappings per skill**: MITRE ATT&CK v19.1, NIST CSF 2.0, MITRE ATLAS v5.4, MITRE D3FEND v1.3, NIST AI RMF 1.0, and MITRE F3 v1.1 (cyber-enabled financial fraud — 94 skills, 123 technique IDs, added April 2026).
- **Progressive disclosure architecture**: `index.json` exposes ~30-token descriptions for all 817 skills (cheap to scan), then agent loads full `SKILL.md` (~500–2,000 tokens) only for the skill it needs.
- **26+ platform compatibility**: Claude Code, GitHub Copilot, Cursor, and any agentskills.io-compatible tool.
- **Validation toolchain**: `tools/validate-skill.py` (Python 3.8+, stdlib-only) enforces required YAML frontmatter; runs in CI via GitHub Actions.

## Installation / quick-start

```bash
# Via npx (agentskills.io CLI)
npx skills add mukul975/Anthropic-Cybersecurity-Skills

# Or clone directly
git clone https://github.com/mukul975/Anthropic-Cybersecurity-Skills
```

No runtime dependencies for the skills themselves — static Markdown/YAML files. Python 3.8+ (stdlib only) required only if running the validation toolchain.

For Claude Code: the `.claude-plugin/` directory provides plugin configuration for direct integration.

## Skill file structure

```yaml
---
name: kubernetes-rbac-audit
description: Audit Kubernetes RBAC bindings for privilege escalation paths
domain: Container Security
subdomain: Authorization
tags: [kubernetes, rbac, privilege-escalation]
mitre_attack: ["T1078", "T1548"]
nist_csf: ["ID.AM-3", "PR.AC-4"]
# ... other framework IDs
---
```

Body sections: **When to Use**, **Prerequisites**, **Workflow** (numbered steps), **Verification**, **Reference Materials**, plus optional embedded scripts or report templates.

## Programmatic discovery pattern

Agents use a two-step load:

1. Fetch `index.json` at repo root — `skills` array with `name`, `description`, `domain`, `path` per entry. ~30 tokens per skill to scan the full catalog.
2. Load the full skill: `skills/<skill-name>/SKILL.md`

```python
index = fetch("index.json")
match = next(s for s in index["skills"] if "dpapi" in s["description"].lower())
skill_content = fetch(match["path"])
```

`mappings/` directory holds bulk framework mapping data for compliance queries (e.g., all skills mapped to NIST CSF PR.AC-4) without loading individual files.

## Gotchas and caveats

- **Offensive and dual-use content is explicitly included** — requires authorized, lawful use and written permission before applying any technique to systems you don't own.
- **Community-maintained, not vendor-guaranteed** — treat skills as starting-point workflows to be validated by a practitioner, not authoritative runbooks.
- **Uneven domain coverage** — Deception Technology and Compliance/Governance domains are underdeveloped.
- **Index.json must stay in sync** — if you fork and add skills without regenerating `index.json`, agents will silently miss new skills. Always regenerate in fork CI.
- **When to use**: loading practitioner-level security workflows on demand; compliance mapping across multiple frameworks; structured skill discovery in multi-agent pipelines.
- **When not to use**: as an authoritative compliance tool without practitioner review; automated pipelines on production systems without human-in-the-loop approval.

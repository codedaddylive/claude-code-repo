# Workflow: Add Knowledge Entry

**Trigger**: A new architectural decision, API pattern, or domain rule has been settled and needs to be encoded in ARIA.

---

## When to Use

- Just figured out how something works (API quirk, encoding flag, framework pattern)
- Made an architectural decision that future agents should follow
- Discovered a constraint or failure mode worth remembering
- Completed a feature and want to preserve the approach

---

## Steps

### 1. Check if it already exists

```bash
python brain.py search "<topic keyword>"
```

If a relevant entry exists, update it instead of creating a duplicate (`python brain.py show <path>` to read it first).

### 2. Add the entry

```bash
python brain.py add --title "Short descriptive title" --category <category>
```

Categories: `patterns` | `apis` | `architecture` | `domain`

This opens an editor. Write the entry in this format:

```markdown
---
title: "..."
category: ...
tags: [tag1, tag2, tag3]
source: https://... (if applicable)
added: YYYY-MM-DD
---

# Title

One-sentence summary of what this encodes.

## The Decision / Pattern

What it is and how to use it.

## Why (not What)

The non-obvious reason this decision was made.

## Code Example

(if applicable)

## Constraints / Gotchas

What to watch out for.
```

### 3. Rebuild the index

```bash
python brain.py rebuild-index
```

### 4. Update CLAUDE.md index

Copy the new entry line from the rebuild output and add it to the correct category section in `CLAUDE.md`.

### 5. Commit

```bash
git add knowledge/ CLAUDE.md
git commit -m "Add knowledge: <title>"
git push -u origin <current-branch>
```

---

## Quick One-Liner (for simple rule additions)

For small rules discovered mid-session, append directly to `memory.md`:

```
[YYYY-MM-DD] Rule — reason
```

---

## Invocation Example

```
Follow skills/add-knowledge.md — we just settled that imageio-ffmpeg must be used for H.264 encoding.
```

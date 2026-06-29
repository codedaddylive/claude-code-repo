# Workflow Template

> Copy this file and rename it for each reusable workflow.
> Reference it in conversation: "follow the workflow in skills/my-workflow.md"

---

## Workflow Name

**One-line description of what this workflow accomplishes.**

---

## Trigger

When to use this workflow:
- [ ] Condition 1
- [ ] Condition 2

---

## Steps

### 1. Pre-flight checks
```bash
# Commands to verify environment/dependencies before starting
python brain.py search "<relevant topic>"   # check ARIA first
```

### 2. [Step name]

**What**: Brief description
**How**:
```bash
# Commands or code
```
**Output**: What to expect

### 3. [Step name]

**What**: Brief description
**How**:
```bash
# Commands or code
```
**Output**: What to expect

### 4. Verify & commit

```bash
# Verify the output
# Stage and commit
git add <files>
git commit -m "..."
git push -u origin <branch>
```

---

## Example Invocation

```
Follow the workflow in skills/this-workflow.md for [specific input].
```

---

# Existing Workflows

## `skills/analyze-video.md` ← create this next

**Trigger**: When I want to analyze a new video end-to-end
**Steps**: download → extract frames → transcribe → Claude vision → save JSON result

---

## `skills/add-knowledge.md` ← create this next

**Trigger**: After settling a new architectural or API decision
**Steps**: draft entry → `python brain.py add` → `python brain.py rebuild-index` → update CLAUDE.md index → commit

---

## `skills/new-feature.md` ← create this next

**Trigger**: Adding a new endpoint or CLI command
**Steps**: check ARIA patterns → scaffold with existing pattern → write Pydantic model → implement → test → commit + PR

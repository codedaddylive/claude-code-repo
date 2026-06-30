# OWASP A06 — Vulnerable and Outdated Components

**Stack**: Python 3.11, pip, requirements.txt
**Trigger**: Audit dependencies for known CVEs before deploying or after incidents.

---

## Audit Commands

```bash
# Install audit tool (pip-audit uses OSV + PyPI Advisory DB)
pip install pip-audit

# Scan all dependencies
pip-audit -r requirements.txt

# Or scan installed environment
pip-audit

# Check for unpinned dependencies (version ranges allow silent upgrades)
grep -E "^[a-zA-Z]" requirements.txt | grep -v "==" | grep -v "^#"
```

---

## Priority packages to watch for this project

| Package | Why it matters |
|---|---|
| `yt-dlp` | Actively maintained — update frequently, it patches extractor bugs |
| `anthropic` | SDK updates add features and patch auth issues |
| `openai-whisper` | Less frequent updates, but check for CVEs |
| `opencv-python` | Large C++ codebase — check for image parsing CVEs |
| `fastapi` / `starlette` | HTTP parsing vulnerabilities affect all routes |
| `pydantic` | Validation bypass CVEs have occurred in v1 |

---

## Fix patterns

**Pin all versions in requirements.txt:**
```
anthropic==0.28.0
fastapi==0.111.0
pydantic==2.7.1
yt-dlp==2024.5.27
```

**Automate audit in CI (GitHub Actions):**
```yaml
- name: Audit dependencies
  run: |
    pip install pip-audit
    pip-audit -r requirements.txt --fail-on-vuln
```

**Update yt-dlp regularly (it patches site extractors weekly):**
```bash
pip install --upgrade yt-dlp
```

---

## Verification

```bash
pip-audit -r requirements.txt
# Should output: "No known vulnerabilities found" or list items to fix
```

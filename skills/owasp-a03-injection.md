# OWASP A03 — Injection

**Stack**: FastAPI, Pydantic v2, Python 3.11, ffmpeg, yt-dlp
**Trigger**: Audit for shell injection via user-supplied URLs, filenames, or parameters.

---

## What to look for

This app passes user input to subprocesses (ffmpeg, yt-dlp, Whisper).
Shell injection is the primary injection risk — not SQL.

- User-supplied URL passed directly to `yt-dlp` or `ffmpeg` subprocess
- Filenames derived from user input used in shell commands
- `subprocess.run(..., shell=True)` anywhere in codebase

---

## Audit Checklist

```bash
# Find all subprocess calls
grep -rn "subprocess\|os\.system\|os\.popen\|shell=True" video_tool/ cli.py api.py

# Find where user input touches file paths
grep -rn "url\|path\|filename" video_tool/downloader.py

# Confirm shell=False everywhere
grep -rn "shell=True" .
```

---

## Fix patterns

**Never use shell=True with user input:**
```python
# BAD — shell injection possible
subprocess.run(f"yt-dlp {user_url}", shell=True)

# GOOD — list form, no shell interpolation
subprocess.run(["yt-dlp", "--no-playlist", user_url], shell=False, check=True)
```

**Sanitize output filenames — never use raw user input as filename:**
```python
import re, pathlib

def safe_filename(raw: str) -> str:
    # strip everything except alphanumeric, dash, underscore, dot
    return re.sub(r"[^\w\-.]", "_", pathlib.Path(raw).name)[:128]
```

**Pydantic URL validation (already in your stack — use it):**
```python
from pydantic import BaseModel, HttpUrl

class AnalyzeRequest(BaseModel):
    url: HttpUrl   # rejects non-HTTP(S) schemes, malformed URLs
```

---

## Verification

```bash
# These should be rejected or sanitized, not passed to shell
curl -X POST http://localhost:8000/analyze \
  -d '{"url": "https://example.com/; rm -rf /"}'

curl -X POST http://localhost:8000/analyze \
  -d '{"url": "file:///etc/passwd"}'
```

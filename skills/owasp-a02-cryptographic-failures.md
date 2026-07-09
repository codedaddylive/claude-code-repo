# OWASP A02 — Cryptographic Failures

**Stack**: FastAPI, Python 3.11
**Trigger**: Audit for secrets in logs, plaintext API keys, insecure config.

---

## What to look for

- `ANTHROPIC_API_KEY` logged or returned in error responses
- API keys stored in plaintext in config files committed to git
- Sensitive filenames or paths exposed in error messages
- Temp files with transcripts/frames not cleaned up securely

---

## Audit Checklist

```bash
# Check for API key leaks in logs or responses
grep -rn "ANTHROPIC_API_KEY\|sk-ant" . --include="*.py" | grep -v ".env\|os.getenv\|environ"

# Check git history for accidentally committed secrets
git log --all --full-history -- .env
git grep "sk-ant" $(git rev-list --all)

# Check error handlers — do they return internal paths or stack traces?
grep -n "exception_handler\|HTTPException\|raise" api.py
```

---

## Fix patterns

**Never log secrets:**
```python
import logging
# BAD
logging.info(f"Using key: {os.getenv('ANTHROPIC_API_KEY')}")
# GOOD
logging.info("Anthropic API key loaded: %s", "set" if os.getenv("ANTHROPIC_API_KEY") else "MISSING")
```

**Generic error responses (don't leak paths/traces):**
```python
@app.exception_handler(Exception)
async def generic_handler(request, exc):
    logging.error("Unhandled error", exc_info=exc)   # full trace to logs only
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

**Secure temp file cleanup:**
```python
import tempfile, shutil
tmp = tempfile.mkdtemp()
try:
    # ... analysis work ...
finally:
    shutil.rmtree(tmp, ignore_errors=True)   # always clean up
```

---

## Verification

```bash
# Confirm .env is gitignored
grep ".env" .gitignore

# Trigger a 500 — response should not contain file paths or stack traces
curl -X POST http://localhost:8000/analyze -d '{"url": "invalid"}'
```

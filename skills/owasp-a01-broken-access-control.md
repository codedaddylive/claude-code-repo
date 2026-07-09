# OWASP A01 — Broken Access Control

**Stack**: FastAPI, Python 3.11
**Trigger**: Review API endpoints for missing authorization checks.

---

## What to look for

- Endpoints that return or modify data without verifying the caller owns it
- No API key / token validation on POST /analyze, POST /analyze/upload
- Job results (`GET /jobs/{job_id}`) accessible by anyone who guesses the ID
- No rate limiting — any caller can flood the analysis pipeline

---

## Audit Checklist

```bash
# Find all route definitions
grep -n "@app\." api.py

# Check for auth dependencies
grep -n "Depends" api.py

# Check job ID format — UUIDs are harder to enumerate than integers
grep -n "job_id" api.py video_tool/models.py
```

---

## FastAPI fix pattern

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(key: str = Security(API_KEY_HEADER)):
    if key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# Apply to all sensitive routes
@app.post("/analyze", dependencies=[Depends(require_api_key)])
async def analyze(req: AnalyzeRequest): ...
```

## Job ID pattern — use UUIDs not integers

```python
import uuid
job_id = str(uuid.uuid4())   # not sequential int
```

---

## Verification

```bash
# Should return 403
curl -X POST http://localhost:8000/analyze -d '{"url":"..."}' 

# Should return 200
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: your-key" -d '{"url":"..."}'
```

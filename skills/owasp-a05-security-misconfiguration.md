# OWASP A05 — Security Misconfiguration

**Stack**: FastAPI, uvicorn, Python 3.11
**Trigger**: Audit FastAPI server config before deploying to EC2.

---

## What to look for

- CORS set to `*` (allows any origin to call your API)
- Debug mode / stack traces exposed in production
- Default uvicorn binding to `0.0.0.0` with no firewall
- OpenAPI docs (`/docs`, `/redoc`) publicly accessible in production
- No request size limit — large video uploads could exhaust memory

---

## Audit Checklist

```bash
# Check CORS config
grep -n "CORSMiddleware\|allow_origins" api.py

# Check if docs are disabled in production
grep -n "docs_url\|redoc_url\|openapi_url" api.py

# Check uvicorn startup command
grep -rn "uvicorn" Makefile requirements.txt *.sh 2>/dev/null

# Check for debug flags
grep -n "debug=True\|reload=True" api.py
```

---

## Fix patterns

**CORS — restrict to known origins:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],   # not "*"
    allow_methods=["POST", "GET"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

**Disable docs in production:**
```python
import os
app = FastAPI(
    docs_url="/docs" if os.getenv("ENV") == "development" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if os.getenv("ENV") == "development" else None,
)
```

**Request size limit:**
```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if int(request.headers.get("content-length", 0)) > 500 * 1024 * 1024:  # 500MB
            return Response("Request too large", status_code=413)
        return await call_next(request)
```

**EC2 — bind to localhost, use nginx reverse proxy:**
```bash
uvicorn api:app --host 127.0.0.1 --port 8000   # not 0.0.0.0
```

---

## Verification

```bash
# CORS header should not be *
curl -I -H "Origin: https://evil.com" http://localhost:8000/health

# /docs should 404 in production
curl http://localhost:8000/docs
```

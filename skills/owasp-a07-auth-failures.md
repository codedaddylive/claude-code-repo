# OWASP A07 — Identification and Authentication Failures

**Stack**: FastAPI, Python 3.11
**Trigger**: Audit API authentication before exposing to the internet.

---

## What to look for

- No authentication on any endpoint (current state)
- API keys passed in query params (logged by servers/proxies)
- No rate limiting — brute-force of API keys possible
- Long-lived API keys with no rotation mechanism

---

## Audit Checklist

```bash
# Find unprotected routes
grep -n "@app\.\(get\|post\|put\|delete\)" api.py | grep -v "health"

# Check if API key is ever in query string
grep -n "api_key\|apikey\|token" api.py | grep "Query\|request\.query"

# Check for rate limiting middleware
grep -n "RateLimitMiddleware\|slowapi\|limits" api.py
```

---

## Fix patterns

**API key via header (not query param — headers aren't logged by default):**
```python
from fastapi.security import APIKeyHeader
from fastapi import Security, HTTPException

api_key_scheme = APIKeyHeader(name="X-API-Key")

async def verify_key(key: str = Security(api_key_scheme)) -> str:
    if key != os.getenv("SERVICE_API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return key
```

**Rate limiting with slowapi:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze(request: Request, req: AnalyzeRequest): ...
```

**Health check stays public, everything else requires auth:**
```python
@app.get("/health")   # no auth — used by load balancers
async def health(): return {"status": "ok"}

@app.post("/analyze", dependencies=[Depends(verify_key)])
async def analyze(req: AnalyzeRequest): ...
```

---

## Verification

```bash
# No key — should 401
curl -X POST http://localhost:8000/analyze -d '{"url":"..."}'

# Wrong key — should 401
curl -X POST http://localhost:8000/analyze -H "X-API-Key: wrong" -d '{"url":"..."}'

# Rate limit — 11th request in one minute should 429
for i in $(seq 1 11); do curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:8000/analyze -H "X-API-Key: correct"; done
```

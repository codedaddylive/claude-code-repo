# OWASP A09 — Security Logging and Monitoring Failures

**Stack**: FastAPI, Python 3.11, uvicorn
**Trigger**: Audit logging before production deployment on EC2.

---

## What to look for

- No structured logging (hard to parse/alert on)
- Auth failures not logged (can't detect brute-force)
- No request logging middleware (no audit trail)
- Logs contain sensitive data (API keys, file paths, transcripts)

---

## Audit Checklist

```bash
# Check what's being logged
grep -rn "logging\.\|print(" api.py video_tool/

# Check log level configuration
grep -rn "basicConfig\|setLevel\|LOG_LEVEL" api.py

# Check if auth failures are logged
grep -n "401\|403\|Unauthorized\|Forbidden" api.py
```

---

## Fix patterns

**Structured request logging middleware:**
```python
import logging, time, uuid
from fastapi import Request

logger = logging.getLogger("api.access")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration,
            "ip": request.client.host,
        }
    )
    return response
```

**Log auth failures explicitly:**
```python
async def verify_key(key: str = Security(api_key_scheme)) -> str:
    if key != os.getenv("SERVICE_API_KEY"):
        logger.warning("auth_failure", extra={"ip": "unknown", "key_prefix": key[:4]})
        raise HTTPException(status_code=401, detail="Unauthorized")
    return key
```

**Never log full API keys or transcripts:**
```python
# BAD
logger.info(f"Transcript: {result.transcript}")

# GOOD
logger.info("Analysis complete", extra={"transcript_chars": len(result.transcript)})
```

**Log config for EC2:**
```python
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
```

---

## Verification

```bash
# Send a bad auth request — should appear in logs
curl -X POST http://localhost:8000/analyze -H "X-API-Key: badkey" -d '{}'
grep "auth_failure" app.log
```

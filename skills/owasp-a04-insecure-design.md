# OWASP A04 — Insecure Design

**Stack**: FastAPI, yt-dlp, Whisper, Claude API
**Trigger**: Architectural review before production — missing threat model.

---

## Design risks for this app

| Risk | Scenario |
|---|---|
| Resource exhaustion | Attacker submits 10 long videos simultaneously; Whisper + Claude costs spike |
| Unbounded storage | Temp dirs accumulate if cleanup fails after error |
| API cost abuse | Each /analyze call invokes Claude API; no cost cap per caller |
| Job store in-memory | Restart loses all jobs; no persistence |
| Single worker | `--workers 1` means one stuck analysis blocks all requests |

---

## Design fixes

**Job queue with concurrency limit:**
```python
import asyncio
_semaphore = asyncio.Semaphore(3)   # max 3 concurrent analyses

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    async with _semaphore:
        return await run_analysis(req)
```

**Per-caller cost cap (token bucket):**
```python
from collections import defaultdict
import time

_call_counts: dict[str, list[float]] = defaultdict(list)
MAX_CALLS_PER_HOUR = 20

def check_rate(caller_id: str):
    now = time.time()
    calls = [t for t in _call_counts[caller_id] if now - t < 3600]
    if len(calls) >= MAX_CALLS_PER_HOUR:
        raise HTTPException(429, "Hourly limit reached")
    _call_counts[caller_id] = calls + [now]
```

**Guaranteed temp cleanup:**
```python
import tempfile, shutil, contextlib

@contextlib.asynccontextmanager
async def temp_workspace():
    tmp = tempfile.mkdtemp(prefix="aria_")
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

async def run_analysis(req):
    async with temp_workspace() as tmp:
        # all work inside; always cleaned up
        ...
```

**Max video duration / file size at design boundary:**
```python
class AnalyzeRequest(BaseModel):
    url: HttpUrl
    max_frames: int = Field(default=5, ge=1, le=20)   # cap frames
    max_duration_seconds: int = Field(default=600, le=3600)  # cap 1hr
```

---

## Verification

```bash
# Submit 5 simultaneous requests — server should queue, not crash
for i in $(seq 1 5); do
  curl -s -X POST http://localhost:8000/analyze \
    -H "X-API-Key: key" -d '{"url":"..."}' &
done
wait
```

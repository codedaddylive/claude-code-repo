# OWASP A10 — Server-Side Request Forgery (SSRF)

**Stack**: FastAPI, yt-dlp, Python 3.11
**Trigger**: CRITICAL — audit before exposing /analyze endpoint to internet.

---

## Why this is high priority for this app

`POST /analyze` accepts a URL and passes it to `yt-dlp` for download.
Without restrictions, an attacker can:
- Hit EC2 metadata endpoint: `http://169.254.169.254/latest/meta-data/` → steal IAM credentials
- Scan internal network: `http://10.0.0.x/`
- Access localhost services: `http://127.0.0.1:5432/` (Postgres, Redis)
- Read local files via yt-dlp extractors that support `file://`

---

## Audit Checklist

```bash
# Find where URLs are accepted and passed downstream
grep -rn "url\|URL" video_tool/downloader.py api.py video_tool/models.py

# Check if file:// scheme is blocked
grep -rn "HttpUrl\|AnyUrl\|url_validator" video_tool/models.py

# Check yt-dlp options — are dangerous options blocked?
grep -rn "ydl_opts\|YoutubeDL" video_tool/downloader.py
```

---

## Fix patterns

**Block private/metadata IP ranges before download:**
```python
import ipaddress, socket
from urllib.parse import urlparse

BLOCKED_RANGES = [
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/GCP metadata
    ipaddress.ip_network("10.0.0.0/8"),       # private
    ipaddress.ip_network("172.16.0.0/12"),    # private
    ipaddress.ip_network("192.168.0.0/16"),   # private
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
]

def validate_url_not_ssrf(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme not allowed: {parsed.scheme}")
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
        if any(ip in r for r in BLOCKED_RANGES):
            raise ValueError(f"URL resolves to blocked IP range: {ip}")
    except socket.gaierror:
        raise ValueError("Could not resolve hostname")
```

**Call it before passing to yt-dlp:**
```python
def download(url: str, output_dir: str) -> str:
    validate_url_not_ssrf(url)   # raises ValueError if blocked
    ydl_opts = {
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
        "no_playlist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
```

**Pydantic model — enforce HTTP/HTTPS scheme:**
```python
from pydantic import BaseModel, HttpUrl

class AnalyzeRequest(BaseModel):
    url: HttpUrl   # rejects file://, ftp://, etc. automatically
```

---

## Verification

```bash
# AWS metadata endpoint — should be blocked
curl -X POST http://localhost:8000/analyze \
  -d '{"url": "http://169.254.169.254/latest/meta-data/"}'
# Expected: 400 or 422, not a download attempt

# file:// scheme — should be rejected by Pydantic HttpUrl
curl -X POST http://localhost:8000/analyze \
  -d '{"url": "file:///etc/passwd"}'
# Expected: 422 Unprocessable Entity
```

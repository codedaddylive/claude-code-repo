# OWASP A08 — Software and Data Integrity Failures

**Stack**: Python 3.11, pip, yt-dlp, GitHub Actions
**Trigger**: Audit supply chain and file upload integrity.

---

## What to look for

- File uploads not validated for type or content (just MIME type spoofing)
- yt-dlp downloading from unverified sources without checksum
- pip dependencies without hash pinning
- No signature verification on downloaded binaries (e.g. Squad binary)

---

## Audit Checklist

```bash
# Check file upload handler — does it validate beyond MIME type?
grep -n "upload\|UploadFile\|content_type" api.py

# Check if requirements.txt uses hashes
grep "==" requirements.txt | head -5
# Hash-pinned looks like: fastapi==0.111.0 --hash=sha256:abc123...

# Generate hash-pinned requirements
pip-compile --generate-hashes requirements.in > requirements.txt
```

---

## Fix patterns

**Validate uploaded files by magic bytes, not just extension/MIME:**
```python
import magic   # pip install python-magic

ALLOWED_VIDEO_SIGNATURES = {
    b'\x00\x00\x00\x18ftypmp4',  # MP4
    b'\x1aE\xdf\xa3',            # WebM/MKV
    b'RIFF',                      # AVI
}

async def validate_video(file: UploadFile) -> bytes:
    header = await file.read(32)
    await file.seek(0)
    if not any(header.startswith(sig) for sig in ALLOWED_VIDEO_SIGNATURES):
        raise HTTPException(status_code=400, detail="Invalid video file")
    return header
```

**Limit upload size:**
```python
MAX_UPLOAD_BYTES = 500 * 1024 * 1024   # 500MB

@app.post("/analyze/upload")
async def analyze_upload(file: UploadFile):
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
```

**Verify downloaded binary checksums:**
```bash
# When downloading Squad or any binary
sha256sum squad-x86_64-unknown-linux-musl.tar.gz
# Compare against published checksum in GitHub release notes
```

---

## Verification

```bash
# Upload a non-video file renamed as .mp4 — should be rejected
cp /etc/passwd fake.mp4
curl -X POST http://localhost:8000/analyze/upload -F "file=@fake.mp4"
```

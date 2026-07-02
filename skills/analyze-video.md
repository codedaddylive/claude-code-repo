# Workflow: Analyze Video

**Trigger**: User provides a video URL or local file path and wants analysis.

---

## Pre-flight Checks

```bash
# Verify API key
echo $ANTHROPIC_API_KEY | grep -q "sk-ant" || echo "ERROR: ANTHROPIC_API_KEY not set"

# Verify dependencies
python -c "import whisper, cv2, anthropic, yt_dlp" && echo "OK" || echo "Run: pip install -r requirements.txt"

# Verify ffmpeg
ffmpeg -version > /dev/null 2>&1 && echo "ffmpeg OK" || echo "Run: apt install ffmpeg"
```

---

## Steps

### 1. Full pipeline (preferred)

```bash
python cli.py analyze "<URL or /path/to/video.mp4>" --max-frames 5 --output result.json
```

Handles download → frame extraction → transcription → Claude vision automatically.

### 2. Step-by-step (use when debugging or partial runs needed)

```bash
# Extract frames only
python cli.py extract-frames "video.mp4" --output-dir ./frames --interval 5

# Transcribe only
python cli.py transcribe "video.mp4" --model base

# Then analyze manually with the extracted frames
python cli.py analyze "video.mp4" --max-frames 10 --output result.json
```

### 3. Viability check (paste a link → adopt/investigate/skip verdict)

Judge whether the tool/technique in a video is worth adopting into this stack.

```bash
python cli.py viability "<URL or /path/to/video.mp4>"
python cli.py viability "https://x.com/user/status/123" --cookies cookies.txt  # auth-walled X
python cli.py viability "<URL>" --output verdict.json
```

Downloads → transcribes (visual-summary fallback if no audio) → asks Claude to
rate the content against the ARIA stack. Prints:

```
VERDICT: ADOPT  (confidence 80%)
Reasoning: ...tied to FastAPI/yt-dlp/Whisper...
Touches: FastAPI, yt-dlp
Encode it: python brain.py add --title "..." --category apis
```

On `ADOPT`, run the printed `brain.py add` line to encode the decision into ARIA.

---

## Where this can run (network policy)

Ingest needs outbound egress to the video host. **The Claude Code web
environment blocks all video hosts** (youtube, x.com/twitter, vimeo, tiktok,
instagram, dailymotion, even direct `.mp4` URLs — verified via proxy CONNECT
log; only github/pypi/npm/anthropic are allowed). So links pasted into a *web*
chat cannot be ingested.

- **Run on a local/EC2 machine** for real ingest (open network).
- **YouTube** additionally IP-blocks datacenter/Colab/EC2 addresses — use a
  home network or a local file there.
- To ingest from the web environment, its network policy must be widened at
  environment-creation time: https://code.claude.com/docs/en/claude-code-on-the-web

---

## Output

Successful `result.json` contains:
```json
{
  "summary": "...",
  "keyframes": [
    { "timestamp": 0.0, "description": "..." }
  ],
  "objects_detected": ["..."],
  "transcript": "..."
}
```

---

## Known Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| Connection fails / HTTP 000 in web env | Network policy blocks video hosts | Run locally, or widen the env network policy |
| yt-dlp download blocked (403) | YouTube blocks datacenter/Colab/EC2 IP | Use a home network or a local file |
| x.com link not routed | Only matched via fallback (slower) | Fixed — `x.com` now in downloader regex |
| Whisper slow first run | Downloading ~150MB base model | Wait — cached after first run |
| `ANTHROPIC_API_KEY` error | Key not exported | `export ANTHROPIC_API_KEY=sk-ant-...` |
| Black MP4 on iPhone | WebM/VP8 output | Use imageio-ffmpeg binary for H.264 |
| `BrokenPipeError` in ffmpeg pipe | Missing `-vcodec mjpeg` flag | Add flag before `-i pipe:0` |

---

## Verification

```bash
# Confirm output file exists and is valid JSON
python -c "import json; d=json.load(open('result.json')); print('OK —', len(d['keyframes']), 'keyframes,', len(d.get('transcript','')) , 'chars transcript')"
```

---

## Invocation Example

```
Follow skills/analyze-video.md for this file: /path/to/video.mp4
```

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
| yt-dlp download blocked | Datacenter/Colab IP | Use a local file instead |
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

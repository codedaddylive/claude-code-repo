#!/usr/bin/env python3
"""
Integration test for the video analysis pipeline.

Tests:
  1. Local file resolution and copy
  2. Frame extraction (OpenCV interval + scene strategies)
  3. Audio extraction (ffmpeg)
  4. Whisper transcription (base model)
  5. Claude vision analysis (requires ANTHROPIC_API_KEY)

Usage:
  # All tests except Claude (no API key needed):
  python tests/integration_test.py

  # Full test including Claude vision:
  ANTHROPIC_API_KEY=sk-ant-... python tests/integration_test.py

  # Skip Whisper (faster):
  SKIP_WHISPER=1 python tests/integration_test.py
"""

import os
import sys
import subprocess
import tempfile
import pathlib
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
SKIP = "\033[93m SKIP\033[0m"


def step(name: str):
    print(f"\n{'─'*50}\n{name}")


def ok(msg: str):
    print(f"  {PASS}  {msg}")


def fail(msg: str):
    print(f"  {FAIL}  {msg}")
    sys.exit(1)


def skip(msg: str):
    print(f"  {SKIP}  {msg}")


# ── Generate test video ────────────────────────────────────────────────────────

def make_test_video(path: pathlib.Path) -> pathlib.Path:
    """Create a 15s synthetic video with 440Hz tone audio."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "testsrc=duration=15:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=15",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(path),
    ], capture_output=True, check=True)
    return path


# ── Test 1: Source resolution + local copy ────────────────────────────────────

def test_source_resolution(video_path: pathlib.Path, tmp: pathlib.Path):
    step("1. Source resolution + local copy")
    from video_tool.downloader import resolve_source, download_video

    src = resolve_source(str(video_path))
    assert src.is_local, "Expected is_local=True for a local path"
    ok(f"resolve_source: is_local={src.is_local}")

    dest = download_video(src, tmp / "dl")
    assert dest.exists() and dest.stat().st_size > 0, "Copied file is empty"
    ok(f"download_video: {dest.name} ({dest.stat().st_size // 1024} KB)")


# ── Test 2: Frame extraction (interval) ───────────────────────────────────────

def test_frame_extraction_interval(video_path: pathlib.Path, tmp: pathlib.Path):
    step("2. Frame extraction — interval strategy")
    from video_tool.extractor import extract_frames, get_video_duration
    from video_tool.models import FrameSamplingStrategy

    dur = get_video_duration(video_path)
    assert 14 < dur < 16, f"Unexpected duration: {dur}"
    ok(f"get_video_duration: {dur:.1f}s")

    frames = extract_frames(
        video_path, tmp / "frames_interval",
        strategy=FrameSamplingStrategy.INTERVAL,
        interval_sec=4.0,
        max_frames=4,
    )
    assert len(frames) == 4, f"Expected 4 frames, got {len(frames)}"
    for f in frames:
        assert pathlib.Path(f.file_path).exists(), f"Frame file missing: {f.file_path}"
        assert pathlib.Path(f.file_path).stat().st_size > 1000, "Frame JPEG looks too small"
    ok(f"extract_frames (interval): {len(frames)} frames at {[round(f.timestamp_sec,1) for f in frames]}s")


# ── Test 3: Frame extraction (scene detection) ────────────────────────────────

def test_frame_extraction_scene(video_path: pathlib.Path, tmp: pathlib.Path):
    step("3. Frame extraction — scene detection strategy")
    from video_tool.extractor import extract_frames
    from video_tool.models import FrameSamplingStrategy

    frames = extract_frames(
        video_path, tmp / "frames_scene",
        strategy=FrameSamplingStrategy.SCENE,
        max_frames=8,
    )
    # testsrc has few scene changes — may fall back to interval, which is fine
    assert len(frames) > 0, "No frames extracted with scene strategy"
    ok(f"extract_frames (scene/fallback): {len(frames)} frames")


# ── Test 4: Audio extraction ───────────────────────────────────────────────────

def test_audio_extraction(video_path: pathlib.Path, tmp: pathlib.Path):
    step("4. Audio extraction")
    from video_tool.extractor import extract_audio

    audio = extract_audio(video_path, tmp / "audio.wav")
    assert audio is not None, "extract_audio returned None for a video with audio"
    assert audio.exists() and audio.stat().st_size > 10_000, "Audio WAV is too small"
    ok(f"extract_audio: {audio.stat().st_size // 1024} KB WAV at 16kHz mono")


# ── Test 5: Whisper transcription ─────────────────────────────────────────────

def test_whisper(video_path: pathlib.Path, tmp: pathlib.Path):
    step("5. Whisper transcription")
    if os.getenv("SKIP_WHISPER") == "1":
        skip("SKIP_WHISPER=1 set — skipping")
        return

    from video_tool.extractor import extract_audio
    from video_tool.transcriber import transcribe

    audio = extract_audio(video_path, tmp / "whisper_audio.wav")
    assert audio is not None

    t0 = time.time()
    try:
        result = transcribe(audio, model_name="base")
        elapsed = time.time() - t0
        ok(f"transcribe: completed in {elapsed:.1f}s, language='{getattr(result, 'language', 'N/A')}', "
           f"text_len={len(getattr(result, 'full_text', ''))}")
    except Exception as e:
        if "403" in str(e) or "download" in str(e).lower() or "urlopen" in str(e).lower():
            skip(f"Whisper model download blocked in this environment: {e}")
        else:
            raise


# ── Test 6: Claude vision analysis ────────────────────────────────────────────

def test_claude_vision(video_path: pathlib.Path, tmp: pathlib.Path):
    step("6. Claude vision analysis")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        skip("ANTHROPIC_API_KEY not set — skipping Claude test")
        return

    from video_tool.extractor import extract_frames
    from video_tool.analyzer import encode_frame, analyze_keyframes, detect_objects_and_scenes, generate_visual_summary, get_client
    from video_tool.models import FrameSamplingStrategy

    frames = extract_frames(
        video_path, tmp / "claude_frames",
        strategy=FrameSamplingStrategy.INTERVAL,
        interval_sec=5.0,
        max_frames=3,
    )
    encoded = [encode_frame(f) for f in frames]

    client = get_client()

    # 6a: Keyframe descriptions
    t0 = time.time()
    descriptions = analyze_keyframes(client, encoded)
    assert len(descriptions) == len(encoded), f"Got {len(descriptions)} descriptions for {len(encoded)} frames"
    ok(f"analyze_keyframes: {len(descriptions)} descriptions in {time.time()-t0:.1f}s")
    for i, d in enumerate(descriptions):
        print(f"     Frame {i}: {d[:80]}")

    # 6b: Object detection
    t0 = time.time()
    detections = detect_objects_and_scenes(client, encoded)
    assert len(detections) > 0
    ok(f"detect_objects_and_scenes: {len(detections)} results in {time.time()-t0:.1f}s")
    for d in detections:
        print(f"     t={d.timestamp_sec:.0f}s objects={d.detected_objects[:3]} scene='{d.scene_description[:60]}'")

    # 6c: Visual summary
    t0 = time.time()
    summary = generate_visual_summary(client, encoded)
    assert len(summary) > 50, "Summary is suspiciously short"
    ok(f"generate_visual_summary: {len(summary)} chars in {time.time()-t0:.1f}s")
    print(f"     Preview: {summary[:200]}...")


# ── Test 7: FastAPI health endpoint ──────────────────────────────────────────

def test_api():
    step("7. FastAPI — health endpoint")
    import api
    from contextlib import asynccontextmanager
    from fastapi.testclient import TestClient

    @asynccontextmanager
    async def _noop(app):
        yield

    api.app.router.lifespan_context = _noop
    client = TestClient(api.app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    ok(f"GET /health -> {r.status_code} {r.json()}")


# ── Test 8: CLI help ──────────────────────────────────────────────────────────

def test_cli():
    step("8. CLI — help text")
    result = subprocess.run(
        ["python3", "cli.py", "--help"],
        capture_output=True, text=True,
        cwd=str(pathlib.Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert "analyze" in result.stdout
    assert "extract-frames" in result.stdout
    assert "transcribe" in result.stdout
    ok("cli.py --help shows all 3 subcommands")


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Video Tool — Integration Test")
    print(f"API key: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
    print("=" * 50)

    with tempfile.TemporaryDirectory(prefix="video_tool_test_") as tmpdir:
        tmp = pathlib.Path(tmpdir)
        video = make_test_video(tmp / "test.mp4")
        print(f"\nTest video: {video} ({video.stat().st_size // 1024} KB)")

        test_source_resolution(video, tmp)
        test_frame_extraction_interval(video, tmp)
        test_frame_extraction_scene(video, tmp)
        test_audio_extraction(video, tmp)
        test_whisper(video, tmp)
        test_claude_vision(video, tmp)
        test_api()
        test_cli()

    print(f"\n{'='*50}")
    print("All tests completed.")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nNOTE: Re-run with ANTHROPIC_API_KEY=sk-ant-... to test Claude vision.")


if __name__ == "__main__":
    main()

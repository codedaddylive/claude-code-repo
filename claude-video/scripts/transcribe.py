"""
transcribe.py — VTT parsing, deduplication, and Whisper orchestration for claude-video.
"""

import os
import re
import subprocess

import whisper as whisper_mod


def parse_vtt(vtt_path):
    """
    Parse a WebVTT file into a list of timestamped caption entries.

    Strips the WEBVTT header, timing lines, and deduplicates consecutive
    repeated lines (common in YouTube auto-captions).

    Returns:
        list[dict]: Each dict has keys 'start' ("MM:SS") and 'text' (str).
    """
    with open(vtt_path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    entries = []
    # Split on blank lines
    blocks = re.split(r"\n\s*\n", raw.strip())

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        # Skip the WEBVTT header block
        if lines[0].startswith("WEBVTT"):
            continue
        # Find the timing line: 00:00:00.000 --> 00:00:00.000
        timing_idx = None
        for i, line in enumerate(lines):
            if re.search(r"\d+:\d+:\d+\.\d+\s+-->\s+\d+:\d+:\d+\.\d+", line) or \
               re.search(r"\d+:\d+\.\d+\s+-->\s+\d+:\d+\.\d+", line):
                timing_idx = i
                break
        if timing_idx is None:
            continue

        timing_line = lines[timing_idx]
        text_lines = lines[timing_idx + 1:]
        if not text_lines:
            continue

        start_str = timing_line.split("-->")[0].strip()
        start_s = _vtt_time_to_seconds(start_str)
        m = int(start_s) // 60
        s = int(start_s) % 60
        start_mmss = f"{m:02d}:{s:02d}"

        # Join text, strip VTT tags like <c>, <00:00:00.000>
        text = " ".join(text_lines)
        text = re.sub(r"<[^>]+>", "", text).strip()
        if not text:
            continue

        entries.append({"start": start_mmss, "text": text})

    return dedup_lines(entries)


def _vtt_time_to_seconds(ts):
    """Convert VTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) to float seconds."""
    ts = ts.split(".")[0]  # drop milliseconds
    parts = ts.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0])


def dedup_lines(entries):
    """
    Remove consecutive duplicate caption lines.

    YouTube auto-captions often repeat the same text across adjacent cues.
    Keep only the first occurrence of each run of identical text.
    """
    if not entries:
        return entries
    result = [entries[0]]
    for entry in entries[1:]:
        if entry["text"].strip() != result[-1]["text"].strip():
            result.append(entry)
    return result


def format_transcript(entries):
    """
    Format caption entries as a readable transcript string.

    Returns:
        str: Lines like "[MM:SS] caption text\n..."
    """
    if not entries:
        return "(no transcript available)"
    return "\n".join(f"[{e['start']}] {e['text']}" for e in entries)


def extract_audio(video_path, out_dir):
    """
    Extract mono 16 kHz WAV audio from video_path using ffmpeg.

    Returns:
        str: Path to the extracted WAV file.

    Raises:
        RuntimeError: If ffmpeg fails.
    """
    os.makedirs(out_dir, exist_ok=True)
    audio_path = os.path.join(out_dir, "audio.wav")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr[-800:]}")

    # Warn if file exceeds 25 MB (Whisper API limit)
    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if size_mb > 25:
        print(
            f"Warning: audio file is {size_mb:.1f} MB (Whisper limit is 25 MB). "
            "Use --start/--end to reduce the segment length.",
            flush=True,
        )

    return audio_path


def get_transcript(vtt_path, video_path, out_dir, backend=None, no_whisper=False):
    """
    Obtain a timestamped transcript, preferring native VTT captions.

    Strategy:
    1. If vtt_path exists → parse VTT (free, instant)
    2. Else if not no_whisper → extract audio and call Whisper
    3. Else → return empty string

    Parameters:
        vtt_path (str|None): Path to VTT caption file, or None.
        video_path (str): Path to the video (for audio extraction).
        out_dir (str): Working directory for audio extraction.
        backend (str|None): "groq", "openai", or None (auto-select).
        no_whisper (bool): If True, skip Whisper fallback.

    Returns:
        str: Formatted transcript text.
    """
    if vtt_path and os.path.exists(vtt_path):
        print("Using native VTT captions.", flush=True)
        entries = parse_vtt(vtt_path)
        return format_transcript(entries)

    if no_whisper:
        return "(transcription disabled)"

    print("No native captions found. Running Whisper...", flush=True)
    try:
        audio_path = extract_audio(video_path, out_dir)
        entries = whisper_mod.transcribe(audio_path, backend=backend)
        return format_transcript(entries)
    except RuntimeError as e:
        print(f"Whisper transcription failed: {e}", flush=True)
        return "(transcription unavailable)"

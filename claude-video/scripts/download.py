"""
download.py — yt-dlp wrapper and local file prober for claude-video.
"""

import json
import os
import re
import subprocess
import glob


def is_url(s):
    """Return True if s looks like a remote URL."""
    return s.startswith(("http://", "https://", "www."))


def probe_local(path):
    """
    Use ffprobe to get duration of a local file.

    Returns duration in seconds as a float.
    Raises FileNotFoundError if path does not exist.
    Raises RuntimeError if ffprobe fails.
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Video file not found: {path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    return duration


def download_video(url, out_dir, start=None, end=None):
    """
    Download a video and optional VTT captions using yt-dlp.

    Parameters:
        url (str): Remote video URL.
        out_dir (str): Directory to save files.
        start (float|None): Start time in seconds (for section download hint).
        end (float|None): End time in seconds.

    Returns:
        dict with keys:
            video_path (str): Path to downloaded video file.
            vtt_path (str|None): Path to VTT caption file, or None.
            duration (float): Video duration in seconds.
    """
    os.makedirs(out_dir, exist_ok=True)
    template = os.path.join(out_dir, "video.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "--convert-subs", "vtt",
        "--output", template,
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )

    # Find the downloaded video (yt-dlp picks the extension)
    video_path = _find_video_file(out_dir)
    if not video_path:
        raise RuntimeError(
            f"yt-dlp ran but no video file found in {out_dir}.\n"
            f"stdout: {result.stdout[-500:]}"
        )

    # Find VTT — yt-dlp writes e.g. video.en.vtt
    vtt_path = _find_vtt_file(out_dir)

    # Probe duration
    duration = probe_local(video_path)

    return {
        "video_path": video_path,
        "vtt_path": vtt_path,
        "duration": duration,
    }


def _find_video_file(directory):
    """Return the first non-VTT, non-JSON media file found in directory."""
    video_exts = {
        ".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".m4v", ".ts"
    }
    for fname in sorted(os.listdir(directory)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in video_exts:
            return os.path.join(directory, fname)
    return None


def _find_vtt_file(directory):
    """Return the first .vtt file found in directory, or None."""
    pattern = os.path.join(directory, "*.vtt")
    matches = sorted(glob.glob(pattern))
    return matches[0] if matches else None

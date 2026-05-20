"""
frames.py — ffmpeg frame extraction with auto-scaled fps budget for claude-video.
"""

import os
import re
import subprocess


# Hard caps
MAX_FPS = 2.0
MAX_FRAMES = 100


def parse_time(s):
    """
    Parse a time string into seconds (float).

    Accepts:
        "90"        → 90.0
        "1:30"      → 90.0
        "1:12:00"   → 4320.0
    """
    s = str(s).strip()
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    parts = s.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Cannot parse time: {s!r}")


def _target_frames(duration_s):
    """Return the target frame count for a given duration."""
    if duration_s <= 30:
        return 30
    if duration_s <= 60:
        return 40
    if duration_s <= 180:
        return 60
    if duration_s <= 600:
        return 80
    return MAX_FRAMES


def calculate_fps(duration_s, start=None, end=None, max_frames=None):
    """
    Calculate an appropriate fps for frame extraction.

    Parameters:
        duration_s (float): Total video duration in seconds.
        start (float|None): Start of focus window in seconds.
        end (float|None): End of focus window in seconds.
        max_frames (int|None): Override the frame budget cap.

    Returns:
        float: fps, capped at MAX_FPS (2.0).
    """
    # Use the focus window duration if specified
    if start is not None or end is not None:
        s = start or 0.0
        e = end if end is not None else duration_s
        window = max(e - s, 1.0)
    else:
        window = max(duration_s, 1.0)

    target = max_frames if max_frames else _target_frames(window)
    fps = target / window
    return min(fps, MAX_FPS)


def _seconds_to_mmss(seconds):
    """Convert seconds to MM-SS string for use in filenames."""
    seconds = int(seconds)
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}-{s:02d}"


def extract_frames(video_path, out_dir, fps, start=None, end=None, width=512):
    """
    Extract JPEG frames from video_path using ffmpeg.

    Frame filenames encode the timestamp: frame_NNNNNN_tMM-SS.jpg

    Parameters:
        video_path (str): Path to the video file.
        out_dir (str): Directory to write frames into.
        fps (float): Frames per second to extract.
        start (float|None): Start time in seconds.
        end (float|None): End time in seconds.
        width (int): Output frame width in pixels (height auto-scaled).

    Returns:
        list[dict]: Each dict has keys 'path' and 'timestamp' ("MM:SS").
    """
    os.makedirs(out_dir, exist_ok=True)

    cmd = ["ffmpeg", "-y"]

    if start is not None:
        cmd += ["-ss", str(start)]

    cmd += ["-i", video_path]

    if end is not None:
        duration = end - (start or 0.0)
        cmd += ["-t", str(duration)]

    # Scale width, preserve aspect ratio; ensure even dimensions
    vf = f"fps={fps},scale={width}:-2"
    cmd += [
        "-vf", vf,
        "-q:v", "3",
        os.path.join(out_dir, "frame_%06d.jpg"),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed:\n{result.stderr[-1000:]}")

    # Collect and rename frames with timestamp suffix
    raw_frames = sorted(
        f for f in os.listdir(out_dir) if f.startswith("frame_") and f.endswith(".jpg")
        and "_t" not in f
    )

    frame_interval = 1.0 / fps
    offset = start or 0.0
    result_list = []

    for i, fname in enumerate(raw_frames):
        elapsed = i * frame_interval
        abs_time = offset + elapsed
        ts_file = _seconds_to_mmss(abs_time)
        ts_display = f"{int(abs_time)//60:02d}:{int(abs_time)%60:02d}"

        old_path = os.path.join(out_dir, fname)
        new_name = f"frame_{i+1:06d}_t{ts_file}.jpg"
        new_path = os.path.join(out_dir, new_name)
        os.rename(old_path, new_path)

        result_list.append({
            "path": new_path,
            "timestamp": ts_display,
        })

    return result_list

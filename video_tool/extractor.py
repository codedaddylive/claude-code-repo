from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import ffmpeg

from .models import ExtractionError, FrameInfo, FrameSamplingStrategy

_MAX_FRAME_WIDTH = 1280


def get_video_duration(video_path: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, ValueError) as e:
        raise ExtractionError(f"Could not determine video duration: {e}") from e


def extract_frames(
    video_path: Path,
    output_dir: Path,
    strategy: FrameSamplingStrategy = FrameSamplingStrategy.INTERVAL,
    interval_sec: float = 5.0,
    max_frames: int = 20,
    scene_threshold: float = 0.4,
) -> list[FrameInfo]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if strategy == FrameSamplingStrategy.SCENE:
        return _extract_by_scene(video_path, output_dir, max_frames, scene_threshold)
    return _extract_by_interval(video_path, output_dir, interval_sec, max_frames)


def _extract_by_interval(
    video_path: Path,
    output_dir: Path,
    interval_sec: float,
    max_frames: int,
) -> list[FrameInfo]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ExtractionError(f"OpenCV could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration = total_frames / fps

    timestamps = [
        i * interval_sec
        for i in range(max_frames)
        if i * interval_sec < total_duration
    ]

    frames: list[FrameInfo] = []
    for i, ts in enumerate(timestamps):
        cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
        ret, frame = cap.read()
        if not ret:
            break

        frame = _resize_frame(frame)
        out_path = output_dir / f"frame_{i:04d}_{int(ts):05d}s.jpg"
        cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frames.append(FrameInfo(index=i, timestamp_sec=ts, file_path=str(out_path)))

    cap.release()
    return frames


def _extract_by_scene(
    video_path: Path,
    output_dir: Path,
    max_frames: int,
    threshold: float,
) -> list[FrameInfo]:
    out_pattern = str(output_dir / "frame_%04d.jpg")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-q:v", "3",
        out_pattern,
        "-y",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse timestamps from showinfo stderr output
    timestamps: list[float] = []
    for line in result.stderr.splitlines():
        match = re.search(r"pts_time:([\d.]+)", line)
        if match:
            timestamps.append(float(match.group(1)))

    frame_files = sorted(output_dir.glob("frame_*.jpg"))
    frames: list[FrameInfo] = []
    for i, (frame_path, ts) in enumerate(zip(frame_files[:max_frames], timestamps[:max_frames])):
        img = cv2.imread(str(frame_path))
        if img is not None:
            img = _resize_frame(img)
            cv2.imwrite(str(frame_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frames.append(FrameInfo(index=i, timestamp_sec=ts, file_path=str(frame_path)))

    # Fallback: if scene detection produced no frames, use interval strategy
    if not frames:
        return _extract_by_interval(video_path, output_dir, interval_sec=10.0, max_frames=max_frames)

    return frames


def extract_audio(
    video_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
) -> Optional[Path]:
    try:
        stream = ffmpeg.input(str(video_path))
        out = ffmpeg.output(
            stream.audio,
            str(output_path),
            ar=sample_rate,
            ac=1,
            acodec="pcm_s16le",
        )
        ffmpeg.run(out, overwrite_output=True, quiet=True)
        return output_path
    except ffmpeg.Error:
        return None


def _resize_frame(frame):
    h, w = frame.shape[:2]
    if w > _MAX_FRAME_WIDTH:
        scale = _MAX_FRAME_WIDTH / w
        new_w = _MAX_FRAME_WIDTH
        new_h = int(h * scale)
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return frame

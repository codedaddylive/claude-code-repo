from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import yt_dlp

from .models import DownloadError, VideoSource

_YTDLP_DOMAINS = re.compile(
    r"(youtube\.com|youtu\.be|vimeo\.com|tiktok\.com|twitter\.com|"
    r"(?<!\w)x\.com|"
    r"instagram\.com|dailymotion\.com|twitch\.tv|facebook\.com)"
)

_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}


def resolve_source(raw: str) -> VideoSource:
    path = Path(raw)
    if path.exists() and path.is_file():
        return VideoSource(raw=raw, is_local=True, local_path=path)

    if _YTDLP_DOMAINS.search(raw):
        return VideoSource(raw=raw, is_local=False)

    # Treat as a direct URL (may still be yt-dlp compatible, try direct first)
    return VideoSource(raw=raw, is_local=False)


def download_video(source: VideoSource, output_dir: Path, cookies_file: Optional[Path] = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    if source.is_local and source.local_path:
        return _copy_local_file(source.local_path, output_dir)

    if _YTDLP_DOMAINS.search(source.raw):
        return _download_with_ytdlp(source.raw, output_dir, cookies_file)

    # Try direct URL download; fall back to yt-dlp if Content-Type is not video
    try:
        return _download_direct_url(source.raw, output_dir)
    except DownloadError:
        return _download_with_ytdlp(source.raw, output_dir, cookies_file)


def _download_with_ytdlp(url: str, output_dir: Path, cookies_file: Optional[Path] = None) -> Path:
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }
    if cookies_file:
        ydl_opts["cookiefile"] = str(cookies_file)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        raise DownloadError(f"yt-dlp failed to download '{url}': {e}") from e

    video_files = sorted(
        [f for f in output_dir.iterdir() if f.suffix in _VIDEO_EXTENSIONS],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not video_files:
        raise DownloadError(f"yt-dlp completed but no video file found in {output_dir}")
    return video_files[0]


def _download_direct_url(url: str, output_dir: Path) -> Path:
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("video/"):
                raise DownloadError(
                    f"URL does not appear to be a direct video (Content-Type: {content_type})"
                )
            suffix = _suffix_from_content_type(content_type)
            out_path = output_dir / f"video{suffix}"
            with out_path.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    fh.write(chunk)
    except httpx.HTTPError as e:
        raise DownloadError(f"HTTP error downloading '{url}': {e}") from e
    return out_path


def _copy_local_file(path: Path, output_dir: Path) -> Path:
    dest = output_dir / path.name
    shutil.copy2(path, dest)
    return dest


def _suffix_from_content_type(content_type: str) -> str:
    mapping = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/x-matroska": ".mkv",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
    }
    base = content_type.split(";")[0].strip()
    return mapping.get(base, ".mp4")
